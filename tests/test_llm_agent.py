"""
测试LLM智能体的输入输出
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pytest
import logging
import json
import traceback

# 添加项目根目录到Python路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from src.agents.llm import LLMAgent
from src.agents.base import GameObservation
from src.engine.game import ActionType, PlayerAction
from src.utils.config import load_config
from src.utils.logger import get_logger

# 设置日志级别
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

def test_llm_agent_basic():
    """测试LLM智能体的基本功能"""
    try:
        # 加载配置
        config = load_config('llm')
        
        # 创建智能体
        agent = LLMAgent("test_agent", config)
        logger.info("成功创建LLM智能体")
        
        # 创建测试观察
        observation = GameObservation(
            game_id="test_game",
            player_id="test_agent",
            phase="PRE_FLOP",
            position=1,
            timestamp=datetime.now(),
            hand_cards=["A♠", "K♠"],
            community_cards=[],
            pot_size=30,
            current_bet=20,
            min_raise=20,
            chips=1000,
            total_bet=0,
            is_all_in=False,
            opponents=[
                {
                    "player_id": "player_1",
                    "chips": 980,
                    "total_bet": 20,
                    "current_bet": 20,
                    "is_active": True,
                    "is_all_in": False
                }
            ],
            round_actions=[
                PlayerAction(
                    player_id="player_1",
                    action_type=ActionType.RAISE,
                    amount=20,
                    timestamp=datetime.now()
                )
            ],
            game_actions=[]
        )
        logger.info("创建测试观察数据")
        
        # 让智能体观察
        agent.observe(observation)
        logger.info("智能体已接收观察数据")
        
        try:
            # 让智能体行动
            logger.info("开始执行智能体行动...")
            action = agent.act()
            logger.info(f"智能体执行了动作: {action}")
            
            # 验证动作
            assert isinstance(action, PlayerAction), "动作类型不正确"
            assert action.player_id == "test_agent", "玩家ID不匹配"
            assert hasattr(action, 'action_type'), "缺少action_type属性"
            assert hasattr(action, 'amount'), "缺少amount属性"
            assert isinstance(action.timestamp, datetime), "timestamp类型不正确"
            
            logger.info("测试通过!")
            return action
            
        except Exception as e:
            logger.error(f"智能体行动时出错: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")
        raise

def test_llm_raw_response():
    """测试LLM的原始响应"""
    try:
        # 加载配置
        config = load_config('llm')
        
        # 创建智能体
        agent = LLMAgent("test_agent", config)
        print("\n成功创建LLM智能体")
        
        # 创建测试观察
        observation = GameObservation(
            game_id="test_game",
            player_id="test_agent",
            phase="PRE_FLOP",
            position=1,
            timestamp=datetime.now(),
            hand_cards=["A♠", "K♠"],
            community_cards=[],
            pot_size=30,
            current_bet=20,
            min_raise=20,
            chips=1000,
            total_bet=0,
            is_all_in=False,
            opponents=[
                {
                    "player_id": "player_1",
                    "chips": 980,
                    "total_bet": 20,
                    "current_bet": 20,
                    "is_active": True,
                    "is_all_in": False
                }
            ],
            round_actions=[
                PlayerAction(
                    player_id="player_1",
                    action_type=ActionType.RAISE,
                    amount=20,
                    timestamp=datetime.now()
                )
            ],
            game_actions=[]
        )
        print("创建测试观察数据")
        
        # 让智能体观察
        agent.observe(observation)
        print("智能体已接收观察数据")
        
        # 生成提示词
        prompt = agent._generate_prompt()
        print("\n【生成的提示词】")
        print("="*50)
        print(prompt)
        print("="*50)
        
        # 获取原始响应
        try:
            print("\n正在调用LLM API...")
            raw_response = agent._call_llm(prompt)
            print("\n【LLM原始响应】")
            print("="*50)
            print(raw_response)
            print("="*50)
            
            # 尝试解析JSON
            print("\n【尝试解析JSON】")
            print("="*50)
            
            # 方法1：直接解析
            print("\n方法1 - 直接解析:")
            try:
                result1 = json.loads(raw_response)
                print("成功!")
                print("-"*30)
                print(json.dumps(result1, indent=2, ensure_ascii=False))
            except json.JSONDecodeError as e:
                print(f"失败: {e}")
                print(f"错误位置: 第{e.lineno}行, 第{e.colno}列")
                print(f"错误内容: {e.doc[max(0, e.pos-40):e.pos+40]}")
            
            # 方法2：提取{}之间的内容
            print("\n方法2 - 提取{}之间的内容:")
            try:
                start = raw_response.find("{")
                end = raw_response.rfind("}") + 1
                if start != -1 and end != 0:
                    json_str = raw_response[start:end]
                    print("提取的JSON字符串:")
                    print("-"*30)
                    print(json_str)
                    print("-"*30)
                    result2 = json.loads(json_str)
                    print("解析结果:")
                    print(json.dumps(result2, indent=2, ensure_ascii=False))
                else:
                    print("未找到JSON内容")
            except json.JSONDecodeError as e:
                print(f"失败: {e}")
                print(f"错误位置: 第{e.lineno}行, 第{e.colno}列")
                print(f"错误内容: {e.doc[max(0, e.pos-40):e.pos+40]}")
            
            print("="*50)
            
        except Exception as e:
            print(f"\nLLM调用或解析过程出错:")
            traceback.print_exc()
            raise
            
    except Exception as e:
        print(f"\n测试过程中出错:")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        # 只运行原始响应测试
        test_llm_raw_response()
    except Exception as e:
        print(f"\n测试失败: {str(e)}")
        sys.exit(1) 