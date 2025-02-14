"""
日志工具测试模块
"""

import os
import pytest
from pathlib import Path
from src.utils.logger import get_logger, LoggerManager

@pytest.fixture
def cleanup_log_file():
    """测试前后清理日志文件"""
    log_file = Path("data/poker.log")
    if log_file.exists():
        os.remove(log_file)
    yield
    if log_file.exists():
        os.remove(log_file)

def test_logger_creation(cleanup_log_file):
    """测试日志记录器创建"""
    logger = get_logger("test")
    assert logger is not None
    assert logger.name == "test"
    
def test_log_file_creation(cleanup_log_file):
    """测试日志文件创建"""
    logger = get_logger("test")
    logger.info("Test message")
    assert Path("data/poker.log").exists()
    
def test_singleton_logger_manager():
    """测试LoggerManager是否为单例"""
    manager1 = LoggerManager()
    manager2 = LoggerManager()
    assert manager1 is manager2
    
def test_logger_caching():
    """测试日志记录器缓存"""
    logger1 = get_logger("test_cache")
    logger2 = get_logger("test_cache")
    assert logger1 is logger2
    
def test_log_levels():
    """测试不同日志级别"""
    logger = get_logger("test_levels")
    log_file = Path("data/poker.log")
    
    # 清理之前的日志
    if log_file.exists():
        os.remove(log_file)
    
    # 测试不同级别的日志
    test_messages = {
        "debug": "Debug message",
        "info": "Info message",
        "warning": "Warning message",
        "error": "Error message",
        "critical": "Critical message"
    }
    
    for level, message in test_messages.items():
        getattr(logger, level)(message)
    
    # 验证日志文件存在并包含消息
    assert log_file.exists()
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
        for message in test_messages.values():
            assert message in content 