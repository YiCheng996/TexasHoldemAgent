"""
基础智能体模块。
定义AI智能体的基本接口和功能。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from src.engine.game import ActionType, PlayerAction
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class GameObservation:
    """游戏观察数据类"""
    # 基本信息
    game_id: str                    # 游戏ID
    player_id: str                  # 玩家ID
    phase: str                      # 游戏阶段
    position: int                   # 玩家位置
    timestamp: datetime             # 观察时间戳
    
    # 牌局信息
    hand_cards: List[str]           # 手牌
    community_cards: List[str]      # 公共牌
    pot_size: int                   # 底池大小
    current_bet: int               # 当前最大注
    min_raise: int                 # 最小加注额
    
    # 玩家信息
    chips: int                      # 当前筹码
    is_all_in: bool                # 是否全下
    
    # 其他玩家信息
    opponents: List[Dict[str, Any]]  # 其他玩家信息列表
    
    # 历史信息
    round_actions: List[Any]  # 本轮动作历史
    game_actions: List[Any]   # 本局动作历史

class Agent(ABC):
    """基础智能体类"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """
        初始化智能体
        
        Args:
            agent_id: 智能体ID
            config: 配置信息
        """
        self.agent_id = agent_id
        self.config = config
        self.logger = get_logger(f"Agent_{agent_id}")
        
        # 当前观察
        self.current_observation: Optional[GameObservation] = None
        
        self.logger.info(f"Agent {agent_id} initialized with config: {config}")
    
    @abstractmethod
    def observe(self, observation: GameObservation) -> None:
        """
        接收游戏状态观察
        
        Args:
            observation: 游戏状态观察
        """
        self.current_observation = observation
        self.logger.debug(f"Received observation at {observation.timestamp}")
    
    @abstractmethod
    def act(self) -> PlayerAction:
        """
        根据当前观察选择动作
        
        Returns:
            PlayerAction: 选择的动作
        """
        if not self.current_observation:
            raise ValueError("No observation available")
            
        # 检查游戏是否已结束
        if self.current_observation.phase == "FINISHED":
            logger.info(f"游戏已结束，AI玩家 {self.agent_id} 停止行动")
            return None
            
        raise NotImplementedError
    
    def reset(self) -> None:
        """重置智能体状态"""
        self.current_observation = None
        self.logger.info("Agent reset")
