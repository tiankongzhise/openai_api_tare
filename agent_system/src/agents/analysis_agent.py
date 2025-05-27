import json
from src.agents.base_agent import BaseAgent
from src.models.schemas import UserInput, AgentResponse, AnalysisRequest
from src.core.llm_client import Message

class AnalysisAgent(BaseAgent):
    async def process(self, user_input: UserInput) -> AgentResponse:
        """处理分析请求"""
        # 验证输入
        analysis_request = AnalysisRequest(**user_input.dict())
        self.validate_input(analysis_request)
        
        # 构建分析提示
        analysis_prompt = self._build_analysis_prompt(
            analysis_request.data,
            analysis_request.analysis_type
        )
        
        # 准备消息
        messages = []
        if self.config.llm.system_prompt:
            messages.append(Message(role="system", content=self.config.llm.system_prompt))
        
        messages.append(Message(role="user", content=analysis_prompt))
        
        # 调用LLM
        response_content = await self.call_llm(messages)
        
        # 如果需要结构化输出，尝试解析JSON
        if self.config.features.get("output_format") == "structured":
            try:
                structured_response = json.loads(response_content)
                response_content = json.dumps(structured_response, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                # 如果解析失败，保持原始响应
                pass
        
        # 保存对话
        await self.save_conversation(
            f"数据分析请求: {analysis_request.analysis_type}",
            response_content
        )
        
        return AgentResponse(
            content=response_content,
            agent_type=self.config.agent.type,
            metadata={
                "analysis_type": analysis_request.analysis_type,
                "model": self.config.llm.model,
                "data_length": len(analysis_request.data)
            }
        )
    
    def _build_analysis_prompt(self, data: str, analysis_type: str) -> str:
        """构建分析提示"""
        prompts = {
            "statistical": f"请对以下数据进行统计分析，包括基本统计量、分布特征等：\n\n{data}",
            "trend": f"请分析以下数据的趋势变化，识别模式和规律：\n\n{data}",
            "comparison": f"请对以下数据进行比较分析，找出差异和相似点：\n\n{data}",
            "summary": f"请对以下数据进行总结分析，提取关键信息：\n\n{data}"
        }
        
        return prompts.get(analysis_type, f"请分析以下数据：\n\n{data}")
