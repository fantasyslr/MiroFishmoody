"""
简单登录系统 — 内测用户表从环境变量加载 + Flask session

用户表格式（环境变量 MOODY_USERS）:
  username:password:display_name:role,username2:password2:...

示例:
  export MOODY_USERS="admin:your-password:Admin:admin,user1:your-password:User1:user"

如果 MOODY_USERS 未设置，启动时会报警告并使用空用户表（无法登录）。
"""

import os
import hashlib
import warnings
from functools import wraps
from flask import session, jsonify, request
import bcrypt


def _is_bcrypt_hash(value: str) -> bool:
    """Check if a string looks like a bcrypt hash ($2b$ or $2a$ prefix, 60 chars)."""
    return bool(value) and value.startswith(('$2b$', '$2a$', '$2y$')) and len(value) == 60


def _hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(username: str, password: str) -> bool:
    """Verify password against stored hash. Auto-migrates plaintext to bcrypt on success."""
    user = USERS.get(username)
    if not user:
        return False
    stored = user["password"]
    if _is_bcrypt_hash(stored):
        return bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
    else:
        # Plaintext comparison (backward compat safety net)
        if stored == password:
            # Auto-migrate: replace plaintext with bcrypt hash in memory
            user["password"] = _hash_password(password)
            return True
        return False


def _load_users():
    """从 MOODY_USERS 环境变量解析用户表。"""
    raw = os.environ.get("MOODY_USERS", "")
    if not raw.strip():
        warnings.warn(
            "MOODY_USERS 环境变量未设置，无法登录。"
            "格式: username:password:display_name:role,..."
        )
        return {}
    users = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) < 4:
            warnings.warn(f"MOODY_USERS 格式错误，跳过: {entry!r}")
            continue
        username, password, display_name, role = parts[0], parts[1], parts[2], parts[3]
        users[username] = {
            "password": password,
            "display_name": display_name,
            "role": role,
        }
    # Hash plaintext passwords immediately — never store plaintext in memory
    for uname, user_data in users.items():
        if not _is_bcrypt_hash(user_data["password"]):
            user_data["password"] = _hash_password(user_data["password"])
    return users


USERS = _load_users()


def _password_version(username: str) -> str:
    """基于当前密码生成版本标识，密码变更时自动失效旧 session"""
    user = USERS.get(username, {})
    pw = user.get("password", "")
    return hashlib.sha256(f"{username}:{pw}".encode()).hexdigest()[:16]


def _validate_session(user_data: dict):
    """验证 session 中的用户数据是否仍然有效。返回 None 表示有效，否则返回错误响应。"""
    username = user_data.get('username', '')
    if username not in USERS:
        session.pop('user', None)
        return jsonify({"error": "用户已不存在"}), 401
    expected_ver = _password_version(username)
    if user_data.get('_pw_ver') != expected_ver:
        session.pop('user', None)
        return jsonify({"error": "密码已变更，请重新登录"}), 401
    return None


def login_required(f):
    """登录校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get('user')
        if not user:
            return jsonify({"error": "未登录，请先登录"}), 401
        invalid = _validate_session(user)
        if invalid:
            return invalid
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """管理员校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get('user')
        if not user:
            return jsonify({"error": "未登录，请先登录"}), 401
        invalid = _validate_session(user)
        if invalid:
            return invalid
        username = user.get('username', '')
        user_info = USERS.get(username, {})
        if user_info.get('role') != 'admin':
            return jsonify({"error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """获取当前登录用户信息"""
    return session.get('user')
