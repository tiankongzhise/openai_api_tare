#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置加载示例

演示如何使用配置文件和环境变量来管理日志配置
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import get_logger, set_logger_config, log_execution
from utils.logger_config import (
    load_logger_config,
    load_logger_config_from_env,
    get_available_logger_profiles,
    LoggerConfigLoader
)
import time


@log_execution
def sample_function(name: str, value: int, data: dict = None) -> dict:
    """示例函数用于测试不同配置"""
    if data is None:
        data = {}
    
    time.sleep(0.1)  # 模拟处理时间
    
    result = {
        "name": name,
        "processed_value": value * 2,
        "data_keys": list(data.keys()),
        "timestamp": time.time()
    }
    
    return result


def demo_config_profiles():
    """演示不同配置档案"""
    print("\n=== 配置档案演示 ===")
    
    # 获取可用的配置档案
    profiles = get_available_logger_profiles()
    print(f"可用的配置档案: {profiles}")
    
    # 测试不同的配置档案
    test_profiles = ['default', 'development', 'production', 'testing']
    
    for profile in test_profiles:
        if profile in profiles:
            print(f"\n--- 使用 {profile} 配置 ---")
            try:
                # 加载配置
                config = load_logger_config(profile=profile)
                set_logger_config(config)
                
                # 测试日志记录
                logger = get_logger()
                logger.info(f"使用 {profile} 配置记录日志")
                
                # 测试函数调用
                result = sample_function(
                    name=f"test_{profile}",
                    value=100,
                    data={"config": profile, "test": True, "extra": "data"}
                )
                print(f"函数返回: {result['name']} -> {result['processed_value']}")
                
            except Exception as e:
                print(f"加载 {profile} 配置失败: {e}")
        else:
            print(f"\n配置档案 {profile} 不存在")


def demo_environment_config():
    """演示环境变量配置"""
    print("\n=== 环境变量配置演示 ===")
    
    # 设置环境变量
    os.environ['LOGGER_NAME'] = 'env_logger'
    os.environ['LOGGER_LEVEL'] = 'DEBUG'
    os.environ['LOGGER_DETAILED_MODE'] = 'false'
    os.environ['LOGGER_MAX_ARGS_DISPLAY'] = '3'
    os.environ['LOGGER_TRUNCATE_LENGTH'] = '100'
    
    try:
        # 从环境变量加载配置
        config = load_logger_config_from_env()
        set_logger_config(config)
        
        logger = get_logger()
        logger.info("使用环境变量配置的日志")
        logger.debug("这是调试信息（应该显示，因为级别设置为DEBUG）")
        
        # 测试函数调用（简要模式）
        result = sample_function(
            name="env_test",
            value=200,
            data={"env": True, "mode": "brief", "test": "environment", "extra1": "value1", "extra2": "value2"}
        )
        print(f"环境变量配置函数返回: {result['name']} -> {result['processed_value']}")
        
    except Exception as e:
        print(f"环境变量配置失败: {e}")
    finally:
        # 清理环境变量
        for key in ['LOGGER_NAME', 'LOGGER_LEVEL', 'LOGGER_DETAILED_MODE', 
                   'LOGGER_MAX_ARGS_DISPLAY', 'LOGGER_TRUNCATE_LENGTH']:
            os.environ.pop(key, None)


def demo_custom_config_loader():
    """演示自定义配置加载器"""
    print("\n=== 自定义配置加载器演示 ===")
    
    # 创建配置加载器
    loader = LoggerConfigLoader()
    
    try:
        # 加载性能监控配置
        perf_config = loader.load_from_file(profile='performance')
        set_logger_config(perf_config)
        
        logger = get_logger()
        logger.info("性能监控模式启动")
        
        # 模拟性能监控场景
        start_time = time.time()
        
        @log_execution
        def performance_critical_function(iterations: int) -> dict:
            """性能关键函数"""
            total = 0
            for i in range(iterations):
                total += i * i
            return {"total": total, "iterations": iterations}
        
        result = performance_critical_function(1000)
        end_time = time.time()
        
        logger.info(f"性能测试完成，总耗时: {end_time - start_time:.4f}秒")
        print(f"性能测试结果: {result}")
        
    except Exception as e:
        print(f"性能配置加载失败: {e}")


def demo_config_comparison():
    """演示配置对比"""
    print("\n=== 配置对比演示 ===")
    
    configs_to_test = ['development', 'production']
    
    for profile in configs_to_test:
        print(f"\n--- {profile.upper()} 配置测试 ---")
        try:
            config = load_logger_config(profile=profile)
            set_logger_config(config)
            
            logger = get_logger()
            logger.info(f"{profile} 环境日志测试")
            
            # 使用相同的函数调用来对比不同配置的输出
            @log_execution
            def comparison_function(env: str, *args, **kwargs) -> str:
                """用于对比的函数"""
                time.sleep(0.05)
                return f"在 {env} 环境中执行完成"
            
            result = comparison_function(
                profile,
                "arg1", "arg2", "arg3", "arg4", "arg5", "arg6",
                param1="value1", param2="value2", param3="value3"
            )
            print(f"对比函数返回: {result}")
            
        except Exception as e:
            print(f"{profile} 配置测试失败: {e}")


def demo_error_handling():
    """演示错误处理"""
    print("\n=== 错误处理演示 ===")
    
    # 测试不存在的配置档案
    try:
        config = load_logger_config(profile='nonexistent')
    except ValueError as e:
        print(f"预期错误 - 不存在的配置档案: {e}")
    
    # 测试不存在的配置文件
    try:
        config = load_logger_config(config_file='nonexistent.toml')
    except FileNotFoundError as e:
        print(f"预期错误 - 不存在的配置文件: {e}")
    
    # 测试环境变量配置（无环境变量时使用默认值）
    try:
        config = load_logger_config_from_env()
        print("环境变量配置成功（使用默认值）")
    except Exception as e:
        print(f"环境变量配置失败: {e}")


if __name__ == "__main__":
    print("日志配置加载示例")
    print("=" * 60)
    
    # 运行各种演示
    demo_config_profiles()
    demo_environment_config()
    demo_custom_config_loader()
    demo_config_comparison()
    demo_error_handling()
    
    print("\n=== 演示完成 ===")
    print("\n配置功能说明:")
    print("1. 支持从TOML配置文件加载多种预设配置")
    print("2. 支持从环境变量动态配置日志参数")
    print("3. 支持不同环境（开发、测试、生产）的配置档案")
    print("4. 提供配置加载器类和便捷函数")
    print("5. 包含完整的错误处理和配置验证")
    print("6. 支持运行时动态切换配置")
    
    print("\n环境变量配置示例:")
    print("export LOGGER_NAME=my_logger")
    print("export LOGGER_LEVEL=DEBUG")
    print("export LOGGER_DETAILED_MODE=true")
    print("export LOGGER_MAX_ARGS_DISPLAY=8")
    print("export LOGGER_TRUNCATE_LENGTH=1500")