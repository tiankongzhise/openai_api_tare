from src.agents.base_agent import BaseAgent
from src.models.schemas import UserInput, AgentResponse, ChatRequest
from src.core.llm_client import Message

class ChatAgent(BaseAgent):
    async def process(self, user_input: UserInput) -> AgentResponse:
        """处理聊天请求"""
        # 验证输入
        chat_request = ChatRequest(**user_input.dict())
        self.validate_input(chat_request)
        
        # 添加用户消息到历史
        self.add_to_history("user", chat_request.content)
        
        # 准备消息
        messages = self.conversation_history.copy()
        
        # 如果启用上下文，添加最近的对话历史
        if self.config.features.enable_context:
            recent_history = await self.db_manager.get_conversation_history(
                agent_type=self.config.agent.type,
                session_id=self.session_id,
                limit=3
            )
            
            if recent_history: # Ensure recent_history is not None or empty
                for conv in reversed(recent_history):
                    messages.insert(-1, Message(role="user", content=conv.user_input))
                    messages.insert(-1, Message(role="assistant", content=conv.agent_response))
        
        # 调用LLM
        response_content = await self.call_llm(messages)
        
        # 添加助手回复到历史
        self.add_to_history("assistant", response_content)
        
        # 保存对话
        await self.save_conversation(chat_request.content, response_content)
        
        return AgentResponse(
            content=response_content,
            agent_type=self.config.agent.type,
            metadata={
                "model": self.config.llm.model,
                "session_id": self.session_id
            }
        )
