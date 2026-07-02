import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Config:
    """配置中心 - 根据图片结构优化"""
    
    # 应用配置
    APP_NAME = "AI Agent System"
    VERSION = "2.1"
    DEBUG = True
    
    # 路径配置 - 根据图片结构
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    
    # 🔥 关键配置：启用上下文记忆
    ENABLE_CONTEXT_MEMORY = True  # 设为True启用上下文记忆
    MEMORY_DB_PATH = BASE_DIR / "langagent.db"  # 使用图片中的数据库文件
    
    # 大模型API配置
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "deepseek-r1:1.5b")
    # LLM_API_KEY = os.getenv("LLM_API_KEY", "您的API密钥")
    # LLM_API_BASE = "https://api.deepseek.com/v1"
    # LLM_MODEL_NAME = "deepseek-chat"
    
    # 天气API配置
    AMAP_API_KEY = os.getenv("AMAP_API_KEY", "您的高德地图API密钥")
    AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
    
    # 记忆配置
    @property
    def memory_config(self) -> Dict[str, Any]:
        return {
            "max_history_length": 10,  # 记住最近10轮对话
            "entity_tracking": True,   # 启用实体跟踪
            "reference_resolution": True  # 启用指代消解
        }
    
    def __init__(self):
        self.DATA_DIR.mkdir(exist_ok=True)
        self._validate_config()

    def _validate_config(self):
        """验证配置"""
        print("=" * 50)
        print("🔧 AI Agent配置验证")
        print("=" * 50)
        print(f"📁 项目根目录: {self.BASE_DIR}")
        print(f"💾 记忆数据库: {self.MEMORY_DB_PATH}")
        print(f"🧠 上下文记忆: {'✅ 启用' if self.ENABLE_CONTEXT_MEMORY else '❌ 禁用'}")
        # print(f"🤖 大模型API: {'✅ 已配置' if self.LLM_API_KEY and self.LLM_API_KEY != '您的API密钥' else '❌ 未配置'}")
        print(f"🌤️ 天气API: {'✅ 已配置' if self.AMAP_API_KEY and self.AMAP_API_KEY != '您的高德地图API密钥' else '❌ 未配置'}")
        print("=" * 50)

settings = Config()