#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志模块使用示例

演示如何使用通用日志模块进行日志记录和函数调用跟踪
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import (
    LoggerConfig, 
    get_logger, 
    set_logger_config,
    log_execution,
    debug, info, warning, error, critical
)
import time
import logging


def demo_direct_logging():
    """演示直接调用日志方法"""
    print("\n=== 直接调用日志方法演示 ===")
    
    # 使用默认配置
    info("这是一条信息日志")
    debug("这是一条调试日志")
    warning("这是一条警告日志")
    error("这是一条错误日志")
    
    # 使用格式化参数
    info("用户 %s 登录成功，IP: %s", "张三", "192.168.1.100")
    
    # 使用关键字参数
    info("处理订单", extra={"order_id": "12345", "amount": 99.99})


def demo_custom_config():
    """演示自定义配置"""
    print("\n=== 自定义配置演示 ===")
    
    # 创建自定义配置
    config = LoggerConfig(
        name="custom_logger",
        level=logging.DEBUG,
        detailed_mode=False,  # 使用简要模式
        max_args_display=3,
        truncate_length=50
    )
    
    # 设置全局配置
    set_logger_config(config)
    
    info("使用自定义配置的日志")
    debug("这条调试日志现在应该可以显示了")


@log_execution
def simple_function(name: str, age: int) -> str:
    """简单函数示例"""
    time.sleep(0.1)  # 模拟处理时间
    return f"Hello, {name}! You are {age} years old."


@log_execution
def function_with_many_args(a, b, c, d, e, f, g, h, i, j, **kwargs) -> dict:
    """多参数函数示例"""
    time.sleep(0.05)
    return {"sum": sum([a, b, c, d, e, f, g, h, i, j]), "kwargs_count": len(kwargs)}


@log_execution
def function_with_exception(should_fail: bool = False):
    """可能抛出异常的函数"""
    time.sleep(0.02)
    if should_fail:
        raise ValueError("这是一个测试异常")
    return "执行成功"


@log_execution
def complex_function(data: dict, options: list = None) -> dict:
    """复杂数据类型函数示例"""
    if options is None:
        options = []
    
    time.sleep(0.08)
    
    result = {
        "processed_data": {k: v * 2 if isinstance(v, (int, float)) else v for k, v in data.items()},
        "options_count": len(options),
        "timestamp": time.time()
    }
    
    return result


def demo_decorator_logging():
    """演示装饰器日志记录"""
    print("\n=== 装饰器日志记录演示 ===")
    
    # 简单函数调用
    result1 = simple_function("Alice", 25)
    print(f"函数返回: {result1}")
    
    print("\n--- 多参数函数（简要模式）---")
    # 多参数函数调用
    result2 = function_with_many_args(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, extra1="value1", extra2="value2", extra3="value3")
    print(f"函数返回: {result2}")
    
    print("\n--- 复杂数据类型函数 ---")
    # 复杂数据类型
    complex_data = {
        "name": "测试数据",
        "value": 100,
        "nested": {"inner": "内部数据"},
        "list_data": [1, 2, 3, 4, 5]
    }
    result3 = complex_function(complex_data, ["option1", "option2"])
    print(f"函数返回: {result3}")
    
    print("\n--- 异常处理演示 ---")
    # 正常执行
    try:
        result4 = function_with_exception(False)
        print(f"正常执行结果: {result4}")
    except Exception as e:
        print(f"捕获异常: {e}")
    
    # 异常执行
    try:
        result5 = function_with_exception(True)
        print(f"异常执行结果: {result5}")
    except Exception as e:
        print(f"捕获异常: {e}")


def demo_detailed_mode():
    """演示详细模式"""
    print("\n=== 详细模式演示 ===")
    
    # 切换到详细模式
    config = LoggerConfig(
        name="detailed_logger",
        level=logging.INFO,
        detailed_mode=True,  # 详细模式
        truncate_length=200
    )
    set_logger_config(config)
    
    # 调用多参数函数
    result = function_with_many_args(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 
                                   extra1="详细模式值1", extra2="详细模式值2", extra3="详细模式值3")
    print(f"详细模式函数返回: {result}")


def demo_logger_instance():
    """演示使用日志器实例"""
    print("\n=== 日志器实例演示 ===")
    
    # 创建特定配置的日志器
    config = LoggerConfig(
        name="instance_logger",
        level=logging.DEBUG,
        format_string="[%(levelname)s] %(name)s: %(message)s",
        detailed_mode=False
    )
    
    logger = get_logger(config)
    
    # 使用实例方法
    logger.info("使用日志器实例记录信息")
    logger.debug("使用日志器实例记录调试信息")
    logger.warning("使用日志器实例记录警告")
    
    # 使用实例装饰器
    @logger.log_execution
    def instance_decorated_function(x: int, y: int) -> int:
        """使用实例装饰器的函数"""
        time.sleep(0.03)
        return x + y
    
    result = instance_decorated_function(10, 20)
    print(f"实例装饰器函数返回: {result}")


if __name__ == "__main__":
    print("日志模块使用示例")
    print("=" * 50)
    
    # 设置初始配置
    initial_config = LoggerConfig(
        name="example_logger",
        level=logging.INFO,
        detailed_mode=False  # 开始使用简要模式
    )
    set_logger_config(initial_config)
    
    # 运行各种演示
    demo_direct_logging()
    demo_custom_config()
    demo_decorator_logging()
    demo_detailed_mode()
    demo_logger_instance()
    
    print("\n=== 演示完成 ===")
    print("\n日志模块功能说明:")
    print("1. 支持直接调用 debug, info, warning, error, critical 方法")
    print("2. 支持 @log_execution 装饰器记录函数执行详情")
    print("3. 支持详细模式和简要模式切换")
    print("4. 简要模式下，超过5个参数时只显示前2个和后2个")
    print("5. 支持自定义配置和多个日志器实例")
    print("6. 记录函数调用时间、参数、返回值和异常信息")