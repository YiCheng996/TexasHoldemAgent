"""
配置加载工具。
提供配置文件的加载和验证功能。
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import os
from copy import deepcopy
import sys

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 默认配置文件路径
DEFAULT_CONFIG_PATHS = {
    'llm': 'config/llm.yml',
    'game': 'config/game.yml'
}

# 配置缓存
_config_cache: Dict[str, Dict[str, Any]] = {}
# 记录已加载的配置文件
_loaded_files = set()

def load_config(config_type: str = None, config_path: str = None, force_reload: bool = False) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_type: 配置类型 ('llm' 或 'game')
        config_path: 自定义配置文件路径
        force_reload: 是否强制重新加载
        
    Returns:
        Dict[str, Any]: 配置字典
    """
    try:
        # 生成缓存键
        cache_key = config_path if config_path else config_type
        
        # 如果不强制重新加载且配置已缓存，直接返回缓存的配置
        if not force_reload and cache_key in _config_cache:
            return deepcopy(_config_cache[cache_key])
        
        # 获取项目根目录
        root_dir = Path(__file__).parent.parent.parent
        
        # 确定配置文件路径
        if config_path:
            full_path = root_dir / config_path
        elif config_type and config_type in DEFAULT_CONFIG_PATHS:
            full_path = root_dir / DEFAULT_CONFIG_PATHS[config_type]
        else:
            raise ValueError("必须指定config_type或config_path")
            
        # 检查文件是否存在
        if not full_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {full_path}")
            
        # 读取配置文件
        with open(full_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # 处理环境变量
        _process_env_vars(config)
        
        # 缓存配置
        _config_cache[cache_key] = deepcopy(config)
        
        # 只在第一次加载时或强制重新加载时记录日志
        file_path_str = str(full_path)
        if force_reload or file_path_str not in _loaded_files:
            # 检查是否在开发环境中
            is_dev = any(arg in sys.argv[0] for arg in ['uvicorn', 'development', 'reload'])
            if not is_dev or force_reload:
                logger.info(f"成功加载配置文件: {full_path}")
            _loaded_files.add(file_path_str)
        
        return config
        
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        raise

def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并多个配置字典
    
    Args:
        *configs: 要合并的配置字典
        
    Returns:
        Dict[str, Any]: 合并后的配置字典
    """
    result = {}
    for config in configs:
        _deep_update(result, deepcopy(config))
    return result

def _deep_update(base: Dict[str, Any], update: Dict[str, Any]) -> None:
    """
    递归更新字典
    
    Args:
        base: 基础字典
        update: 更新字典
    """
    for key, value in update.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _deep_update(base[key], value)
        else:
            base[key] = value

def _process_env_vars(config: Dict[str, Any]) -> None:
    """
    处理配置中的环境变量
    
    Args:
        config: 配置字典
    """
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                env_value = os.getenv(env_var)
                if env_value is None:
                    # 为API密钥提供默认值
                    if key == "api_key" and "provider" in config:
                        if config["provider"] == "openai":
                            config[key] = "95285665986d43ad84eeeb3506e1150d.USTAijnoWSy6ADHc"
                        elif config["provider"] == "anthropic":
                            config[key] = "dummy-anthropic-key"
                    else:
                        logger.warning(f"环境变量 {env_var} 未设置，使用原始值")
                        config[key] = value
                else:
                    config[key] = env_value
            elif isinstance(value, (dict, list)):
                _process_env_vars(value)
    elif isinstance(config, list):
        for item in config:
            if isinstance(item, (dict, list)):
                _process_env_vars(item)

def validate_config(config: Dict[str, Any], required_fields: Dict[str, type]) -> bool:
    """
    验证配置是否包含所需字段
    
    Args:
        config: 配置字典
        required_fields: 必需字段及其类型的字典
        
    Returns:
        bool: 验证是否通过
    """
    try:
        for field, field_type in required_fields.items():
            if field not in config:
                raise ValueError(f"缺少必需的配置字段: {field}")
            if not isinstance(config[field], field_type):
                raise TypeError(f"配置字段 {field} 的类型应为 {field_type.__name__}，"
                              f"实际为 {type(config[field]).__name__}")
        return True
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        return False

def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    获取配置值，支持点号分隔的路径
    
    Args:
        config: 配置字典
        key_path: 键路径，如 "models.default.api_key"
        default: 默认值
        
    Returns:
        Any: 配置值
    """
    try:
        current = config
        for key in key_path.split('.'):
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default

def clear_config_cache() -> None:
    """清除配置缓存"""
    global _config_cache, _loaded_files
    _config_cache.clear()
    _loaded_files.clear()
    logger.info("配置缓存已清除") 