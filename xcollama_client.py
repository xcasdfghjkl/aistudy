import requests
import logging
from typing import Dict, Any
from xcconfig import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    """Ollama API客户端"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL_NAME
        self._test_connection()
    
    def _test_connection(self):
        """测试Ollama连接"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                available_models = [m['name'] for m in models]
                logger.info(f"✅ Ollama连接成功，可用模型: {available_models}")
                if self.model not in available_models:
                    logger.warning(f"⚠️ 模型 '{self.model}' 未找到，请使用: ollama pull {self.model}")
            else:
                logger.error("❌ Ollama服务未启动")
        except Exception as e:
            logger.error(f"🔌 无法连接Ollama: {e}")
            raise ConnectionError(f"请确保Ollama服务正在运行: {e}")
    
    def generate(self, prompt: str) -> str:
        """使用Ollama生成文本"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 512
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '未获取到响应')
            else:
                return f"Ollama API错误: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Ollama生成失败: {e}")
            return f"生成错误: {str(e)}"

# 全局实例
ollama_client = OllamaClient()