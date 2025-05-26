import os
import toml
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class LLMConfig(BaseModel):
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    system_prompt: Optional[str] = None

class AgentConfig(BaseModel):
    type: str
    name: str
    description: str

class FeaturesConfig(BaseModel):
    enable_memory: bool = False
    enable_context: bool = False
    max_history: int = 10

class ValidationConfig(BaseModel):
    max_input_length: int = 1000
    required_fields: list[str] = Field(default_factory=list)

class Config(BaseModel):
    agent: AgentConfig
    llm: LLMConfig
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)

class ConfigManager:
    def __init__(self):
        self.base_config = self._load_base_config()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.database_url = os.getenv("DATABASE_URL")
    
    def _load_base_config(self) -> Dict[str, Any]:
        """加载基础配置"""
        with open("config/base.toml", "r", encoding="utf-8") as f:
            return toml.load(f)
    
    def load_agent_config(self, config_path: str) -> Config:
        """加载Agent配置"""
        with open(config_path, "r", encoding="utf-8") as f:
            agent_config = toml.load(f)
        
        # 合并基础配置和Agent配置
        merged_config = {**self.base_config, **agent_config}
        return Config(**merged_config)
    
    def get_available_configs(self) -> list[str]:
        """获取可用的配置文件"""
        config_dir = "config"
        configs = []
        for file in os.listdir(config_dir):
            if file.endswith(".toml") and file != "base.toml":
                configs.append(os.path.join(config_dir, file))
        return configs