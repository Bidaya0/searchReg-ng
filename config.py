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
        "model": os.getenv("MODEL", "THUDM/GLM-Z1-9B-0414"),
        "temperature": float(os.getenv("TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("MAX_TOKENS", "15000")),
        "max_results": int(os.getenv("MAX_RESULTS", "20")),
        "searx_host": os.getenv("SEARX_HOST", "http://127.0.0.1:8080"),
        "storage": {
            "cache_dir": "./data/cache",
            "results_dir": "./data/results",
            "logs_dir": "./data/logs",
            "checkpoints_dir": "./data/checkpoints",
            "progress_dir": "./data/progress"
        },
        "email": {
            "mailgun_domain": os.getenv("MAILGUN_DOMAIN"),
            "mailgun_api_key": os.getenv("MAILGUN_API_KEY"),
            "from_email": os.getenv("FROM_EMAIL", "noreply@example.com"),
            "to_email": os.getenv("TO_EMAIL"),
            "cc_email": os.getenv("CC_EMAIL"),
            "bcc_email": os.getenv("BCC_EMAIL")
        },
        "long_running": {
            "max_duration_hours": int(os.getenv("MAX_DURATION_HOURS", "8")),
            "checkpoint_interval_minutes": int(os.getenv("CHECKPOINT_INTERVAL_MINUTES", "15")),
            "memory_cleanup_interval_minutes": int(os.getenv("MEMORY_CLEANUP_INTERVAL_MINUTES", "30")),
            "resource_monitor_interval_seconds": int(os.getenv("RESOURCE_MONITOR_INTERVAL_SECONDS", "60")),
            "max_memory_usage_mb": int(os.getenv("MAX_MEMORY_USAGE_MB", "2048")),
            "max_disk_usage_mb": int(os.getenv("MAX_DISK_USAGE_MB", "10240")),
            "search_timeout": int(os.getenv("LONG_RUNNING_SEARCH_TIMEOUT", "300")),
            "max_concurrent_searches": int(os.getenv("LONG_RUNNING_MAX_CONCURRENT", "3")),
            "search_retry_count": int(os.getenv("LONG_RUNNING_SEARCH_RETRY_COUNT", "5")),
            "max_iterations": int(os.getenv("LONG_RUNNING_MAX_ITERATIONS", "100")),
            "iteration_timeout_minutes": int(os.getenv("ITERATION_TIMEOUT_MINUTES", "30")),
            "quality_convergence_threshold": float(os.getenv("QUALITY_CONVERGENCE_THRESHOLD", "0.02")),
            "min_iteration_time_seconds": int(os.getenv("MIN_ITERATION_TIME_SECONDS", "30")),
            
            # 时间策略配置
            "time_strategies": {
                "hard": {
                    "buffer_time_seconds": int(os.getenv("HARD_STRATEGY_BUFFER_SECONDS", "300")),  # 5分钟缓冲
                    "strict_deadline": True
                },
                "soft": {
                    "buffer_time_seconds": int(os.getenv("SOFT_STRATEGY_BUFFER_SECONDS", "1800")),  # 30分钟缓冲
                    "iteration_reduction_factor": int(os.getenv("SOFT_STRATEGY_REDUCTION_FACTOR", "2")),  # 每隔一轮执行
                    "gradual_reduction": True
                },
                "adaptive": {
                    "high_quality_threshold": float(os.getenv("ADAPTIVE_HIGH_QUALITY_THRESHOLD", "0.8")),
                    "low_quality_threshold": float(os.getenv("ADAPTIVE_LOW_QUALITY_THRESHOLD", "0.5")),
                    "high_quality_iteration_factor": int(os.getenv("ADAPTIVE_HIGH_QUALITY_FACTOR", "3")),  # 每3轮执行一次
                    "quality_based_adjustment": True
                }
            },
            
            # 迭代搜索配置
            "iteration_search": {
                "default_duration_hours": int(os.getenv("ITERATION_DEFAULT_DURATION_HOURS", "2")),
                "max_questions_per_iteration": int(os.getenv("ITERATION_MAX_QUESTIONS", "25")),
                "deepening_questions_count": int(os.getenv("ITERATION_DEEPENING_QUESTIONS", "5")),
                "quality_evaluation_enabled": True,
                "result_deduplication_enabled": True
            }
        }
    }
