# 通用日志模块

一个功能强大、灵活配置的Python日志模块，支持多种使用方式和配置选项。

## 功能特性

### 🚀 核心功能
- **多种调用方式**: 支持直接调用和装饰器调用
- **详细执行跟踪**: 记录函数调用时间、参数、返回值和异常
- **灵活配置**: 支持配置文件和环境变量配置
- **多模式支持**: 详细模式和简要模式可切换
- **第三方库兼容**: 可扩展支持各种第三方日志库

### 📊 装饰器功能
- 自动记录函数名称、模块路径
- 精确的开始时间和结束时间
- 计算总执行耗时
- 智能参数格式化（支持详细/简要模式）
- 异常捕获和记录

### ⚙️ 配置选项
- **详细模式**: 记录所有参数和返回值
- **简要模式**: 超过5个参数时只显示前2个和后2个，中间用`...`替换
- **参数截断**: 防止过长参数影响日志可读性
- **多环境配置**: 支持开发、测试、生产等不同环境配置

## 快速开始

### 基本使用

```python
from src.utils.logger import debug, info, warning, error, log_execution

# 直接调用日志方法
info("这是一条信息日志")
error("这是一条错误日志")

# 使用装饰器
@log_execution
def my_function(name: str, age: int) -> str:
    return f"Hello, {name}! You are {age} years old."

result = my_function("Alice", 25)
```

### 配置文件使用

```python
from src.utils.logger_config import load_logger_config
from src.utils.logger import set_logger_config, get_logger

# 加载开发环境配置
config = load_logger_config(profile='development')
set_logger_config(config)

logger = get_logger()
logger.info("使用开发环境配置")
```

### 环境变量配置

```bash
# 设置环境变量
export LOGGER_NAME=my_app
export LOGGER_LEVEL=DEBUG
export LOGGER_DETAILED_MODE=true
export LOGGER_MAX_ARGS_DISPLAY=8
export LOGGER_TRUNCATE_LENGTH=1500
```

```python
from src.utils.logger_config import load_logger_config_from_env
from src.utils.logger import set_logger_config

# 从环境变量加载配置
config = load_logger_config_from_env()
set_logger_config(config)
```

## 详细文档

### LoggerConfig 配置类

```python
class LoggerConfig:
    def __init__(
        self,
        name: str = "agent_system",           # 日志器名称
        level: Union[str, int] = logging.INFO, # 日志级别
        format_string: str = "...",            # 日志格式
        detailed_mode: bool = True,            # 是否详细模式
        max_args_display: int = 5,             # 简要模式最大参数显示数
        truncate_length: int = 1000            # 参数截断长度
    )
```

### 装饰器输出示例

#### 详细模式
```
[CALL_START] module.function | 开始时间: 2024-01-01 12:00:00.123456 | 参数: args=['arg1', 'arg2'], kwargs={'key1': 'value1', 'key2': 'value2'}
[CALL_SUCCESS] module.function | 结束时间: 2024-01-01 12:00:00.234567 | 耗时: 0.1111秒 | 返回值: result_value
```

#### 简要模式（超过5个参数）
```
[CALL_START] module.function | 开始时间: 2024-01-01 12:00:00.123456 | 参数: args=['arg1', 'arg2', '...', 'arg9', 'arg10'], kwargs={'key1': 'value1', 'key2': 'value2', '...': '...', 'key9': 'value9', 'key10': 'value10'}
```

### 配置文件格式

配置文件使用TOML格式，支持多个配置档案：

```toml
[logger.default]
name = "agent_system"
level = "INFO"
format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
detailed_mode = true
max_args_display = 5
truncate_length = 1000

[logger.development]
name = "dev_logger"
level = "DEBUG"
format_string = "[%(levelname)s] %(asctime)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
detailed_mode = true
max_args_display = 10
truncate_length = 2000

[logger.production]
name = "prod_logger"
level = "INFO"
format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
detailed_mode = false
max_args_display = 3
truncate_length = 500
```

## API 参考

### 直接调用函数

```python
# 基本日志方法
debug(message, *args, **kwargs)
info(message, *args, **kwargs)
warning(message, *args, **kwargs)
error(message, *args, **kwargs)
critical(message, *args, **kwargs)

# 装饰器
@log_execution
def your_function():
    pass
```

### 配置管理

