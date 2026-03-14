"""
Shared test fixtures — 设置测试环境变量（在 import app 之前）
"""

import os
import tempfile

# 必须在 app 模块被 import 之前设置
os.environ.setdefault("MOODY_SECRET_KEY", "test-secret")
os.environ.setdefault("MOODY_UPLOAD_FOLDER", tempfile.mkdtemp())
os.environ.setdefault(
    "MOODY_USERS",
    "slr:test-pass:Liren:admin,tester1:test-pass:Tester1:user",
)
