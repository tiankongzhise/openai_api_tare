import openai
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: str

class LLMResponse(BaseModel):
    content: str
    usage: Dict[str, Any]
    model: str

class LLMClient:
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """聊天完成"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[msg.dict() for msg in messages],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                usage=response.usage.dict(),
                model=response.model
            )
        except Exception as e:
            raise Exception(f"LLM调用失败: {str(e)}")