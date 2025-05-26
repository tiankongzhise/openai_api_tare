from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserInput(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('输入内容不能为空')
        return v.strip()

class AgentResponse(BaseModel):
    content: str
    agent_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(UserInput):
    """聊天请求"""
    user_input: str = Field(alias='content')

class AnalysisRequest(UserInput):
    """分析请求"""
    data: str = Field(..., description="要分析的数据")
    analysis_type: str = Field(..., description="分析类型")
    
    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        allowed_types = ['statistical', 'trend', 'comparison', 'summary']
        if v not in allowed_types:
            raise ValueError(f'分析类型必须是: {allowed_types}')
        return v

class AgentStatus(BaseModel):
    name: str
    type: str
    status: str  # active, inactive, error
    last_used: Optional[datetime] = None
    total_requests: int = 0