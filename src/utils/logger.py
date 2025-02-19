"""
日志工具模块，提供统一的日志记录功能。
支持从配置文件读取配置，支持文件和控制台输出，支持不同级别的日志记录。
"""

import logging
import logging.handlers
import os
import yaml
import tempfile
import atexit
import sys
from pathlib import Path
from typing import Optional, Dict
from threading import Lock

class LoggerManager:
    """日志管理器，负责创建和管理日志实例"""
    
    _instance = None
    _loggers: Dict[str, logging.Logger] = {}
    _file_handlers: Dict[str, logging.Handler] = {}
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.config = self._load_config()
        self._setup_log_directory()
        atexit.register(self._cleanup)
        
    def _load_config(self) -> dict:
        """加载日志配置"""
        config_path = Path("config/game.yml")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('logging', {})
        except Exception as e:
            # 如果无法读取配置文件，使用默认配置
            print(f"Warning: Could not load logging config: {e}")
            return {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'data/poker.log'
            }
    
    def _setup_log_directory(self):
        """确保日志目录存在"""
        log_file = self.config.get('file', 'data/poker.log')
        log_dir = os.path.dirname(log_file)
        if log_dir:  # 如果目录不为空
            os.makedirs(log_dir, exist_ok=True)
            
    def _cleanup(self):
        """清理资源"""
        with self._lock:
            for handler in self._file_handlers.values():
                try:
                    handler.close()
                except:
                    pass
            self._file_handlers.clear()
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取或创建一个命名的日志记录器
        
        Args:
            name: 日志记录器名称，通常使用模块名
            
        Returns:
            logging.Logger: 配置好的日志记录器
        """
        with self._lock:
            if name in self._loggers:
                return self._loggers[name]
                
            logger = logging.getLogger(name)
            level = getattr(logging, self.config.get('level', 'INFO').upper())
            logger.setLevel(level)
            
            # 如果logger没有处理器，添加处理器
            if not logger.handlers:
                try:
                    # 在测试环境中使用临时文件
                    if 'pytest' in sys.modules:
                        log_dir = tempfile.gettempdir()
                        log_file = os.path.join(log_dir, f'poker_test_{name}.log')
                    else:
                        log_file = self.config.get('file', 'data/poker.log')
                        log_dir = os.path.dirname(log_file)
                        if log_dir:
                            os.makedirs(log_dir, exist_ok=True)
                        
                    # 添加文件处理器，使用完整格式
                    file_handler = logging.handlers.RotatingFileHandler(
                        log_file,
                        maxBytes=10*1024*1024,  # 10MB
                        backupCount=5,
                        encoding='utf-8',
                        delay=True  # 延迟创建文件，直到第一次写入
                    )
                    file_handler.setFormatter(
                        logging.Formatter(self.config.get('format'))
                    )
                    logger.addHandler(file_handler)
                    self._file_handlers[name] = file_handler
                except (PermissionError, OSError) as e:
                    # 如果无法访问日志文件，只使用控制台输出
                    print(f"Warning: Could not create file handler: {e}")
                    
                # 添加控制台处理器，使用简化格式
                console_handler = logging.StreamHandler()
                # 为LLM相关的日志使用特殊格式
                if name.startswith("Agent_"):
                    console_format = '%(message)s'  # 只显示消息内容
                else:
                    # 使用简化的控制台格式，只包含时间和消息
                    console_format = '%(asctime)s - %(message)s'
                    
                console_handler.setFormatter(logging.Formatter(console_format))
                logger.addHandler(console_handler)
                
            self._loggers[name] = logger
            return logger
            
    def remove_logger(self, name: str):
        """
        移除一个日志记录器
        
        Args:
            name: 要移除的日志记录器名称
        """
        with self._lock:
            if name not in self._loggers:
                return
                
            logger = self._loggers[name]
            
            # 关闭并移除文件处理器
            if name in self._file_handlers:
                self._file_handlers[name].close()
                del self._file_handlers[name]
                
            # 关闭并移除所有处理器
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
                
            del self._loggers[name]

# 创建全局日志管理器实例
logger_manager = LoggerManager()

def get_logger(name: str) -> logging.Logger:
    """
    获取一个命名的日志记录器的便捷方法
    
    Args:
        name: 日志记录器名称，通常使用模块名
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    return logger_manager.get_logger(name)

def reset_logger(name: str) -> None:
    """
    重置指定的日志记录器
    
    Args:
        name: 日志记录器名称
    """
    logger_manager.reset_logger(name)

# 为了便于测试，创建一个默认的日志记录器
default_logger = get_logger("default")
