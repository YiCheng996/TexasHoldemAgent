"""
LLM智能体模块测试。
测试基于大语言模型的智能体功能。
"""

import pytest
import os
from datetime import datetime
from pathlib import Path
import json
import yaml
from unittest.mock import patch
import time

from src.agents.llm import LLMAgent
from src.agents.base import GameObservation, ActionResult
from src.engine.game import ActionType, PlayerAction

@pytest.fixture
def config_path(tmp_path):
    """创建测试配置文件"""
    config = {
        "models": {
            "default": {
                "provider": "openai",
                "model": "openai/glm-4-plus",
                "api_key": "95285665986d43ad84eeeb3506e1150d.USTAijnoWSy6ADHc",
                "base_url": "https://open.bigmodel.cn/api/paas/v4/",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30
            },
            "fallback": {
                "provider": "anthropic",
                "model": "claude-2",
                "api_key": "${ANTHROPIC_API_KEY}",
                "base_url": "https://api.anthropic.com",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30
            }
        },
        "memory": {
            "short_term": {
                "max_rounds": 10
            },
            "long_term": {
                "collection": "test_memories",
                "max_results": 5,
                "similarity_threshold": 0.8,
                "pruning_days": 30
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
            "decision_making": (
                "你是一个德州扑克AI玩家。请根据当前游戏状态和历史信息做出决策。\n\n"
                "当前状态:\n"
                "- 手牌: {hand_cards}\n"
                "- 公共牌: {community_cards}\n"
                "- {current_action}\n"
                "- 底池: {pot_size}\n"
                "- 位置: {position}\n\n"
                "本轮玩家行动:\n{player_actions}\n\n"
                "历史记忆:\n{historical_context}\n\n"
                "请分析当前局势并做出决策。输出格式必须是JSON:\n"
                '{{"action": {{'
                '"type": "动作类型(FOLD/CHECK/CALL/RAISE)",'
                '"amount": "加注金额(如果选择加注)",'
                '"confidence": "决策置信度(0-1)"'
                '}},'
                '"reasoning": {{'
                '"hand_strength": "手牌强度分析",'
                '"position_analysis": "位置分析",'
                '"pot_odds": "底池赔率分析",'
                '"opponent_reads": ["对手行为分析"]'
                '}},'
                '"table_talk": {{'
                '"message": "发言内容",'
                '"tone": "发言语气"'
                '}}}}'
            ),
            "round_summary": (
                "请总结本轮游戏的关键信息:\n\n"
                "牌局信息:\n"
                "- 阶段: {phase}\n"
                "- 手牌: {hand_cards}\n"
                "- 公共牌: {community_cards}\n"
                "- 最终底池: {pot_size}\n\n"
                "玩家行动:\n{player_actions}\n\n"
                "请分析以下几点:\n"
                "1. 玩家的策略倾向\n"
                "2. 关键决策点\n"
                "3. 可能的改进空间\n\n"
                "输出格式必须是JSON:\n"
                '{{"analysis": {{'
                '"strategy_patterns": ["策略模式分析"],'
                '"key_decisions": ["关键决策分析"],'
                '"improvements": ["改进建议"]'
                '}},'
                '"metadata": {{'
                '"importance": "重要性评分(1-5)",'
                '"tags": ["相关标签"]'
                '}}}}'
            )
        }
    }
    
    config_file = tmp_path / "test_config.yml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)
    return str(config_file)

@pytest.fixture
def sample_observation():
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
def sample_result(sample_observation):
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

@pytest.fixture
def llm_agent(config_path):
    """创建LLM智能体实例"""
    # 为每个测试创建唯一的集合名称
    test_collection = f"test_memories_{datetime.now().timestamp()}"
    config = {
        "models": {
            "default": {
                "provider": "openai",
                "model": "openai/glm-4-plus",
                "api_key": "95285665986d43ad84eeeb3506e1150d.USTAijnoWSy6ADHc",
                "base_url": "https://open.bigmodel.cn/api/paas/v4/",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30
            },
            "fallback": {
                "provider": "anthropic",
                "model": "claude-2",
                "api_key": "${ANTHROPIC_API_KEY}",
                "base_url": "https://api.anthropic.com",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30
            }
        },
        "memory": {
            "short_term": {
                "max_rounds": 10
            },
            "long_term": {
                "collection": test_collection,
                "max_results": 5,
                "similarity_threshold": 0.8,
                "pruning_days": 30
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
            "decision_making": (
                "你是一个德州扑克AI玩家。请根据当前游戏状态和历史信息做出决策。\n\n"
                "当前状态:\n"
                "- 手牌: {hand_cards}\n"
                "- 公共牌: {community_cards}\n"
                "- {current_action}\n"
                "- 底池: {pot_size}\n"
                "- 位置: {position}\n\n"
                "本轮玩家行动:\n{player_actions}\n\n"
                "历史记忆:\n{historical_context}\n\n"
                "请分析当前局势并做出决策。输出格式必须是JSON:\n"
                '{{"action": {{'
                '"type": "动作类型(FOLD/CHECK/CALL/RAISE)",'
                '"amount": "加注金额(如果选择加注)",'
                '"confidence": "决策置信度(0-1)"'
                '}},'
                '"reasoning": {{'
                '"hand_strength": "手牌强度分析",'
                '"position_analysis": "位置分析",'
                '"pot_odds": "底池赔率分析",'
                '"opponent_reads": ["对手行为分析"]'
                '}},'
                '"table_talk": {{'
                '"message": "发言内容",'
                '"tone": "发言语气"'
                '}}}}'
            ),
            "round_summary": (
                "请总结本轮游戏的关键信息:\n\n"
                "牌局信息:\n"
                "- 阶段: {phase}\n"
                "- 手牌: {hand_cards}\n"
                "- 公共牌: {community_cards}\n"
                "- 最终底池: {pot_size}\n\n"
                "玩家行动:\n{player_actions}\n\n"
                "请分析以下几点:\n"
                "1. 玩家的策略倾向\n"
                "2. 关键决策点\n"
                "3. 可能的改进空间\n\n"
                "输出格式必须是JSON:\n"
                '{{"analysis": {{'
                '"strategy_patterns": ["策略模式分析"],'
                '"key_decisions": ["关键决策分析"],'
                '"improvements": ["改进建议"]'
                '}},'
                '"metadata": {{'
                '"importance": "重要性评分(1-5)",'
                '"tags": ["相关标签"]'
                '}}}}'
            )
        }
    }
    
    config_file = config_path
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)
    
    agent = LLMAgent("test_agent", config_file)
    yield agent
    
    # 清理测试数据
    try:
        agent.memory_manager.collection.delete()
    except Exception as e:
        print(f"清理测试数据时出错: {e}")

@pytest.fixture(autouse=True)
def mock_env_vars():
    """模拟环境变量"""
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key"
    }):
        yield

