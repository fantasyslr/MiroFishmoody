"""
Campaign Ranker Engine — 配置管理
"""

import os
from dotenv import load_dotenv

project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    load_dotenv(override=True)


class Config:
    """Flask配置类"""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'campaign-ranker-secret')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    JSON_AS_ASCII = False

    # LLM配置（OpenAI格式）
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # 评审引擎配置
    JUDGE_TEMPERATURE = float(os.environ.get('JUDGE_TEMPERATURE', '0.3'))
    PANEL_TEMPERATURE = float(os.environ.get('PANEL_TEMPERATURE', '0.4'))
    MAX_CAMPAIGNS = int(os.environ.get('MAX_CAMPAIGNS', '6'))

    # Market-Making Judge（实验性，默认关闭）
    USE_MARKET_JUDGE = os.environ.get('USE_MARKET_JUDGE', 'false').lower() == 'true'

    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown', 'json'}

    @classmethod
    def validate(cls):
        """验证必要配置"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")
        return errors
