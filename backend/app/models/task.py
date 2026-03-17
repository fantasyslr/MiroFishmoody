"""
任务状态管理
用于跟踪长时间运行的任务（如图谱构建）
SQLite持久化：任务在服务重启后仍然保留
"""

import json
import os
import sqlite3
import uuid
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from app.config import Config


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 等待中
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败


@dataclass
class Task:
    """任务数据类"""
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0              # 总进度百分比 0-100
    message: str = ""              # 状态消息
    result: Optional[Dict] = None  # 任务结果
    error: Optional[str] = None    # 错误信息
    metadata: Dict = field(default_factory=dict)  # 额外元数据
    progress_detail: Dict = field(default_factory=dict)  # 详细进度信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "message": self.message,
            "progress_detail": self.progress_detail,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


class TaskManager:
    """
    任务管理器
    线程安全的任务状态管理，SQLite持久化
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tasks: Dict[str, Task] = {}
                    cls._instance._task_lock = threading.Lock()
                    cls._instance._init_db()
                    cls._instance._load_all_from_db()
        return cls._instance

    # ------------------------------------------------------------------ #
    #  SQLite helpers
    # ------------------------------------------------------------------ #

    def _db_path(self) -> str:
        return os.path.join(Config.UPLOAD_FOLDER, "tasks.db")

    def _connect(self) -> sqlite3.Connection:
        """Create a SQLite connection with WAL mode and busy_timeout."""
        conn = sqlite3.connect(self._db_path(), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        """Create the tasks table if it does not exist."""
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        conn = self._connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id        TEXT PRIMARY KEY,
                    task_type      TEXT,
                    status         TEXT,
                    created_at     TEXT,
                    updated_at     TEXT,
                    progress       INTEGER,
                    message        TEXT,
                    result         TEXT,
                    error          TEXT,
                    metadata       TEXT,
                    progress_detail TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_all_from_db(self):
        """Load every row from SQLite into the in-memory dict.
        Tasks stuck in PROCESSING/PENDING are marked FAILED (server restart recovery).
        """
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        interrupted = []
        try:
            rows = conn.execute("SELECT * FROM tasks").fetchall()
            for row in rows:
                task = self._row_to_task(row)
                if task.status in (TaskStatus.PROCESSING, TaskStatus.PENDING):
                    task.status = TaskStatus.FAILED
                    task.error = "服务重启，任务中断"
                    task.message = "服务重启，任务中断（可重新提交）"
                    task.updated_at = datetime.now()
                    interrupted.append(task)
                self._tasks[task.task_id] = task
        finally:
            conn.close()
        for task in interrupted:
            self._persist_task(task)

    @staticmethod
    def _row_to_task(row) -> Task:
        """Convert a sqlite3.Row into a Task dataclass instance."""
        result_val = json.loads(row["result"]) if row["result"] else None
        metadata_val = json.loads(row["metadata"]) if row["metadata"] else {}
        progress_detail_val = json.loads(row["progress_detail"]) if row["progress_detail"] else {}
        return Task(
            task_id=row["task_id"],
            task_type=row["task_type"],
            status=TaskStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            progress=row["progress"] or 0,
            message=row["message"] or "",
            result=result_val,
            error=row["error"],
            metadata=metadata_val,
            progress_detail=progress_detail_val,
        )

    def _persist_task(self, task: Task):
        """Upsert a single task into SQLite (called inside _task_lock)."""
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO tasks
                    (task_id, task_type, status, created_at, updated_at,
                     progress, message, result, error, metadata, progress_detail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.task_type,
                    task.status.value,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    task.progress,
                    task.message,
                    json.dumps(task.result) if task.result is not None else None,
                    task.error,
                    json.dumps(task.metadata) if task.metadata else None,
                    json.dumps(task.progress_detail) if task.progress_detail else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _delete_task_from_db(self, task_id: str):
        """Delete a single task from SQLite (called inside _task_lock)."""
        conn = self._connect()
        try:
            conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  Public API (unchanged signatures)
    # ------------------------------------------------------------------ #

    def create_task(self, task_type: str, metadata: Optional[Dict] = None) -> str:
        """
        创建新任务

        Args:
            task_type: 任务类型
            metadata: 额外元数据

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()

        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )

        with self._task_lock:
            self._tasks[task_id] = task
            self._persist_task(task)

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is not None:
                return task
        # Fallback: check SQLite in case memory was cleared
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if row:
                task = self._row_to_task(row)
                with self._task_lock:
                    self._tasks[task_id] = task
                return task
        finally:
            conn.close()
        return None

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        progress_detail: Optional[Dict] = None
    ):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度
            message: 消息
            result: 结果
            error: 错误信息
            progress_detail: 详细进度信息
        """
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task:
                task.updated_at = datetime.now()
                if status is not None:
                    task.status = status
                if progress is not None:
                    task.progress = progress
                if message is not None:
                    task.message = message
                if result is not None:
                    task.result = result
                if error is not None:
                    task.error = error
                if progress_detail is not None:
                    task.progress_detail = progress_detail
                self._persist_task(task)

    def complete_task(self, task_id: str, result: Dict):
        """标记任务完成"""
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="任务完成",
            result=result
        )

    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message="任务失败",
            error=error
        )

    def list_tasks(self, task_type: Optional[str] = None) -> list:
        """列出任务"""
        with self._task_lock:
            tasks = list(self._tasks.values())
            if task_type:
                tasks = [t for t in tasks if t.task_type == task_type]
            return [t.to_dict() for t in sorted(tasks, key=lambda x: x.created_at, reverse=True)]

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        with self._task_lock:
            old_ids = [
                tid for tid, task in self._tasks.items()
                if task.created_at < cutoff and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            ]
            for tid in old_ids:
                del self._tasks[tid]
                self._delete_task_from_db(tid)
