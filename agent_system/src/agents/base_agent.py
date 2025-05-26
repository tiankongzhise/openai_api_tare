from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from src.core.config import Config, ConfigManager
from src.core.llm_client import LLMClient, Message
from src.core.database import DatabaseManager
from src.models.schemas import UserInput, AgentResponse
import uuid

class BaseAgent(ABC):
    def __init__(self, config_path: str):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_agent_config(config_path)
        
        # 初始化LLM客户端
        self.llm_client = LLMClient(
            api_key=self.config_manager.openai_api_key,
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        
        # 初始化数据库
        self.db_manager = DatabaseManager(self.config_manager.database_url)
        
        # Agent状态
        self.session_id = str(uuid.uuid4())
        self.conversation_history: List[Message] = []
        
        # 添加系统提示
        if self.config.llm.system_prompt:
            self.conversation_history.append(
                Message(role="system", content=self.config.llm.system_prompt)
            )
    
    @abstractmethod
    async def process(self, user_input: UserInput) -> AgentResponse:
        """处理用户输入的抽象方法"""
        pass
    
    def validate_input(self, user_input: UserInput) -> bool:
        """验证输入"""
        # 检查输入长度
        if len(user_input.content) > self.config.validation.max_input_length:
            raise ValueError(f"输入长度超过限制: {self.config.validation.max_input_length}")
        
        # 检查必需字段
        for field in self.config.validation.required_fields:
            if not hasattr(user_input, field) or not getattr(user_input, field):
                raise ValueError(f"缺少必需字段: {field}")
        
        return True
    
    def add_to_history(self, role: str, content: str):
        """添加到对话历史"""
        self.conversation_history.append(Message(role=role, content=content))
        
        # 限制历史长度
        if self.config.features.enable_memory:
            max_history = self.config.features.max_history * 2 + 1  # +1 for system message
            if len(self.conversation_history) > max_history:
                # 保留系统消息，删除最旧的对话
                system_msg = self.conversation_history[0]
                self.conversation_history = [system_msg] + self.conversation_history[-(max_history-1):]
    
    async def call_llm(self, messages: List[Message]) -> str:
        """调用LLM"""
        response = await self.llm_client.chat_completion(
            messages=messages,
            model=self.config.llm.model,
            max_tokens=self.config.llm.max_tokens,
            temperature=self.config.llm.temperature
        )
        return response.content
    
    def save_conversation(self, user_input: str, agent_response: str):
        """保存对话到数据库"""
        if self.config.features.enable_memory:
            self.db_manager.save_conversation(
                agent_type=self.config.agent.type,
                user_input=user_input,
                agent_response=agent_response,
                session_id=self.session_id
            )