from typing import Dict, Type
from src.agents.base_agent import BaseAgent
from src.agents.chat_agent import ChatAgent
from src.agents.analysis_agent import AnalysisAgent

class AgentFactory:
    """Agent工厂类，用于创建和管理不同类型的Agent"""
    
    _agent_types: Dict[str, Type[BaseAgent]] = {
        "chat": ChatAgent,
        "analysis": AnalysisAgent,
    }
    
    _agent_instances: Dict[str, BaseAgent] = {}
    
    @classmethod
    def register_agent(cls, agent_type: str, agent_class: Type[BaseAgent]):
        """注册新的Agent类型"""
        cls._agent_types[agent_type] = agent_class
    
    @classmethod
    def create_agent(cls, config_path: str, agent_type: str = None) -> BaseAgent:
        """创建Agent实例"""
        # 如果没有指定类型，从配置文件推断
        if not agent_type:
            from src.core.config import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.load_agent_config(config_path)
            agent_type = config.agent.type
        
        if agent_type not in cls._agent_types:
            raise ValueError(f"未知的Agent类型: {agent_type}")
        
        agent_class = cls._agent_types[agent_type]
        return agent_class(config_path)
    
    @classmethod
    def get_or_create_agent(cls, config_path: str, agent_type: str = None) -> BaseAgent:
        """获取或创建Agent实例（单例模式）"""
        key = f"{config_path}:{agent_type}"
        
        if key not in cls._agent_instances:
            cls._agent_instances[key] = cls.create_agent(config_path, agent_type)
        
        return cls._agent_instances[key]
    
    @classmethod
    def list_available_agents(cls) -> list[str]:
        """列出可用的Agent类型"""
        return list(cls._agent_types.keys())
    
    @classmethod
    def reload_agent(cls, config_path: str, agent_type: str = None):
        """重载Agent配置"""
        key = f"{config_path}:{agent_type}"
        if key in cls._agent_instances:
            del cls._agent_instances[key]
        return cls.get_or_create_agent(config_path, agent_type)