"""
Auth API — 登录 / 登出 / 当前用户
"""

from flask import Blueprint, request, jsonify, session
from ..auth import USERS

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    user = USERS.get(username)
    if not user or user["password"] != password:
        return jsonify({"error": "用户名或密码错误"}), 401

    session['user'] = {
        "username": username,
        "display_name": user["display_name"],
        "role": user.get("role", "user"),
    }
    return jsonify({
        "username": username,
        "display_name": user["display_name"],
        "role": user.get("role", "user"),
    })


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"status": "ok"})


@auth_bp.route('/me', methods=['GET'])
def me():
    user = session.get('user')
    if not user:
        return jsonify({"error": "未登录"}), 401
    return jsonify(user)
