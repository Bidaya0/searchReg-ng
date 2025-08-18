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
    search_results: List[SearchResult] = []
    summaries: List[str] = []
    key_points: List[str] = []
    chat_history: List[ChatMessage] = []
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorLog(BaseModel):
    """错误日志"""
    error: str
    topic: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str = "error"
    termination_reason: str = "system_error" 