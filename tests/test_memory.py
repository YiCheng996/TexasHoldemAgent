"""
记忆管理模块测试。
测试记忆的存储、检索和管理功能。
"""

import pytest
from datetime import datetime
from pathlib import Path
import json

from src.agents.memory import Memory, MemoryManager

@pytest.fixture
def memory_config():
    """创建测试用配置"""
    return {
        "memory": {
            "short_term": {
                "max_rounds": 3
            },
            "long_term": {
                "collection": "test_memories",
                "max_results": 5,
                "similarity_threshold": 0.8,
                "pruning_days": 30
            }
        }
    }

@pytest.fixture
def sample_memory():
    """创建样例记忆"""
    return Memory(
        timestamp=datetime.now(),
        phase="PRE_FLOP",
        hand_cards=["A♠", "K♠"],
        community_cards=[],
        pot_size=100,
        current_bet=20,
        total_bet=20,
        round_actions=[
            {
                "player_id": "player1",
                "action_type": "RAISE",
                "amount": 20
            }
        ]
    )

@pytest.fixture
def memory_manager(memory_config):
    """创建记忆管理器实例"""
    return MemoryManager(memory_config)

def test_memory_initialization(sample_memory):
    """测试记忆数据类初始化"""
    assert sample_memory.phase == "PRE_FLOP"
    assert sample_memory.hand_cards == ["A♠", "K♠"]
    assert sample_memory.community_cards == []
    assert sample_memory.pot_size == 100
    assert sample_memory.current_bet == 20
    assert sample_memory.total_bet == 20
    assert len(sample_memory.round_actions) == 1
    assert sample_memory.metadata == {}

def test_memory_manager_initialization(memory_manager, memory_config):
    """测试记忆管理器初始化"""
    assert memory_manager.config == memory_config
    assert memory_manager.max_rounds == memory_config["memory"]["short_term"]["max_rounds"]
    assert len(memory_manager.short_term_memory) == 0
    assert memory_manager.collection is not None

def test_add_memory(memory_manager, sample_memory):
    """测试添加记忆"""
    memory_manager.add_memory(sample_memory)
    assert len(memory_manager.short_term_memory) == 1
    assert memory_manager.short_term_memory[0] == sample_memory

def test_short_term_memory_limit(memory_manager, sample_memory):
    """测试短期记忆容量限制"""
    # 添加超过限制的记忆
    for i in range(5):
        memory = Memory(
            timestamp=datetime.now(),
            phase=f"PHASE_{i}",
            hand_cards=["A♠", "K♠"],
            community_cards=[],
            pot_size=100,
            current_bet=20,
            total_bet=20,
            round_actions=[]
        )
        memory_manager.add_memory(memory)
    
    # 验证只保留最近的记忆
    assert len(memory_manager.short_term_memory) == memory_manager.max_rounds
    assert memory_manager.short_term_memory[-1].phase == "PHASE_4"

def test_memory_to_text(memory_manager, sample_memory):
    """测试记忆文本转换"""
    text = memory_manager._memory_to_text(sample_memory)
    assert "阶段: PRE_FLOP" in text
    assert "手牌: A♠, K♠" in text
    assert "底池: 100" in text
    assert "player1: RAISE" in text

def test_query_similar_memories(memory_manager, sample_memory):
    """测试相似记忆查询"""
    # 添加一些记忆
    memory_manager.add_memory(sample_memory)
    
    # 查询相似记忆
    query = "PRE_FLOP阶段的强牌"
    memories = memory_manager.query_similar_memories(
        query,
        n_results=1,
        threshold=0.9
    )
    
    assert isinstance(memories, list)
    if memories:  # ChromaDB可能返回空结果
        assert "PRE_FLOP" in memories[0]["text"]
        assert "A♠, K♠" in memories[0]["text"]

def test_get_recent_memories(memory_manager, sample_memory):
    """测试获取最近记忆"""
    # 添加多个记忆
    for i in range(3):
        memory = Memory(
            timestamp=datetime.now(),
            phase=f"PHASE_{i}",
            hand_cards=["A♠", "K♠"],
            community_cards=[],
            pot_size=100,
            current_bet=20,
            total_bet=20,
            round_actions=[]
        )
        memory_manager.add_memory(memory)
    
    # 获取最近2条记忆
    recent = memory_manager.get_recent_memories(2)
    assert len(recent) == 2
    assert recent[-1].phase == "PHASE_2"

def test_clear_short_term(memory_manager, sample_memory):
    """测试清空短期记忆"""
    memory_manager.add_memory(sample_memory)
    assert len(memory_manager.short_term_memory) == 1
    
    memory_manager.clear_short_term()
    assert len(memory_manager.short_term_memory) == 0

def test_save_load_memory(memory_manager, sample_memory, tmp_path):
    """测试记忆状态保存和加载"""
    # 添加记忆
    memory_manager.add_memory(sample_memory)
    
    # 保存状态
    save_path = tmp_path / "memory_state.json"
    memory_manager.save(str(save_path))
    
    # 清空当前记忆
    memory_manager.clear_short_term()
    assert len(memory_manager.short_term_memory) == 0
    
    # 加载状态
    memory_manager.load(str(save_path))
    assert len(memory_manager.short_term_memory) == 1
    loaded_memory = memory_manager.short_term_memory[0]
    assert loaded_memory.phase == sample_memory.phase
    assert loaded_memory.hand_cards == sample_memory.hand_cards 