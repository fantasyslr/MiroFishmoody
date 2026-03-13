"""
简单登录系统 — 内测用硬编码用户表 + Flask session
"""

from functools import wraps
from flask import session, jsonify, request

# 硬编码内测用户（后续改成数据库）
USERS = {
    "liren": {"password": "moody2026", "display_name": "Liren"},
    "tester1": {"password": "test1234", "display_name": "测试员1"},
    "tester2": {"password": "test1234", "display_name": "测试员2"},
    "test1": {"password": "eazillion123", "display_name": "Test1"},
    "test2": {"password": "eazillion123", "display_name": "Test2"},
    "test3": {"password": "eazillion123", "display_name": "Test3"},
    "test4": {"password": "eazillion123", "display_name": "Test4"},
    "test5": {"password": "eazillion123", "display_name": "Test5"},
    "test6": {"password": "eazillion123", "display_name": "Test6"},
    "test7": {"password": "eazillion123", "display_name": "Test7"},
    "test8": {"password": "eazillion123", "display_name": "Test8"},
    "test9": {"password": "eazillion123", "display_name": "Test9"},
    "test10": {"password": "eazillion123", "display_name": "Test10"},
}


def login_required(f):
    """登录校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "未登录，请先登录"}), 401
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """获取当前登录用户信息"""
    return session.get('user')