```python
# 配置加载
load_logger_config(profile="default", config_file="logger.toml")
load_logger_config_from_env(env_prefix="LOGGER_")
get_available_logger_profiles(config_file="logger.toml")

# 日志器管理
get_logger(config=None)
set_logger_config(config)
```

### UniversalLogger 类

```python
logger = UniversalLogger(config)

# 基本方法
logger.debug(message)
logger.info(message)
logger.warning(message)
logger.error(message)
logger.critical(message)

# 装饰器方法
@logger.log_execution
def function():
    pass
```

## 使用示例

### 示例1: 基本使用

```python
from src.utils.logger import info, log_execution
import time

@log_execution
def process_data(data_list: list, multiplier: int = 2) -> list:
    """处理数据列表"""
    time.sleep(0.1)  # 模拟处理时间
    return [x * multiplier for x in data_list]

# 使用函数
info("开始处理数据")
result = process_data([1, 2, 3, 4, 5], multiplier=3)
info(f"处理完成，结果: {result}")
```

输出:
```
2024-01-01 12:00:00,123 - agent_system - INFO - 开始处理数据
2024-01-01 12:00:00,124 - agent_system - INFO - [CALL_START] __main__.process_data | 开始时间: 2024-01-01 12:00:00.124567 | 参数: args=[[1, 2, 3, 4, 5]], kwargs={'multiplier': 3}
2024-01-01 12:00:00,234 - agent_system - INFO - [CALL_SUCCESS] __main__.process_data | 结束时间: 2024-01-01 12:00:00.234567 | 耗时: 0.1100秒 | 返回值: [3, 6, 9, 12, 15]
2024-01-01 12:00:00,235 - agent_system - INFO - 处理完成，结果: [3, 6, 9, 12, 15]
```

### 示例2: 多环境配置

```python
from src.utils.logger_config import load_logger_config
from src.utils.logger import set_logger_config, log_execution

# 根据环境加载不同配置
import os
env = os.getenv('APP_ENV', 'development')
config = load_logger_config(profile=env)
set_logger_config(config)

@log_execution
def api_call(endpoint: str, params: dict) -> dict:
    """API调用示例"""
    # 模拟API调用
    import time
    time.sleep(0.05)
    return {"status": "success", "data": params}

# 在不同环境下会有不同的日志输出格式和详细程度
result = api_call("/api/users", {"page": 1, "limit": 10})
```

### 示例3: 异常处理

```python
from src.utils.logger import error, log_execution

@log_execution
def risky_operation(value: int) -> int:
    """可能出错的操作"""
    if value < 0:
        raise ValueError("值不能为负数")
    return value * 2

try:
    result = risky_operation(-5)
except ValueError as e:
    error(f"操作失败: {e}")
```

输出:
```
2024-01-01 12:00:00,123 - agent_system - INFO - [CALL_START] __main__.risky_operation | 开始时间: 2024-01-01 12:00:00.123456 | 参数: args=[-5], kwargs={}
2024-01-01 12:00:00,124 - agent_system - ERROR - [CALL_ERROR] __main__.risky_operation | 结束时间: 2024-01-01 12:00:00.124567 | 耗时: 0.0011秒 | 异常: 值不能为负数
2024-01-01 12:00:00,125 - agent_system - ERROR - 操作失败: 值不能为负数
```

## 扩展功能

### 第三方日志库适配

模块设计支持扩展到第三方日志库：

```python
class LogrusAdapter(UniversalLogger):
    """Logrus风格适配器"""
    def with_fields(self, **fields):
        # 实现字段添加逻辑
        return self

class StructlogAdapter(UniversalLogger):
    """Structlog风格适配器"""
    def bind(self, **kwargs):
        # 实现上下文绑定逻辑
        return self
```

## 最佳实践

1. **环境配置**: 在不同环境使用不同的配置档案
2. **参数控制**: 在生产环境使用简要模式以减少日志量
3. **异常记录**: 使用装饰器自动捕获和记录异常
4. **性能监控**: 利用执行时间记录进行性能分析
5. **敏感信息**: 注意不要在日志中记录敏感信息

## 文件结构

```
src/utils/
├── logger.py              # 核心日志模块
└── logger_config.py        # 配置加载器

config/
└── logger.toml            # 日志配置文件

examples/
├── logger_example.py      # 基本使用示例
└── logger_config_example.py # 配置使用示例
```

## 依赖要求

- Python >= 3.7
- toml (用于配置文件支持)

安装依赖:
```bash
pip install toml
```

## 许可证

本模块遵循项目的整体许可证。