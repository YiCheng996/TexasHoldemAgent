"""
记忆管理模块。
实现智能体的短期和长期记忆管理。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

import chromadb
from chromadb.config import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class Memory:
    """记忆数据类"""
    timestamp: datetime
    phase: str
    hand_cards: List[str]
    community_cards: List[str]
    pot_size: int
    current_bet: int
    round_actions: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)

class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化记忆管理器
        
        Args:
            config: 配置信息
        """
        self.config = config
        self.short_term_config = config["memory"]["short_term"]
        self.long_term_config = config["memory"]["long_term"]
        
        # 短期记忆
        self.short_term_memory: List[Memory] = []
        self.max_rounds = self.short_term_config["max_rounds"]
        
        # 长期记忆
        persist_dir = os.path.join("data", "memories")
        if not os.path.exists(persist_dir):
            os.makedirs(persist_dir)
            
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            self.collection = self._init_collection()
        except Exception as e:
            logger.error(f"初始化向量数据库失败: {e}")
            raise
            
        logger.info("Memory manager initialized")
    
    def _init_collection(self) -> chromadb.Collection:
        """初始化向量数据库集合"""
        collection_name = self.long_term_config["collection"]
        try:
            # 检查集合是否存在
            try:
                collection = self.chroma_client.get_collection(collection_name)
                logger.info(f"使用已存在的集合: {collection_name}")
                return collection
            except Exception:
                # 集合不存在，创建新的集合
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"description": "Poker game memories"}
                )
                logger.info(f"创建新集合: {collection_name}")
                return collection
                
        except Exception as e:
            logger.error(f"初始化集合失败: {e}")
            raise
    
    def add_memory(self, memory: Memory) -> None:
        """
        添加新记忆
        
        Args:
            memory: 记忆数据
        """
        # 更新短期记忆
        self.short_term_memory.append(memory)
        if len(self.short_term_memory) > self.max_rounds:
            self.short_term_memory.pop(0)
        
        # 更新长期记忆
        self._store_in_vector_db(memory)
        
        logger.debug(f"Added memory at {memory.timestamp}")
    
    def _store_in_vector_db(self, memory: Memory) -> None:
        """
        将记忆存储到向量数据库
        
        Args:
            memory: 记忆数据
        """
        try:
            # 将记忆转换为文本
            text = self._memory_to_text(memory)
            
            # 存储到向量数据库
            self.collection.add(
                documents=[text],
                metadatas=[{
                    "timestamp": memory.timestamp.isoformat(),
                    "phase": memory.phase,
                    **memory.metadata
                }],
                ids=[f"memory_{datetime.now().timestamp()}"]
            )
        except Exception as e:
            logger.error(f"存储记忆到向量数据库失败: {e}")
            # 不抛出异常，继续执行
    
    def _memory_to_text(self, memory: Memory) -> str:
        """
        将记忆转换为文本格式
        
        Args:
            memory: 记忆数据
            
        Returns:
            str: 文本格式的记忆
        """
        actions = []
        for action in memory.round_actions:
            actions.append(f"{action['player_id']}: {action['action_type']}")
            
        return (
            f"阶段: {memory.phase}\n"
            f"手牌: {', '.join(memory.hand_cards)}\n"
            f"公共牌: {', '.join(memory.community_cards)}\n"
            f"底池: {memory.pot_size}\n"
            f"当前下注: {memory.current_bet}\n"
            f"行动: {', '.join(actions)}"
        )
    
    def query_similar_memories(
        self,
        query: str,
        n_results: int = None,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        查询相似记忆
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            threshold: 相似度阈值
            
        Returns:
            List[Dict]: 相似记忆列表
        """
        if n_results is None:
            n_results = self.long_term_config["max_results"]
        if threshold is None:
            threshold = self.long_term_config["similarity_threshold"]
            
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        memories = []
        for i, doc in enumerate(results["documents"][0]):
            if results["distances"][0][i] < threshold:
                memories.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i],
                    "similarity": results["distances"][0][i]
                })
                
        return memories
    
    def get_recent_memories(self, n: int = None) -> List[Memory]:
        """
        获取最近的记忆
        
        Args:
            n: 返回数量，默认返回全部
            
        Returns:
            List[Memory]: 记忆列表
        """
        if n is None:
            return self.short_term_memory
        return self.short_term_memory[-n:]
    
    def clear_short_term(self) -> None:
        """清空短期记忆"""
        self.short_term_memory = []
        logger.info("Short-term memory cleared")
    
    def prune_long_term(self, days: int = 30) -> None:
        """
        清理长期记忆
        
        Args:
            days: 保留最近几天的记忆
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        self.collection.delete(
            where={"timestamp": {"$lt": cutoff}}
        )
        logger.info(f"Pruned memories older than {days} days")
    
    def save(self, path: str) -> None:
        """
        保存记忆状态
        
        Args:
            path: 保存路径
        """
        state = {
            "short_term": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "phase": m.phase,
                    "hand_cards": m.hand_cards,
                    "community_cards": m.community_cards,
                    "pot_size": m.pot_size,
                    "current_bet": m.current_bet,
                    "round_actions": m.round_actions,
                    "metadata": m.metadata
                }
                for m in self.short_term_memory
            ]
        }
        
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
            
        logger.info(f"Memory state saved to {path}")
    
    def load(self, path: str) -> None:
        """
        加载记忆状态
        
        Args:
            path: 加载路径
        """
        with open(path, "r") as f:
            state = json.load(f)
            
        self.short_term_memory = [
            Memory(
                timestamp=datetime.fromisoformat(m["timestamp"]),
                phase=m["phase"],
                hand_cards=m["hand_cards"],
                community_cards=m["community_cards"],
                pot_size=m["pot_size"],
                current_bet=m["current_bet"],
                round_actions=m["round_actions"],
                metadata=m["metadata"]
            )
            for m in state["short_term"]
        ]
        
        logger.info(f"Memory state loaded from {path}")

    def cleanup(self) -> None:
        """清理资源"""
        try:
            if hasattr(self, "collection"):
                collection_name = self.collection.name
                self.chroma_client.delete_collection(collection_name)
            if hasattr(self, "chroma_client"):
                self.chroma_client.reset()
        except Exception as e:
            logger.error(f"清理资源失败: {e}")

    def __del__(self):
        """析构函数，确保资源被正确清理"""
        self.cleanup()
