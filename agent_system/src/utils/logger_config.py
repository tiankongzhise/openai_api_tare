#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置加载器

支持从TOML配置文件加载日志配置
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    import toml
except ImportError:
    toml = None

from .logger import LoggerConfig


class LoggerConfigLoader:
    """日志配置加载器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置文件目录，默认为项目根目录下的config文件夹
        """
        if config_dir is None:
            # 默认配置目录
            current_dir = Path(__file__).parent.parent.parent
            self.config_dir = current_dir / "config"
        else:
            self.config_dir = Path(config_dir)
    
    def load_from_file(self, filename: str = "logger.toml", profile: str = "default") -> LoggerConfig:
        """
        从TOML文件加载配置
        
        Args:
            filename: 配置文件名
            profile: 配置档案名称（如default, development, production等）
            
        Returns:
            LoggerConfig: 日志配置对象
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置格式错误或缺少必要字段
        """
        if toml is None:
            raise ImportError("需要安装toml库: pip install toml")
        
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = toml.load(f)
        except Exception as e:
            raise ValueError(f"读取配置文件失败: {e}")
        
        # 获取指定档案的配置
        logger_configs = config_data.get('logger', {})
        profile_config = logger_configs.get(profile)
        
        if profile_config is None:
            available_profiles = list(logger_configs.keys())
            raise ValueError(
                f"配置档案 '{profile}' 不存在。可用档案: {available_profiles}"
            )
        
        return self._create_config_from_dict(profile_config)
    
    def _create_config_from_dict(self, config_dict: Dict[str, Any]) -> LoggerConfig:
        """
        从字典创建LoggerConfig对象
        
        Args:
            config_dict: 配置字典
            
        Returns:
            LoggerConfig: 日志配置对象
        """
        # 转换日志级别
        level = config_dict.get('level', 'INFO')
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        
        return LoggerConfig(
            name=config_dict.get('name', 'agent_system'),
            level=level,
            format_string=config_dict.get('format_string', 
                                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            detailed_mode=config_dict.get('detailed_mode', True),
            max_args_display=config_dict.get('max_args_display', 5),
            truncate_length=config_dict.get('truncate_length', 1000)
        )
    
    def load_from_env(self, env_prefix: str = "LOGGER_") -> LoggerConfig:
        """
        从环境变量加载配置
        
        Args:
            env_prefix: 环境变量前缀
            
        Returns:
            LoggerConfig: 日志配置对象
        """
        config_dict = {}
        
        # 映射环境变量到配置字段
        env_mappings = {
            f"{env_prefix}NAME": 'name',
            f"{env_prefix}LEVEL": 'level',
            f"{env_prefix}FORMAT": 'format_string',
            f"{env_prefix}DETAILED_MODE": 'detailed_mode',
            f"{env_prefix}MAX_ARGS_DISPLAY": 'max_args_display',
            f"{env_prefix}TRUNCATE_LENGTH": 'truncate_length'
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # 类型转换
                if config_key in ['detailed_mode']:
                    config_dict[config_key] = value.lower() in ('true', '1', 'yes', 'on')
                elif config_key in ['max_args_display', 'truncate_length']:
                    config_dict[config_key] = int(value)
                else:
                    config_dict[config_key] = value
        
        # 如果没有从环境变量获取到任何配置，使用默认配置
        if not config_dict:
            return LoggerConfig()
        
        return self._create_config_from_dict(config_dict)
    
    def get_available_profiles(self, filename: str = "logger.toml") -> list:
        """
        获取可用的配置档案列表
        
        Args:
            filename: 配置文件名
            
        Returns:
            list: 可用档案名称列表
        """
        if toml is None:
            return []
        
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            return []
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = toml.load(f)
            
            logger_configs = config_data.get('logger', {})
            return list(logger_configs.keys())
        except Exception:
            return []


# 便捷函数
def load_logger_config(profile: str = "default", 
                      config_file: str = "logger.toml",
                      config_dir: Optional[str] = None) -> LoggerConfig:
    """
    便捷函数：加载日志配置
    
    Args:
        profile: 配置档案名称
        config_file: 配置文件名
        config_dir: 配置文件目录
        
    Returns:
        LoggerConfig: 日志配置对象
    """
    loader = LoggerConfigLoader(config_dir)
    return loader.load_from_file(config_file, profile)


def load_logger_config_from_env(env_prefix: str = "LOGGER_") -> LoggerConfig:
    """
    便捷函数：从环境变量加载日志配置
    
    Args:
        env_prefix: 环境变量前缀
        
    Returns:
        LoggerConfig: 日志配置对象
    """
    loader = LoggerConfigLoader()
    return loader.load_from_env(env_prefix)


def get_available_logger_profiles(config_file: str = "logger.toml",
                                config_dir: Optional[str] = None) -> list:
    """
    便捷函数：获取可用的日志配置档案
    
    Args:
        config_file: 配置文件名
        config_dir: 配置文件目录
        
    Returns:
        list: 可用档案名称列表
    """
    loader = LoggerConfigLoader(config_dir)
    return loader.get_available_profiles(config_file)