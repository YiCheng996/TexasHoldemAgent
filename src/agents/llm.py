"""
LLM智能体模块。
实现基于大语言模型的德州扑克AI智能体。
"""

import json
import yaml
import os
from typing import Dict, List, Any, Union, Optional
from datetime import datetime
import time

from litellm import completion
from src.agents.base import Agent, GameObservation
from src.engine.game import ActionType, PlayerAction
from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger(__name__)

class LLMAgent(Agent):
    """基于大语言模型的智能体"""
    
    def __init__(self, agent_id: str, config: Union[str, Dict[str, Any]]):
        """
        初始化LLM智能体
        
        Args:
            agent_id: 智能体ID
            config: 配置信息,可以是配置文件路径或配置字典
        """
        # 加载配置
        if isinstance(config, str):
            # 使用缓存的配置
            config = load_config(config_path=config)
        
        super().__init__(agent_id, config)
        
        # 根据agent_id获取对应的AI玩家配置
        if agent_id in config["ai_players"]:
            self.model_config = config["ai_players"][agent_id]
            self.description = self.model_config.get(
                "description", 
                "在激进和保守之间寻找平衡的玩家"
            )
        else:
            # 如果找不到对应配置，抛出异常
            raise ValueError(f"未找到AI玩家 {agent_id} 的配置，请在llm.yml中添加相应配置")
        
        # 设置API密钥
        os.environ["OPENAI_API_KEY"] = self.model_config.get("api_key", "")
        
        # 加载提示词模板
        self.prompt_template = config["prompts"]["decision_making"]
        
        logger.info(f"LLM Agent {agent_id} 初始化完成，使用模型 {self.model_config['model']}，性格: {self.description}")
    
    def observe(self, observation: GameObservation) -> None:
        """记录当前游戏状态"""
        super().observe(observation)
        logger.info(f"AI玩家 {self.agent_id} 观察到新的游戏状态")
    
    def act(self) -> PlayerAction:
        """使用LLM生成动作"""
        if not self.current_observation:
            raise ValueError("No observation available")
            
        # 初始化重试次数
        retry_count = 0
        max_retries = 3
        last_error = None
        
        while retry_count < max_retries:
            try:
                # 生成提示词
                prompt = self._generate_prompt(last_error)
                
                # 调用LLM
                response = self._call_llm(prompt)
                
                # 解析响应
                decision = self._parse_response(response)
                
                # 验证决策
                if not self._validate_decision(decision):
                    raise ValueError("LLM决策验证失败")
                    
                # 创建动作
                action_type = ActionType[decision["action"]["type"]]
                amount = decision["action"].get("amount", 0)
                
                # 验证金额
                if isinstance(amount, str):
                    amount = int(amount)
                
                # 验证加注金额不超过剩余筹码
                if action_type in [ActionType.RAISE, ActionType.ALL_IN]:
                    if amount > self.current_observation.chips:
                        raise ValueError(f"加注金额 {amount} 超过了剩余筹码 {self.current_observation.chips}")
                
                # 创建动作对象
                action = PlayerAction(
                    player_id=self.agent_id,
                    action_type=action_type,
                    amount=amount,
                    timestamp=datetime.now()
                )
                
                logger.info(f"生成动作: {action.action_type.name} 金额: {action.amount}")
                return action
                
            except Exception as e:
                retry_count += 1
                last_error = str(e)
                logger.warning(f"决策生成失败 (尝试 {retry_count}/{max_retries}): {last_error}")
                time.sleep(1)  # 短暂等待后重试
        
        # 如果所有重试都失败，返回弃牌动作
        logger.error(f"达到最大重试次数，选择弃牌。最后一次错误: {last_error}")
        return PlayerAction(
            player_id=self.agent_id,
            action_type=ActionType.FOLD,
            amount=0,
            timestamp=datetime.now()
        )
    
    def _get_default_action(self, error: str) -> PlayerAction:
        """当LLM决策失败时，返回一个安全的默认动作"""
        if not self.current_observation:
            raise ValueError("No observation available")
            
        # 如果是因为金额超过筹码导致的错误，选择全下或弃牌
        if "超过了剩余筹码" in error:
            if self.current_observation.hand_strength > 0.7:  # 如果手牌较强
                return PlayerAction(
                    player_id=self.agent_id,
                    action_type=ActionType.ALL_IN,
                    amount=self.current_observation.chips,
                    timestamp=datetime.now()
                )
            else:
                return PlayerAction(
                    player_id=self.agent_id,
                    action_type=ActionType.FOLD,
                    amount=0,
                    timestamp=datetime.now()
                )
        
        # 默认选择跟注，如果筹码不足则弃牌
        call_amount = self.current_observation.current_bet
        if call_amount <= self.current_observation.chips:
            return PlayerAction(
                player_id=self.agent_id,
                action_type=ActionType.CALL,
                amount=call_amount,
                timestamp=datetime.now()
            )
        else:
            return PlayerAction(
                player_id=self.agent_id,
                action_type=ActionType.FOLD,
                amount=0,
                timestamp=datetime.now()
            )
    
    def _generate_prompt(self, last_error: Optional[str] = None) -> str:
        """生成提示词"""
        if not self.current_observation:
            raise ValueError("No observation available")
            
        # 格式化手牌
        hand_cards = ", ".join(self.current_observation.hand_cards)
        
        # 格式化公共牌
        community_cards = ", ".join(
            self.current_observation.community_cards
        ) if self.current_observation.community_cards else "无"
        
        # 格式化对手信息
        opponents_info = []
        for opp in self.current_observation.opponents:
            opp_info = (
                f"玩家ID: {opp['player_id']}\n"
                f"筹码: {opp['chips']}\n"
                f"当前下注: {opp['current_bet']}\n"
                f"状态: {'激活' if opp['is_active'] else '未激活'}"
            )
            opponents_info.append(opp_info)
        opponents = "\n---\n".join(opponents_info)
        
        # 格式化玩家行动历史
        player_actions = []
        for action in self.current_observation.round_actions:
            player_actions.append(
                f"{action.player_id}: "
                f"{action.action_type.name} "
                f"{action.amount if action.amount > 0 else ''}"
            )
        player_actions = "\n".join(player_actions)

        # 计算当前最大注和最小加注额
        current_max_bet = self.current_observation.current_bet
        min_raise = self.current_observation.min_raise
        min_raise_to = current_max_bet + min_raise  # 最小加注额是当前最大注加上最小加注增量
        
        # 添加上一次错误信息（如果有）
        error_context = f"\n上一次决策错误: {last_error}\n请避免重复此错误。" if last_error else ""
        
        # 渲染提示词模板
        prompt = self.prompt_template.format(
            hand_cards=hand_cards,
            community_cards=community_cards,
            phase=str(self.current_observation.phase),
            position=self.current_observation.position,
            pot_size=self.current_observation.pot_size,
            current_bet=current_max_bet,
            min_raise=min_raise_to,
            chips=self.current_observation.chips,
            opponents=opponents,
            round_actions=player_actions,
            historical_context=f"你是一个{self.description}{error_context}"
        )
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        try:
            # 记录请求内容
            logger.info("\n" + "="*50)
            logger.info("🤖 AI玩家 {self.agent_id} 思考中...")
            logger.info(f"使用模型: {self.model_config['model']}")
            logger.info(f"提示词:\n{prompt}")
            
            # 调用LLM
            response = completion(
                model=self.model_config["model"],
                messages=[{"role": "user", "content": prompt}],
                api_key=self.model_config["api_key"],
                base_url=self.model_config["base_url"],
                temperature=self.model_config["temperature"],
                max_tokens=self.model_config["max_tokens"],
                timeout=self.model_config["timeout"]
            )
            response_content = response.choices[0]["message"]["content"]
            
            # 记录响应内容
            logger.info(f"\n💭 决策结果:\n{response_content}")
            logger.info("="*50 + "\n")
            
            return response_content
            
        except Exception as e:
            logger.error(f"❌ LLM调用失败: {e}")
            raise
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 清理响应文本
            response = response.strip()
            json_str = response
            
            # 尝试提取JSON（处理可能的markdown格式）
            if response.startswith("```"):
                lines = response.split("\n")
                start_idx = 1
                if lines[1].lower().startswith("json"):
                    start_idx = 2
                end_idx = -1
                if lines[-1].strip() == "```":
                    end_idx = -1
                json_str = "\n".join(lines[start_idx:end_idx])
            
            # 清理和规范化JSON字符串
            json_str = json_str.strip()
            
            # 解析JSON
            try:
                decision = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                raise
            
            # 验证必要字段
            required_fields = ["action", "reasoning", "table_talk"]
            missing_fields = [field for field in required_fields if field not in decision]
            if missing_fields:
                raise ValueError(f"缺少必要字段: {missing_fields}")
            
            # 验证action字段
            action = decision["action"]
            action_required_fields = ["type", "amount"]
            missing_action_fields = [field for field in action_required_fields if field not in action]
            if missing_action_fields:
                raise ValueError(f"action缺少必要字段: {missing_action_fields}")
            
            # 验证动作类型
            valid_actions = ["FOLD", "CHECK", "CALL", "RAISE", "ALL_IN"]
            if action["type"] not in valid_actions:
                raise ValueError(f"无效的动作类型: {action['type']}")
            
            # 验证加注金额
            if action["type"] in ["RAISE", "ALL_IN"]:
                if not isinstance(action["amount"], (int, float)) or action["amount"] <= 0:
                    raise ValueError(f"加注金额必须是正数")
            elif action["type"] in ["FOLD", "CHECK", "CALL"]:
                action["amount"] = 0
            
            return decision
            
        except Exception as e:
            logger.error(f"解析LLM响应时出错: {str(e)}")
            raise
    
    def _validate_decision(self, decision: Dict[str, Any]) -> bool:
        """验证LLM决策"""
        try:
            # 验证动作类型
            action = decision["action"]
            if "type" not in action or "amount" not in action:
                logger.error("动作缺少type或amount字段")
                return False
                
            # 验证动作类型是否有效
            action_type_str = action["type"]
            try:
                ActionType[action_type_str]
            except KeyError:
                logger.error(f"无效的动作类型: {action_type_str}")
                return False
                
            # 验证加注金额
            if action_type_str in ["RAISE", "ALL_IN"]:
                if not isinstance(action["amount"], (int, float)):
                    logger.error(f"加注金额类型错误: {type(action['amount'])}")
                    return False
                if action["amount"] <= 0:
                    logger.error(f"加注金额必须为正数: {action['amount']}")
                    return False
                    
                # 验证加注金额是否在允许范围内
                if not self.current_observation:
                    logger.error("缺少当前观察")
                    return False
                    
                if action_type_str == "RAISE":
                    max_bet = self.current_observation.current_bet
                    min_raise = self.current_observation.min_raise
                    min_raise_to = max_bet + min_raise
                    
                    if action["amount"] < min_raise_to:
                        logger.error(f"加注金额 {action['amount']} 小于最小加注额 {min_raise_to}")
                        return False
                        
                    if action["amount"] > self.current_observation.chips:
                        logger.error(f"加注金额 {action['amount']} 超过剩余筹码 {self.current_observation.chips}")
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"验证决策时出错: {e}")
            return False