@pytest.fixture(autouse=True)
def mock_litellm():
    """模拟LiteLLM调用"""
    with patch("src.agents.llm.completion") as mock_completion:
        mock_completion.return_value.choices = [{
            "message": {
                "content": """
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
            }
        }]
        yield mock_completion

def test_agent_initialization(llm_agent):
    """测试智能体初始化"""
    assert llm_agent.agent_id == "test_agent"
    assert llm_agent.model_config["provider"] == "openai"
    assert llm_agent.model_config["model"] == "openai/glm-4-plus"
    assert llm_agent.personality is not None
    assert llm_agent.memory_manager is not None

def test_observe(llm_agent, sample_observation):
    """测试观察功能"""
    llm_agent.observe(sample_observation)
    assert llm_agent.current_observation == sample_observation
    assert len(llm_agent.memory_manager.short_term_memory) == 1
    
    memory = llm_agent.memory_manager.short_term_memory[0]
    assert memory.phase == sample_observation.phase
    assert memory.hand_cards == sample_observation.hand_cards
    assert memory.pot_size == sample_observation.pot_size

def test_generate_prompt(llm_agent, sample_observation):
    """测试提示词生成"""
    llm_agent.observe(sample_observation)
    prompt = llm_agent._generate_prompt()
    
    assert "A♠, K♠" in prompt
    assert "当前下注: 20" in prompt
    assert "player2: CALL" in prompt

def test_generate_summary_prompt(llm_agent, sample_result):
    """测试总结提示词生成"""
    prompt = llm_agent._generate_summary_prompt(sample_result)
    
    assert "PRE_FLOP" in prompt
    assert "A♠, K♠" in prompt
    assert "player2: CALL" in prompt

def test_parse_response(llm_agent):
    """测试响应解析"""
    # 测试有效响应
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
    decision = llm_agent._parse_response(valid_response)
    assert decision["action"]["type"] == "RAISE"
    assert decision["action"]["amount"] == 100
    assert decision["action"]["confidence"] == 0.8
    
    # 测试无效响应
    invalid_response = "这不是JSON格式"
    with pytest.raises(ValueError):
        llm_agent._parse_response(invalid_response)

def test_validate_decision(llm_agent):
    """测试决策验证"""
    # 测试有效决策
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
    assert llm_agent._validate_decision(valid_decision)
    
    # 测试无效决策 - 缺少必要字段
    invalid_decision = {
        "action": {
            "type": "RAISE"
        }
    }
    assert not llm_agent._validate_decision(invalid_decision)
    
    # 测试无效决策 - 无效的动作类型
    invalid_decision = {
        "action": {
            "type": "INVALID",
            "amount": 100,
            "confidence": 0.8
        },
        "reasoning": {},
        "table_talk": {}
    }
    assert not llm_agent._validate_decision(invalid_decision)

def test_fallback_action(llm_agent, sample_observation):
    """测试后备动作"""
    llm_agent.observe(sample_observation)
    
    # 测试激进型个性
    llm_agent.personality = {
        "name": "激进型",
        "aggression_factor": 0.8
    }
    action = llm_agent._fallback_action()
    assert action.action_type == ActionType.RAISE
    
    # 测试保守型个性
    llm_agent.personality = {
        "name": "保守型",
        "aggression_factor": 0.2
    }
    action = llm_agent._fallback_action()
    assert action.action_type == ActionType.FOLD

def test_save_load(llm_agent, sample_observation, tmp_path):
    """测试状态保存和加载"""
    # 设置一些状态
    llm_agent.observe(sample_observation)
    llm_agent.total_reward = 100.0
    
    # 保存状态
    save_path = tmp_path / "agent_state.json"
    llm_agent.save(str(save_path))
    
    # 创建新智能体并加载状态
    new_agent = LLMAgent("test_agent", llm_agent.config_path)
    new_agent.load(str(save_path))
    
    assert new_agent.agent_id == llm_agent.agent_id
    assert new_agent.personality == llm_agent.personality
    assert new_agent.total_reward == llm_agent.total_reward
    assert len(new_agent.memory_manager.short_term_memory) == len(llm_agent.memory_manager.short_term_memory)

def test_learn(llm_agent, sample_result):
    """测试学习功能"""
    llm_agent.learn(sample_result)
    assert len(llm_agent.episode_memory) == 1
    assert llm_agent.total_reward == sample_result.reward
    
    # 验证记忆更新
    if sample_result.next_observation:
        assert len(llm_agent.memory_manager.short_term_memory) > 0
        memory = llm_agent.memory_manager.short_term_memory[-1]
        assert memory.phase == sample_result.next_observation.phase
        assert memory.hand_cards == sample_result.next_observation.hand_cards

def test_api_key_configuration(config_path):
    """测试API密钥配置"""
    # 创建测试配置
    config = {
        "models": {
            "default": {
                "provider": "openai",
                "model": "openai/glm-4-plus",
                "api_key": "95285665986d43ad84eeeb3506e1150d.USTAijnoWSy6ADHc",
                "base_url": "https://open.bigmodel.cn/api/paas/v4/",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30
            },
            "fallback": {
                "provider": "anthropic",
                "model": "claude-2",
                "api_key": "${ANTHROPIC_API_KEY}",
                "base_url": "https://api.anthropic.com",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30
            }
        },
        "memory": {
            "short_term": {"max_rounds": 10},
            "long_term": {
                "collection": "test_memories",
                "max_results": 5,
                "similarity_threshold": 0.8,
                "pruning_days": 30
            }
        },
        "personalities": [
            {
                "name": "激进型",
                "description": "倾向于加注和诈唬的激进玩家",
                "aggression_factor": 0.8,
                "bluff_frequency": 0.3
            }
        ],
        "prompts": {
            "decision_making": "测试提示词"
        }
    }
    
    config_file = Path(config_path).parent / "test_config.yml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)
    
    # 初始化智能体
    agent = LLMAgent("test_agent", str(config_file))  # 转换为字符串路径
    
    # 验证API密钥设置
    assert os.environ.get("OPENAI_API_KEY") == "95285665986d43ad84eeeb3506e1150d.USTAijnoWSy6ADHc"
    assert os.environ.get("ANTHROPIC_API_KEY") == "${ANTHROPIC_API_KEY}"
    
    # 验证模型配置
    assert agent.model_config["api_key"] == "95285665986d43ad84eeeb3506e1150d.USTAijnoWSy6ADHc"
    assert agent.fallback_config["api_key"] == "${ANTHROPIC_API_KEY}"

def test_call_llm(llm_agent, sample_observation):
    """测试LLM调用"""
    # 设置观察
    llm_agent.observe(sample_observation)
    
    # 生成提示词
    prompt = llm_agent._generate_prompt()
    
    # 调用LLM
    response = llm_agent._call_llm(prompt)
    assert isinstance(response, str)
    assert "{" in response and "}" in response  # 确保返回JSON格式
    
    # 测试后备模型调用
    llm_agent.model_config["api_key"] = "invalid_key"
    response = llm_agent._call_llm(prompt)
    assert isinstance(response, str)

def test_on_episode_end(llm_agent, sample_observation):
    """测试回合结束处理"""
    # 设置观察和奖励
    llm_agent.observe(sample_observation)
    reward = 100.0
    
    # 调用回合结束处理
    llm_agent.on_episode_end(reward)
    
    # 验证状态
    assert llm_agent.total_reward == reward
    assert llm_agent.current_observation is None
    assert len(llm_agent.memory_manager.short_term_memory) == 0

def test_memory_management(llm_agent, sample_observation):
    """测试记忆管理"""
    try:
        # 添加多个观察
        for i in range(5):
            llm_agent.observe(sample_observation)
            
        # 验证短期记忆限制
        assert len(llm_agent.memory_manager.short_term_memory) <= llm_agent.max_memory_rounds
        
        # 验证记忆内容
        memory = llm_agent.memory_manager.short_term_memory[-1]
        assert memory.phase == sample_observation.phase
        assert memory.hand_cards == sample_observation.hand_cards
        assert memory.pot_size == sample_observation.pot_size
        
        # 等待向量数据库操作完成
        time.sleep(1)
        
        # 测试记忆查询
        similar_memories = llm_agent.memory_manager.query_similar_memories(
            "PRE_FLOP阶段的强牌",
            n_results=2
        )
        assert isinstance(similar_memories, list)
        
        # 测试清理记忆
        llm_agent.memory_manager.clear_short_term()
        assert len(llm_agent.memory_manager.short_term_memory) == 0
    except Exception as e:
        print(f"测试过程中出错: {e}")
        raise

def test_personality_influence(llm_agent, sample_observation):
    """测试个性对决策的影响"""
    llm_agent.observe(sample_observation)
    
    # 测试激进型个性
    llm_agent.personality = {
        "name": "激进型",
        "aggression_factor": 0.8,
        "bluff_frequency": 0.3
    }
    action = llm_agent._fallback_action()
    assert action.action_type == ActionType.RAISE
    
    # 测试保守型个性
    llm_agent.personality = {
        "name": "保守型",
        "aggression_factor": 0.2,
        "bluff_frequency": 0.1
    }
    action = llm_agent._fallback_action()
    assert action.action_type == ActionType.FOLD
    
    # 测试平衡型个性
    llm_agent.personality = {
        "name": "平衡型",
        "aggression_factor": 0.5,
        "bluff_frequency": 0.2
    }
    action = llm_agent._fallback_action()
    assert action.action_type == ActionType.CALL 

def test_error_handling(llm_agent):
    """测试错误处理"""
    # 测试无观察时的错误
    with pytest.raises(ValueError):
        llm_agent.act()
    
    # 测试无效的LLM响应
    invalid_response = "这不是JSON格式"
    with pytest.raises(ValueError):
        llm_agent._parse_response(invalid_response)
    
    # 测试无效的决策
    invalid_decision = {
        "action": {
            "type": "INVALID_ACTION",
            "amount": -100
        }
    }
    assert not llm_agent._validate_decision(invalid_decision)

def test_prompt_generation(llm_agent, sample_observation):
    """测试提示词生成"""
    llm_agent.observe(sample_observation)
    
    # 测试决策提示词
    decision_prompt = llm_agent._generate_prompt()
    assert isinstance(decision_prompt, str)
    assert "手牌" in decision_prompt
    assert "底池" in decision_prompt
    assert str(sample_observation.pot_size) in decision_prompt
    
    # 测试总结提示词
    summary_prompt = llm_agent._generate_summary_prompt(ActionResult(
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
    ))
    assert isinstance(summary_prompt, str)
    assert sample_observation.phase in summary_prompt 

def test_config_validation(config_path):
    """测试配置验证"""
    # 测试缺少必要配置
    invalid_config = {
        "models": {
            "default": {
                "provider": "openai",
                "model": "openai/glm-4-plus"
                # 缺少 api_key 和其他必要字段
            }
        },
        "memory": {
            "short_term": {"max_rounds": 10},
            "long_term": {
                "collection": "test_memories",
                "max_results": 5,
                "similarity_threshold": 0.8,
                "pruning_days": 30
            }
        },
        "personalities": [
            {
                "name": "激进型",
                "description": "倾向于加注和诈唬的激进玩家",
                "aggression_factor": 0.8,
                "bluff_frequency": 0.3
            }
        ],
        "prompts": {
            "decision_making": "测试提示词",
            "round_summary": "测试总结提示词"
        }
    }

    config_file = Path(config_path).parent / "invalid_config.yml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(invalid_config, f)

    with pytest.raises(KeyError):
        LLMAgent("test_agent", str(config_file))

    # 测试无效的个性配置
    invalid_personality_config = {
        "models": {
            "default": {
                "provider": "openai",
                "model": "openai/glm-4-plus",
                "api_key": "95285665986d43ad84eeeb3506e1150d.USTAijnoWSy6ADHc",
                "base_url": "https://open.bigmodel.cn/api/paas/v4/",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30
            },
            "fallback": {
                "provider": "anthropic",
                "model": "claude-2",
                "api_key": "${ANTHROPIC_API_KEY}",
                "base_url": "https://api.anthropic.com",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30
            }
        },
        "memory": {
            "short_term": {"max_rounds": 10},
            "long_term": {
                "collection": "test_memories",
                "max_results": 5,
                "similarity_threshold": 0.8,
                "pruning_days": 30
            }
        },
        "personalities": [],  # 空的个性列表
        "prompts": {
            "decision_making": "测试提示词",
            "round_summary": "测试总结提示词"
        }
    }

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(invalid_personality_config, f)

    with pytest.raises(IndexError):
        LLMAgent("test_agent", str(config_file)) 