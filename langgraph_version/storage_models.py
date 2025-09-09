from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class SearchItem(BaseModel):
    """搜索结果项"""
    title: str
    snippet: str
    link: str

class SearchResult(BaseModel):
    """搜索结果"""
    query: str
    results: List[SearchItem]
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatMessage(BaseModel):
    """对话消息"""
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class FinalResult(BaseModel):
    """最终结果"""
    status: str
    termination_reason: Optional[str] = None
    search_results: List[SearchResult] = Field(default_factory=list)
    summaries: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    chat_history: List[ChatMessage] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorLog(BaseModel):
    """错误日志"""
    error: str
    topic: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str = "error"
    termination_reason: str = "system_error"

class QuestionItem(BaseModel):
    """单个问题项"""
    question: str
    intent: str | None = None

class QuestionDirection(BaseModel):
    """问题方向及其问题集合"""
    direction: str
    rationale: str | None = None
    questions: List[QuestionItem] = Field(default_factory=list)

class QuestionsResult(BaseModel):
    """按方向组织的25问结果"""
    topic: str
    directions: List[QuestionDirection] = Field(default_factory=list)
    total_questions: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

class QuestionSearchRun(BaseModel):
    """单个问题的搜索运行记录"""
    question: str
    direction: str | None = None
    query: str | None = None
    search_result: SearchResult | None = None
    error: str | None = None
    retrieved_at: datetime = Field(default_factory=datetime.now)

class QuestionsSearchResult(BaseModel):
    """整批问题搜索结果"""
    topic: str
    directions: List[QuestionDirection] = Field(default_factory=list)
    question_runs: List[QuestionSearchRun] = Field(default_factory=list)
    total_questions: int = 0
    completed_runs: int = 0
    error_runs: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

# LangGraph 状态模型
class SearchState(BaseModel):
    """搜索系统状态"""
    topic: str
    current_query: Optional[str] = None
    search_results: List[SearchResult] = Field(default_factory=list)
    summaries: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    messages: List[ChatMessage] = Field(default_factory=list)
    status: str = "running"
    termination_reason: Optional[str] = None
    iteration_count: int = 0
    max_iterations: int = 20

class QuestionState(BaseModel):
    """问题生成系统状态"""
    topic: str
    directions: List[QuestionDirection] = Field(default_factory=list)
    total_questions: int = 0
    status: str = "running"
    error: Optional[str] = None
