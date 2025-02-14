"""
数据库管理模块。
提供数据库连接和基本操作的封装。
"""

import yaml
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from src.utils.logger import get_logger
from .models import Base

logger = get_logger(__name__)

class DatabaseManager:
    """数据库管理器，负责数据库连接和会话管理"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.config = self._load_config()
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
    def _load_config(self) -> dict:
        """加载数据库配置"""
        config_path = Path("config/game.yml")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('database', {})
        except Exception as e:
            logger.warning(f"Could not load database config: {e}")
            return {
                'url': 'sqlite:///data/poker.db',
                'echo': False
            }
    
    def _create_engine(self):
        """创建数据库引擎"""
        return create_engine(
            self.config.get('url', 'sqlite:///data/poker.db'),
            echo=self.config.get('echo', False),
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
    
    def create_database(self):
        """创建数据库表"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话的上下文管理器"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

# 创建全局数据库管理器实例
db_manager = DatabaseManager()

def init_database():
    """初始化数据库"""
    db_manager.create_database()

def get_db() -> Generator[Session, None, None]:
    """获取数据库会话的便捷方法"""
    with db_manager.get_session() as session:
        yield session 