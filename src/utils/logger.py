"""
日志工具模块，提供统一的日志记录功能。
支持从配置文件读取配置，支持文件和控制台输出，支持不同级别的日志记录。
"""

import logging
import logging.handlers
import os
import yaml
from pathlib import Path
from typing import Optional

class LoggerManager:
    """日志管理器，负责创建和管理日志实例"""
    
    _instance = None
    _loggers = {}
    
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
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取或创建一个命名的日志记录器
        
        Args:
            name: 日志记录器名称，通常使用模块名
            
        Returns:
            logging.Logger: 配置好的日志记录器
        """
        if name in self._loggers:
            return self._loggers[name]
            
        logger = logging.getLogger(name)
        level = getattr(logging, self.config.get('level', 'INFO'))
        logger.setLevel(level)
        
        # 如果logger没有处理器，添加处理器
        if not logger.handlers:
            # 添加文件处理器
            log_file = self.config.get('file', 'data/poker.log')
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(
                logging.Formatter(self.config.get('format'))
            )
            logger.addHandler(file_handler)
            
            # 添加控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter(self.config.get('format'))
            )
            logger.addHandler(console_handler)
        
        self._loggers[name] = logger
        return logger

# 创建全局日志管理器实例
logger_manager = LoggerManager()

def get_logger(name: str) -> logging.Logger:
    """
    获取一个命名的日志记录器的便捷方法
    
    Args:
        name: 日志记录器名称，通常使用模块名
        
    Returns:
        logging.Logger: 配置好的日志记录器
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("这是一条信息日志")
        >>> logger.error("这是一条错误日志")
    """
    return logger_manager.get_logger(name)

# 为了便于测试，创建一个默认的日志记录器
default_logger = get_logger("default")
