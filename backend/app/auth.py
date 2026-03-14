"""
简单登录系统 — 内测用户表从环境变量加载 + Flask session

用户表格式（环境变量 MOODY_USERS）:
  username:password:display_name:role,username2:password2:...

示例:
  export MOODY_USERS="admin:your-password:Admin:admin,user1:your-password:User1:user"

如果 MOODY_USERS 未设置，启动时会报警告并使用空用户表（无法登录）。
"""

import os
import warnings
from functools import wraps
from flask import session, jsonify, request


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
    return users


USERS = _load_users()


def login_required(f):
    """登录校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "未登录，请先登录"}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """管理员校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get('user')
        if not user:
            return jsonify({"error": "未登录，请先登录"}), 401
        username = user.get('username', '')
        user_info = USERS.get(username, {})
        if user_info.get('role') != 'admin':
            return jsonify({"error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """获取当前登录用户信息"""
    return session.get('user')
