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