"""
AI智能体测试模块。
测试基础Agent类和具体智能体实现。
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.agents.base import Agent, GameObservation, ActionResult, RandomAgent
from src.agents.llm import LLMAgent
from src.engine.game import ActionType, PlayerAction

@pytest.fixture
def basic_config() -> Dict[str, Any]:
    """创建基本配置"""
    return {
        "models": {
            "default": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30,
                "api_key": "test_api_key"  # 添加模拟的 API 密钥
            },
            "fallback": {
                "provider": "anthropic",
                "model": "claude-2",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30,
                "api_key": "test_api_key"  # 添加模拟的 API 密钥
            }
        },
        "memory": {
            "short_term": {
                "max_rounds": 10
            }
        },
        "personalities": [
            {
                "name": "激进型",
                "description": "倾向于加注和诈唬的激进玩家",
                "aggression_factor": 0.8,
                "bluff_frequency": 0.3
            },
            {
                "name": "保守型",
                "description": "倾向于稳健打法的保守玩家",
                "aggression_factor": 0.3,
                "bluff_frequency": 0.1
            }
        ],
        "prompts": {
            "decision_making": "测试提示词模板"
        }
    }

@pytest.fixture
def sample_observation() -> GameObservation:
    """创建样例观察"""
    return GameObservation(
        game_id="test_game",
        player_id="test_player",
        phase="PRE_FLOP",
        position=0,
        timestamp=datetime.now(),
        hand_cards=["A♠", "K♠"],
        community_cards=[],
        pot_size=100,
        current_bet=20,
        min_raise=40,
        chips=1000,
        total_bet=20,
        is_all_in=False,
        opponents=[
            {
                "player_id": "player2",
                "chips": 980,
                "total_bet": 20,
                "is_active": True,
                "is_all_in": False
            }
        ],
        round_actions=[
            PlayerAction(
                player_id="player2",
                action_type=ActionType.CALL,
                amount=20,
                timestamp=datetime.now()
            )
        ],
        game_actions=[]
    )

@pytest.fixture
def sample_result(sample_observation) -> ActionResult:
    """创建样例结果"""
    return ActionResult(
        success=True,
        action=PlayerAction(
            player_id="test_player",
            action_type=ActionType.CALL,
            amount=20,
            timestamp=datetime.now()
        ),
        reward=10.0,
        next_observation=sample_observation,
        done=False,
        info={}
    )

def test_random_agent_initialization(basic_config):
    """测试随机智能体初始化"""
    agent = RandomAgent("test_agent", basic_config)
    assert agent.agent_id == "test_agent"
    assert agent.config == basic_config
    assert agent.current_observation is None
    assert agent.episode_memory == []
    assert agent.total_reward == 0.0

def test_random_agent_observe(basic_config, sample_observation):
    """测试随机智能体观察"""
    agent = RandomAgent("test_agent", basic_config)
    agent.observe(sample_observation)
    assert agent.current_observation == sample_observation

def test_random_agent_act(basic_config, sample_observation):
    """测试随机智能体动作"""
    agent = RandomAgent("test_agent", basic_config)
    agent.observe(sample_observation)
    
    action = agent.act()
    assert isinstance(action, PlayerAction)
    assert action.player_id == "test_agent"
    assert action.action_type in [
        ActionType.FOLD,
        ActionType.CHECK,
        ActionType.CALL,
        ActionType.RAISE
    ]
    
    if action.action_type == ActionType.RAISE:
        assert action.amount >= sample_observation.min_raise
        assert action.amount <= sample_observation.chips

def test_random_agent_learn(basic_config, sample_result):
    """测试随机智能体学习"""
    agent = RandomAgent("test_agent", basic_config)
    agent.learn(sample_result)
    assert len(agent.episode_memory) == 1
    assert agent.total_reward == sample_result.reward

def test_random_agent_reset(basic_config, sample_observation, sample_result):
    """测试随机智能体重置"""
    agent = RandomAgent("test_agent", basic_config)
    agent.observe(sample_observation)
    agent.learn(sample_result)
    
    agent.reset()
    assert agent.current_observation is None
    assert agent.episode_memory == []
    assert agent.total_reward == 0.0

def test_llm_agent_initialization(basic_config):
    """测试LLM智能体初始化"""
    agent = LLMAgent("test_agent", basic_config)
    assert agent.agent_id == "test_agent"
    assert agent.config == basic_config
    assert agent.model_config == basic_config["models"]["default"]
    assert agent.fallback_config == basic_config["models"]["fallback"]
    assert agent.prompt_template == basic_config["prompts"]["decision_making"]
    assert agent.personality is not None
    assert len(agent.short_term_memory) == 0

def test_llm_agent_observe(basic_config, sample_observation):
    """测试LLM智能体观察"""
    agent = LLMAgent("test_agent", basic_config)
    agent.observe(sample_observation)
    assert agent.current_observation == sample_observation
    assert len(agent.short_term_memory) == 1
    
    memory = agent.short_term_memory[0]
    assert memory["phase"] == sample_observation.phase
    assert memory["hand_cards"] == sample_observation.hand_cards
    assert memory["pot_size"] == sample_observation.pot_size

def test_llm_agent_memory_limit(basic_config, sample_observation):
    """测试LLM智能体记忆限制"""
    agent = LLMAgent("test_agent", basic_config)
    max_rounds = basic_config["memory"]["short_term"]["max_rounds"]
    
    # 添加超过限制的观察
    for i in range(max_rounds + 5):
        agent.observe(sample_observation)
        
    assert len(agent.short_term_memory) == max_rounds
    
def test_llm_agent_generate_prompt(basic_config, sample_observation):
    """测试LLM智能体提示词生成"""
    agent = LLMAgent("test_agent", basic_config)
    agent.observe(sample_observation)
    
    prompt = agent._generate_prompt()
    assert isinstance(prompt, str)
    assert "A♠, K♠" in prompt  # 手牌
    assert "当前下注: 20" in prompt  # 当前下注
    assert "player2: CALL" in prompt  # 玩家动作

def test_llm_agent_parse_response():
    """测试LLM智能体响应解析"""
    agent = LLMAgent("test_agent", basic_config)
    
    # 有效响应
    valid_response = """
    分析当前情况...
    
    {
        "action": {
            "type": "RAISE",
            "amount": 100,
            "confidence": 0.8
        },
        "reasoning": {
            "hand_strength": "强牌",
            "position_analysis": "位置优势",
            "pot_odds": "值得跟注",
            "opponent_reads": ["对手可能弱牌"]
        },
        "table_talk": {
            "message": "我加注",
            "tone": "自信"
        }
    }
    """
    decision = agent._parse_response(valid_response)
    assert decision["action"]["type"] == "RAISE"
    assert decision["action"]["amount"] == 100
    assert decision["action"]["confidence"] == 0.8
    
    # 无效响应
    invalid_response = "这不是JSON格式"
    with pytest.raises(ValueError):
        agent._parse_response(invalid_response)

def test_llm_agent_validate_decision():
    """测试LLM智能体决策验证"""
    agent = LLMAgent("test_agent", basic_config)
    
    # 有效决策
    valid_decision = {
        "action": {
            "type": "RAISE",
            "amount": 100,
            "confidence": 0.8
        },
        "reasoning": {
            "hand_strength": "强牌"
        },
        "table_talk": {
            "message": "我加注"
        }
    }
    assert agent._validate_decision(valid_decision)
    
    # 无效决策 - 缺少必要字段
    invalid_decision = {
        "action": {
            "type": "RAISE"
        }
    }
    assert not agent._validate_decision(invalid_decision)
    
    # 无效决策 - 无效的动作类型
    invalid_decision = {
        "action": {
            "type": "INVALID",
            "amount": 100,
            "confidence": 0.8
        },
        "reasoning": {},
        "table_talk": {}
    }
    assert not agent._validate_decision(invalid_decision)

def test_llm_agent_fallback_action(basic_config, sample_observation):
    """测试LLM智能体后备动作"""
    agent = LLMAgent("test_agent", basic_config)
    agent.observe(sample_observation)
    
    # 测试激进型个性
    agent.personality = {
        "name": "激进型",
        "aggression_factor": 0.8
    }
    action = agent._fallback_action()
    assert action.action_type == ActionType.RAISE
    
    # 测试保守型个性
    agent.personality = {
        "name": "保守型",
        "aggression_factor": 0.2
    }
    action = agent._fallback_action()
    assert action.action_type == ActionType.FOLD
    
    # 测试平衡型个性
    agent.personality = {
        "name": "平衡型",
        "aggression_factor": 0.5
    }
    action = agent._fallback_action()
    assert action.action_type == ActionType.CALL

def test_llm_agent_save_load(basic_config, sample_observation, tmp_path):
    """测试LLM智能体状态保存和加载"""
    agent = LLMAgent("test_agent", basic_config)
    agent.observe(sample_observation)
    agent.total_reward = 100.0
    
    # 保存状态
    save_path = tmp_path / "agent_state.json"
    agent.save(str(save_path))
    
    # 创建新智能体并加载状态
    new_agent = LLMAgent("test_agent", basic_config)
    new_agent.load(str(save_path))
    
    assert new_agent.agent_id == agent.agent_id
    assert new_agent.personality == agent.personality
    assert len(new_agent.short_term_memory) == len(agent.short_term_memory)
    assert new_agent.total_reward == agent.total_reward 