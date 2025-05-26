import logging
import time
import functools
from typing import Any, Callable, Optional, Union, Dict
from datetime import datetime
import json


class LoggerConfig:
    """日志配置类"""
    def __init__(
        self,
        name: str = "agent_system",
        level: Union[str, int] = logging.INFO,
        format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        detailed_mode: bool = True,
        max_args_display: int = 5,
        truncate_length: int = 1000
    ):
        self.name = name
        self.level = level
        self.format_string = format_string
        self.detailed_mode = detailed_mode
        self.max_args_display = max_args_display
        self.truncate_length = truncate_length


class UniversalLogger:
    """通用日志器，支持多种第三方日志库"""
    
    def __init__(self, config: Optional[LoggerConfig] = None):
        self.config = config or LoggerConfig()
        self._logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志器"""
        # 默认使用Python标准日志器
        self._logger = logging.getLogger(self.config.name)
        self._logger.setLevel(self.config.level)
        
        # 避免重复添加handler
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(self.config.format_string)
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
    
    def _format_args(self, args: tuple, kwargs: dict) -> str:
        """格式化参数"""
        if self.config.detailed_mode:
            return self._format_detailed_args(args, kwargs)
        else:
            return self._format_brief_args(args, kwargs)
    
    def _format_detailed_args(self, args: tuple, kwargs: dict) -> str:
        """详细模式格式化参数"""
        try:
            args_str = [self._truncate_value(str(arg)) for arg in args]
            kwargs_str = {k: self._truncate_value(str(v)) for k, v in kwargs.items()}
            return f"args={args_str}, kwargs={kwargs_str}"
        except Exception:
            return "args=<serialization_error>, kwargs=<serialization_error>"
    
    def _format_brief_args(self, args: tuple, kwargs: dict) -> str:
        """简要模式格式化参数"""
        try:
            total_args = len(args) + len(kwargs)
            if total_args <= self.config.max_args_display:
                return self._format_detailed_args(args, kwargs)
            
            # 处理位置参数
            if len(args) > 4:
                args_display = list(args[:2]) + ["..."] + list(args[-2:])
            else:
                args_display = list(args)
            
            # 处理关键字参数
            kwargs_items = list(kwargs.items())
            if len(kwargs_items) > 4:
                kwargs_display = dict(kwargs_items[:2])
                kwargs_display["..."] = "..."
                kwargs_display.update(dict(kwargs_items[-2:]))
            else:
                kwargs_display = kwargs
            
            args_str = [self._truncate_value(str(arg)) for arg in args_display]
            kwargs_str = {k: self._truncate_value(str(v)) for k, v in kwargs_display.items()}
            return f"args={args_str}, kwargs={kwargs_str}"
        except Exception:
            return "args=<serialization_error>, kwargs=<serialization_error>"
    
    def _truncate_value(self, value: str) -> str:
        """截断过长的值"""
        if len(value) > self.config.truncate_length:
            return value[:self.config.truncate_length] + "..."
        return value
    
    def _format_return_value(self, result: Any) -> str:
        """格式化返回值"""
        try:
            return self._truncate_value(str(result))
        except Exception:
            return "<serialization_error>"
    
    def debug(self, message: str, *args, **kwargs):
        """记录debug级别日志"""
        self._logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """记录info级别日志"""
        self._logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """记录warning级别日志"""
        self._logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """记录error级别日志"""
        self._logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """记录critical级别日志"""
        self._logger.critical(message, *args, **kwargs)
    
    def log_execution(self, func: Callable) -> Callable:
        """装饰器：记录函数执行信息"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            start_time = time.time()
            start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            
            # 记录开始信息
            args_info = self._format_args(args, kwargs)
            self.info(f"[CALL_START] {func_name} | 开始时间: {start_datetime} | 参数: {args_info}")
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录成功结束信息
                end_time = time.time()
                end_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                duration = end_time - start_time
                
                return_info = self._format_return_value(result)
                self.info(
                    f"[CALL_SUCCESS] {func_name} | "
                    f"结束时间: {end_datetime} | "
                    f"耗时: {duration:.4f}秒 | "
                    f"返回值: {return_info}"
                )
                
                return result
                
            except Exception as e:
                # 记录异常信息
                end_time = time.time()
                end_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                duration = end_time - start_time
                
                self.error(
                    f"[CALL_ERROR] {func_name} | "
                    f"结束时间: {end_datetime} | "
                    f"耗时: {duration:.4f}秒 | "
                    f"异常: {str(e)}"
                )
                raise
        
        return wrapper


# 全局日志器实例
_default_logger = None


def get_logger(config: Optional[LoggerConfig] = None) -> UniversalLogger:
    """获取日志器实例"""
    global _default_logger
    if _default_logger is None or config is not None:
        _default_logger = UniversalLogger(config)
    return _default_logger


def set_logger_config(config: LoggerConfig):
    """设置全局日志器配置"""
    global _default_logger
    _default_logger = UniversalLogger(config)


# 便捷函数
def debug(message: str, *args, **kwargs):
    """记录debug级别日志"""
    get_logger().debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs):
    """记录info级别日志"""
    get_logger().info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs):
    """记录warning级别日志"""
    get_logger().warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs):
    """记录error级别日志"""
    get_logger().error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs):
    """记录critical级别日志"""
    get_logger().critical(message, *args, **kwargs)


def log_execution(func: Callable) -> Callable:
    """装饰器：记录函数执行信息"""
    return get_logger().log_execution(func)


# 支持第三方日志库的扩展
class LogrusAdapter(UniversalLogger):
    """Logrus风格的日志适配器示例"""
    
    def __init__(self, config: Optional[LoggerConfig] = None):
        super().__init__(config)
    
    def with_fields(self, **fields) -> 'LogrusAdapter':
        """添加字段（模拟logrus的WithFields）"""
        # 这里可以实现字段添加逻辑
        return self


class StructlogAdapter(UniversalLogger):
    """Structlog风格的日志适配器示例"""
    
    def __init__(self, config: Optional[LoggerConfig] = None):
        super().__init__(config)
    
    def bind(self, **kwargs) -> 'StructlogAdapter':
        """绑定上下文（模拟structlog的bind）"""
        # 这里可以实现上下文绑定逻辑
        return self