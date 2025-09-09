import logging
import sys
from datetime import datetime
from typing import Any, Dict, List
import json

def json_serializer(obj):
    """自定义JSON序列化器"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, 'dict'):
        return obj.dict()
    else:
        return str(obj)

class WorkflowLogger:
    """工作流日志记录器"""
    
    def __init__(self, name: str = "workflow", log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(f"./data/logs/workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        if not self.logger.handlers:
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
    
    def log_workflow_start(self, workflow_name: str, topic: str):
        """记录工作流开始"""
        self.logger.info(f"🚀 工作流开始: {workflow_name}")
        self.logger.info(f"📝 主题: {topic}")
        self.logger.info("=" * 50)
    
    def log_workflow_end(self, workflow_name: str, status: str, result: Dict[str, Any]):
        """记录工作流结束"""
        self.logger.info("=" * 50)
        self.logger.info(f"🏁 工作流结束: {workflow_name}")
        self.logger.info(f"📊 状态: {status}")
        self.logger.info(f"📈 结果摘要: {json.dumps(result, ensure_ascii=False, indent=2, default=json_serializer)}")
    
    def log_node_start(self, node_name: str, state: Dict[str, Any]):
        """记录节点开始"""
        self.logger.info(f"🔄 节点开始: {node_name}")
        self.logger.debug(f"📋 当前状态: {json.dumps(state, ensure_ascii=False, indent=2, default=json_serializer)}")
    
    def log_node_end(self, node_name: str, result: Any):
        """记录节点结束"""
        self.logger.info(f"✅ 节点完成: {node_name}")
        if isinstance(result, dict):
            self.logger.debug(f"📤 节点结果: {json.dumps(result, ensure_ascii=False, indent=2, default=json_serializer)}")
        else:
            self.logger.debug(f"📤 节点结果: {str(result)}")
    
    def log_conversation(self, role: str, content: str, node_name: str = ""):
        """记录对话内容"""
        prefix = f"[{node_name}] " if node_name else ""
        self.logger.info(f"💬 {prefix}{role}: {content[:200]}{'...' if len(content) > 200 else ''}")
    
    def log_search_query(self, query: str, results_count: int):
        """记录搜索查询"""
        self.logger.info(f"🔍 搜索查询: {query}")
        self.logger.info(f"📊 搜索结果数量: {results_count}")
    
    def log_error(self, error: str, context: str = ""):
        """记录错误"""
        self.logger.error(f"❌ 错误: {error}")
        if context:
            self.logger.error(f"📍 上下文: {context}")
    
    def log_warning(self, warning: str, context: str = ""):
        """记录警告"""
        self.logger.warning(f"⚠️ 警告: {warning}")
        if context:
            self.logger.warning(f"📍 上下文: {context}")
    
    def log_info(self, message: str, data: Any = None):
        """记录信息"""
        self.logger.info(f"ℹ️ {message}")
        if data is not None:
            self.logger.info(f"📊 数据: {json.dumps(data, ensure_ascii=False, indent=2, default=json_serializer)}")
    
    def log_debug(self, message: str, data: Any = None):
        """记录调试信息"""
        self.logger.debug(f"🐛 {message}")
        if data is not None:
            self.logger.debug(f"📊 数据: {json.dumps(data, ensure_ascii=False, indent=2, default=json_serializer)}")
    
    def log_state_transition(self, from_node: str, to_node: str, reason: str = ""):
        """记录状态转换"""
        self.logger.info(f"🔄 状态转换: {from_node} -> {to_node}")
        if reason:
            self.logger.info(f"💭 原因: {reason}")
    
    def log_llm_request(self, prompt: str, model: str):
        """记录LLM请求"""
        self.logger.info(f"🤖 LLM请求 - 模型: {model}")
        self.logger.debug(f"📝 提示词: {prompt[:300]}{'...' if len(prompt) > 300 else ''}")
    
    def log_llm_response(self, response: str, model: str):
        """记录LLM响应"""
        self.logger.info(f"🤖 LLM响应 - 模型: {model}")
        self.logger.debug(f"📤 响应内容: {response[:300]}{'...' if len(response) > 300 else ''}")

# 全局日志记录器实例
workflow_logger = WorkflowLogger()
