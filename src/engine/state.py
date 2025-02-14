"""
游戏状态管理模块。
负责管理和维护德州扑克游戏的状态，包括玩家信息、牌局信息、回合状态等。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime, UTC
import uuid

from src.utils.logger import get_logger

logger = get_logger(__name__)

class GameStage(Enum):
    """游戏阶段枚举"""
    WAITING = "waiting"        # 等待玩家加入
    PRE_FLOP = "pre_flop"     # 翻牌前
    FLOP = "flop"             # 翻牌
    TURN = "turn"             # 转牌
    RIVER = "river"           # 河牌
    SHOWDOWN = "showdown"     # 摊牌
    FINISHED = "finished"     # 游戏结束

class PlayerAction(Enum):
    """玩家动作枚举"""
    FOLD = "fold"       # 弃牌
    CHECK = "check"     # 过牌
    CALL = "call"       # 跟注
    RAISE = "raise"     # 加注
    ALL_IN = "all_in"   # 全下

@dataclass
class PlayerState:
    """玩家状态类"""
    player_id: str
    position: int                    # 位置（0-4，0为庄家位）
    chips: int                       # 当前筹码
    hand_cards: List[str] = field(default_factory=list)  # 手牌
    current_bet: int = 0            # 当前下注金额
    is_active: bool = True          # 是否仍在游戏中
    is_all_in: bool = False         # 是否全下
    total_bet: int = 0              # 本局总下注金额

@dataclass
class GameState:
    """游戏状态类"""
    game_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stage: GameStage = GameStage.WAITING
    players: Dict[str, PlayerState] = field(default_factory=dict)
    community_cards: List[str] = field(default_factory=list)
    pot: int = 0                    # 当前底池
    current_player_idx: int = 0     # 当前行动玩家索引
    dealer_position: int = 0        # 庄家位置
    small_blind: int = 10           # 小盲注
    big_blind: int = 20            # 大盲注
    min_raise: int = 20            # 最小加注
    last_raise: int = 0            # 上一次加注金额
    round_actions: List[Tuple[str, PlayerAction, int]] = field(default_factory=list)  # 回合动作历史
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: Optional[datetime] = None

    def __post_init__(self):
        """初始化后的处理"""
        self.logger = get_logger(f"GameState_{self.game_id}")
        self.logger.info(f"Created new game with ID: {self.game_id}")

    def add_player(self, player_id: str, chips: int) -> bool:
        """
        添加玩家到游戏
        
        Args:
            player_id: 玩家ID
            chips: 初始筹码数
            
        Returns:
            bool: 是否添加成功
        """
        if len(self.players) >= 5:
            self.logger.warning(f"Cannot add player {player_id}: game is full")
            return False
            
        if player_id in self.players:
            self.logger.warning(f"Player {player_id} already in game")
            return False
            
        position = len(self.players)
        self.players[player_id] = PlayerState(
            player_id=player_id,
            position=position,
            chips=chips
        )
        self.logger.info(f"Added player {player_id} at position {position}")
        return True
        
    def get_active_players(self) -> List[PlayerState]:
        """获取仍在游戏中的玩家列表"""
        return [p for p in self.players.values() if p.is_active]
        
    def get_next_player(self, current_position: int) -> Optional[PlayerState]:
        """获取下一个行动的玩家"""
        active_players = self.get_active_players()
        if not active_players:
            return None
            
        # 按位置排序
        sorted_players = sorted(active_players, key=lambda p: p.position)
        
        # 找到当前位置之后的第一个活跃玩家
        for player in sorted_players:
            if player.position > current_position:
                return player
                
        # 如果没有找到，返回第一个活跃玩家
        return sorted_players[0]
        
    def apply_action(self, player_id: str, action: PlayerAction, amount: int = 0) -> bool:
        """
        应用玩家动作
        
        Args:
            player_id: 玩家ID
            action: 动作类型
            amount: 动作金额（对于加注动作）
            
        Returns:
            bool: 动作是否有效并成功执行
        """
        if player_id not in self.players:
            self.logger.error(f"Invalid player_id: {player_id}")
            return False
            
        player = self.players[player_id]
        if not player.is_active:
            self.logger.error(f"Player {player_id} is not active")
            return False
            
        try:
            if action == PlayerAction.FOLD:
                player.is_active = False
            elif action == PlayerAction.CHECK:
                # 检查是否可以过牌
                if self._get_current_bet() > player.current_bet:
                    self.logger.error(f"Player {player_id} cannot check")
                    return False
            elif action == PlayerAction.CALL:
                call_amount = self._get_current_bet() - player.current_bet
                if not self._deduct_chips(player, call_amount):
                    return False
                player.current_bet = self._get_current_bet()
            elif action == PlayerAction.RAISE:
                if not self._is_valid_raise(amount):
                    self.logger.error(f"Invalid raise amount: {amount}")
                    return False
                if not self._deduct_chips(player, amount):
                    return False
                player.current_bet += amount
                self.last_raise = amount
            elif action == PlayerAction.ALL_IN:
                all_in_amount = player.chips
                player.current_bet += all_in_amount
                player.chips = 0
                player.is_all_in = True
                
            # 记录动作
            self.round_actions.append((player_id, action, amount))
            self.logger.info(f"Player {player_id} performed action {action} with amount {amount}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying action: {e}")
            return False
            
    def _get_current_bet(self) -> int:
        """获取当前最高下注"""
        return max((p.current_bet for p in self.players.values()), default=0)
        
    def _is_valid_raise(self, amount: int) -> bool:
        """检查加注金额是否有效"""
        return amount >= self.min_raise and amount >= self.last_raise
        
    def _deduct_chips(self, player: PlayerState, amount: int) -> bool:
        """从玩家筹码中扣除金额"""
        if player.chips < amount:
            self.logger.error(f"Player {player.player_id} does not have enough chips")
            return False
            
        player.chips -= amount
        player.total_bet += amount
        self.pot += amount
        return True
        
    def advance_stage(self) -> bool:
        """
        推进游戏阶段
        
        Returns:
            bool: 是否成功推进阶段
        """
        stage_order = [
            GameStage.WAITING,
            GameStage.PRE_FLOP,
            GameStage.FLOP,
            GameStage.TURN,
            GameStage.RIVER,
            GameStage.SHOWDOWN,
            GameStage.FINISHED
        ]
        
        try:
            current_index = stage_order.index(self.stage)
            if current_index < len(stage_order) - 1:
                self.stage = stage_order[current_index + 1]
                self.logger.info(f"Advanced game stage to {self.stage}")
                
                # 清理回合状态
                for player in self.players.values():
                    if player.is_active:
                        player.current_bet = 0
                self.round_actions = []
                
                return True
            return False
        except ValueError:
            self.logger.error(f"Invalid game stage: {self.stage}")
            return False
            
    def is_round_complete(self) -> bool:
        """检查当前回合是否结束"""
        active_players = self.get_active_players()
        if len(active_players) <= 1:
            return True
            
        # 检查所有活跃玩家是否都行动过且下注相等
        current_bet = self._get_current_bet()
        return all(
            p.current_bet == current_bet or p.is_all_in
            for p in active_players
        )
