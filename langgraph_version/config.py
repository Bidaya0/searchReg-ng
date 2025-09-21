from typing import Dict, Any
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def get_config() -> Dict[str, Any]:
    """获取系统配置"""
    return {
        "api_key": os.getenv("API_KEY"),
        "base_url": os.getenv("BASE_URL", "http://localhost:8000"),
        "model": os.getenv("MODEL", "Pro/THUDM/glm-4-9b-chat"),
        "temperature": float(os.getenv("TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("MAX_TOKENS", "15000")),
        "max_results": int(os.getenv("MAX_RESULTS", "20")),
        "searx_host": os.getenv("SEARX_HOST", "http://127.0.0.1:8080"),
        "storage": {
            "cache_dir": "./data/cache",
            "results_dir": "./data/results",
            "logs_dir": "./data/logs"
        }
    }
