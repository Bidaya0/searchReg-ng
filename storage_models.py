from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json

class BaseModelWithDatetime(BaseModel):
    """带有datetime序列化支持的基类"""
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def dict(self, **kwargs):
        """重写dict方法以正确处理datetime"""
        data = super().dict(**kwargs)
        # 递归处理嵌套的datetime对象
        return self._serialize_datetime(data)
    
    def _serialize_datetime(self, obj):
        """递归序列化datetime对象"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        else:
            return obj

class SearchItem(BaseModelWithDatetime):
    """搜索结果项"""
    title: str
    snippet: str
    link: str

class SearchResult(BaseModelWithDatetime):
    """搜索结果"""
    query: str
    results: List[SearchItem]
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatMessage(BaseModelWithDatetime):
    """对话消息"""
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class FinalResult(BaseModelWithDatetime):
    """最终结果"""
    status: str
    termination_reason: Optional[str] = None
    search_results: List[SearchResult] = Field(default_factory=list)
    summaries: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    chat_history: List[ChatMessage] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorLog(BaseModelWithDatetime):
    """错误日志"""
    error: str
    topic: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str = "error"
    termination_reason: str = "system_error"

class QuestionItem(BaseModelWithDatetime):
    """单个问题项"""
    question: str
    intent: str | None = None

class QuestionDirection(BaseModelWithDatetime):
    """问题方向及其问题集合"""
    direction: str
    rationale: str | None = None
    questions: List[QuestionItem] = Field(default_factory=list)

class QuestionsResult(BaseModelWithDatetime):
    """按方向组织的25问结果"""
    topic: str
    directions: List[QuestionDirection] = Field(default_factory=list)
    total_questions: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

class QuestionSearchRun(BaseModelWithDatetime):
    """单个问题的搜索运行记录"""
    question: str
    direction: str | None = None
    query: str | None = None
    search_result: SearchResult | None = None
    error: str | None = None
    retrieved_at: datetime = Field(default_factory=datetime.now)

class QuestionsSearchResult(BaseModelWithDatetime):
    """整批问题搜索结果"""
    topic: str
    directions: List[QuestionDirection] = Field(default_factory=list)
    question_runs: List[QuestionSearchRun] = Field(default_factory=list)
    total_questions: int = 0
    completed_runs: int = 0
    error_runs: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

class SearchRoundRecord(BaseModelWithDatetime):
    """单轮搜索记录"""
    round_number: int
    question: str
    direction: str
    search_query: str
    search_results: List[SearchItem] = Field(default_factory=list)
    summary: str = ""
    key_points: List[str] = Field(default_factory=list)
    success: bool = True
    error_message: str = ""
    processing_time: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)

class IntegratedWorkflowRecord(BaseModelWithDatetime):
    """集成工作流完整记录"""
    topic: str
    workflow_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_questions: int = 0
    completed_searches: int = 0
    failed_searches: int = 0
    search_rounds: List[SearchRoundRecord] = Field(default_factory=list)
    final_summary: str = ""
    key_insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    execution_stats: Dict[str, Any] = Field(default_factory=dict)
    status: str = "running"
    error_message: str = ""

# LangGraph 状态模型 - 使用TypedDict而不是BaseModel
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class SearchState(TypedDict):
    """搜索系统状态"""
    topic: str
    current_query: Optional[str]
    search_results: List[SearchResult]
    summaries: List[str]
    key_points: List[str]
    messages: Annotated[List[BaseMessage], add_messages]
    status: str
    termination_reason: Optional[str]
    iteration_count: int
    max_iterations: int
    # 新增记忆相关字段
    historical_topics: List[str]  # 历史搜索主题
    learning_mode: bool  # 学习模式开关
    knowledge_graph: Dict[str, Any]  # 知识图谱
    related_concepts: List[str]  # 相关概念
    user_preferences: Dict[str, Any]  # 用户偏好
    session_memory: Dict[str, Any]  # 会话记忆
    context_memory: List[Dict[str, Any]]  # 上下文记忆
    search_patterns: List[Dict[str, Any]]  # 搜索模式记忆

class QuestionState(TypedDict):
    """问题生成系统状态"""
    topic: str
    directions: List[QuestionDirection]
    total_questions: int
    status: str
    error: Optional[str]
    raw_response: Optional[str]
    last_llm_response: Optional[str]  # 备用响应字段
    parsed_json: Optional[Dict[str, Any]]
    retry_count: int

# 长时间运行工作流状态模型
class LongRunningWorkflowState(TypedDict):
    """长时间运行工作流状态"""
    # 基础信息
    topic: str
    status: str
    error: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    workflow_id: str
    
    # 时间控制
    deadline: datetime
    elapsed_time: float
    remaining_time: float
    time_warnings: List[str]
    
    # 迭代控制
    current_iteration: int
    max_iterations: int
    iteration_budget: float
    quality_threshold: float
    convergence_threshold: float
    
    # 质量评估
    quality_scores: List[Dict[str, Any]]
    improvement_directions: List[str]
    convergence_metrics: Dict[str, Any]
    
    # 结果累积
    accumulated_results: List[Dict[str, Any]]
    best_results: Dict[str, Any]
    improvement_history: List[Dict[str, Any]]
    
    # 资源管理
    resource_status: Dict[str, Any]
    memory_pressure: bool
    disk_pressure: bool
    trigger_cleanup: bool
    memory_cleanup_count: int
    
    # 检查点管理
    last_checkpoint_time: Optional[datetime]
    checkpoint_path: Optional[str]
    custom_checkpoint_id: Optional[str]
    force_checkpoint: bool
    
    # 进度跟踪
    progress: Dict[str, Any]
    should_continue: str
    
    # 原有工作流状态字段
    questions: List[QuestionItem]
    question_directions: List[QuestionDirection]
    question_generation_completed: bool
    question_generation_error: Optional[str]
    
    search_tasks: List[Dict[str, Any]]
    search_results: List[SearchResult]
    search_progress: Dict[str, Any]
    search_completed: bool
    search_errors: List[str]
    
    processed_results: Optional[Dict[str, Any]]
    result_processing_completed: bool
    result_processing_error: Optional[str]
    
    integrated_summary: Optional[Dict[str, Any]]
    summary_completed: bool
    summary_error: Optional[str]
    
    final_report: Optional[Dict[str, Any]]
    report_generated: bool
    
    workflow_record: Optional[IntegratedWorkflowRecord]
    search_rounds: List[SearchRoundRecord]
    parsed_json: Optional[Dict[str, Any]]
    retry_count: int
