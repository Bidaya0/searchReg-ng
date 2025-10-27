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
        },
        "email": {
            "mailgun_domain": os.getenv("MAILGUN_DOMAIN"),
            "mailgun_api_key": os.getenv("MAILGUN_API_KEY"),
            "from_email": os.getenv("FROM_EMAIL", "noreply@example.com"),
            "to_email": os.getenv("TO_EMAIL"),
            "cc_email": os.getenv("CC_EMAIL"),
            "bcc_email": os.getenv("BCC_EMAIL")
        },
        # User Story 4 配置
        "us4": {
            # 树状建模配置
            "tree_modeling": {
                "max_tree_depth": 3,
                "min_importance_threshold": 0.3,
                "max_branching_factor": 10
            },
            # 评分系统配置
            "scoring": {
                "min_comprehensive_score": 60.0,
                "min_quality_level": "中",
                "weights": {
                    "search_quality_weight": 0.4,
                    "content_depth_weight": 0.4,
                    "technical_metrics_weight": 0.2
                }
            },
            # 方向筛选配置
            "direction_selection": {
                "max_detailed_directions": 1,
                "max_summary_directions": 4,
                "complementary_threshold": 0.3,
                "enable_quality_filtering": True,
                "enable_complementary_analysis": True
            },
            # 报告优化配置
            "report_optimization": {
                "executive_summary_length": 300,
                "detailed_analysis_length": 800,
                "enable_llm_generation": True
            }
        },
        # 无尽模式配置
        "endless_mode": {
            "enabled": False,
            "max_iterations": 10,
            "top_reports": 3,
            "new_question_strategy": "best_direction_based",
            "early_termination": {
                "enabled": False,
                "no_improvement_threshold": 3,
                "min_score_improvement": 5.0
            },
            "error_handling": {
                "max_consecutive_failures": 3,
                "continue_on_partial_failure": True
            }
        }
    }
