"""
游戏状态管理模块。
负责管理游戏状态和玩家状态。
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime

from src.utils.logger import get_logger

logger = get_logger(__name__)

class GameStage(Enum):
    """游戏阶段枚举"""
    WAITING = auto()    # 等待开始
    PRE_FLOP = auto()   # 翻牌前
    FLOP = auto()       # 翻牌
    TURN = auto()       # 转牌
    RIVER = auto()      # 河牌
    SHOWDOWN = auto()   # 摊牌
    FINISHED = auto()   # 结束

class PlayerAction(Enum):
    """玩家动作枚举"""
    FOLD = "FOLD"      # 弃牌
    CHECK = "CHECK"     # 过牌
    CALL = "CALL"      # 跟注
    RAISE = "RAISE"     # 加注
    ALL_IN = "ALL_IN"    # 全下
    
    def __str__(self) -> str:
        return self.value

@dataclass
class PlayerState:
    """玩家状态类"""
    id: str                     # 玩家ID
    chips: int                  # 当前筹码
    cards: List[str] = field(default_factory=list)  # 手牌
    current_bet: int = 0        # 当前下注
    total_bet: int = 0         # 本局游戏总下注
    has_acted: bool = False    # 是否已行动
    is_active: bool = True     # 是否仍在游戏中
    is_all_in: bool = False    # 是否全下
    position: int = 0          # 玩家位置

class GameState:
    """游戏状态类"""
    
    def __init__(self):
        """初始化游戏状态"""
        self.game_id: str = ""  # 添加game_id属性
        self.players: Dict[str, PlayerState] = {}
        self.active_players: List[PlayerState] = []
        self.pot: int = 0
        self.initial_chips: int = 1000
        self.community_cards: List[str] = []
        self.current_bet: int = 0
        self.min_raise: int = 0
        self.max_raise: int = 0  # 添加最大加注额
        self.phase: str = "WAITING"
        self.current_player: Optional[str] = None
        self.game_result: Optional[Dict] = None  # 添加游戏结果字段
        self.round_actions: List[PlayerAction] = []  # 当前回合的动作历史
        self.game_actions: List[PlayerAction] = []   # 整局游戏的动作历史
        
        logger.info("游戏状态已初始化")
        
    def add_player(self, player_id: str, chips: int, position: int) -> None:
        """
        添加玩家
        
        Args:
            player_id: 玩家ID
            chips: 初始筹码
            position: 座位位置
        """
        # 设置正确的位置
        if player_id == "player_0":
            position = 0
        elif player_id.startswith("ai_"):
            # 从ai_1开始，位置从1开始递增
            position = int(player_id.split("_")[1])
            
        player = PlayerState(player_id, chips, position=position)
        self.players[player_id] = player
        self.active_players.append(player)
        logger.info(f"Added player {player_id} with {chips} chips at position {position}")
        
    def get_active_players(self) -> List[PlayerState]:
        """
        获取活跃玩家列表，按照当前回合的正确顺序排序
        
        Returns:
            List[PlayerState]: 按照行动顺序排序的活跃玩家列表
        """
        active_players = [p for p in self.players.values() if p.is_active]
        
        # 按照位置排序
        active_players.sort(key=lambda p: p.position)
        
        logger.debug(f"当前活跃玩家顺序: {[p.id for p in active_players]}")
        return active_players
        
    def fold_player(self, player_id: str) -> None:
        """
        玩家弃牌
        
        Args:
            player_id: 玩家ID
        """
        if player_id not in self.players:
            raise ValueError(f"玩家 {player_id} 不存在")
            
        player = self.players[player_id]
        player.is_active = False
        player.cards = []  # 清空手牌
        player.has_acted = True  # 标记为已行动
        
        logger.info(f"玩家 {player_id} 弃牌")
        
        # 检查是否只剩一个活跃玩家
        active_players = self.get_active_players()
        if len(active_players) == 1:
            logger.info(f"只剩一个活跃玩家: {active_players[0].id}")
        
    def call(self, player_id: str) -> None:
        """
        玩家跟注
        """
        if player_id not in self.players:
            raise ValueError(f"玩家 {player_id} 不存在")
            
        player = self.players[player_id]
        if not player.is_active:
            raise ValueError(f"玩家 {player_id} 已经弃牌")
            
        # 获取当前最大下注
        max_bet = self.get_max_bet()
        
        # 计算需要跟注的金额
        call_amount = max_bet - player.current_bet
        
        # 实际可跟注金额不能超过玩家剩余筹码
        actual_amount = min(call_amount, player.chips)
        
        # 更新玩家状态
        player.current_bet += actual_amount
        player.chips -= actual_amount
        player.total_bet += actual_amount  # 更新总下注
        self.pot += actual_amount  # 将跟注金额加入底池
        
        logger.info(f"玩家 {player_id} 跟注 {actual_amount} 筹码")
        
    def raise_bet(self, player_id: str, amount: int) -> None:
        """
        玩家加注
        """
        if player_id not in self.players:
            raise ValueError(f"玩家 {player_id} 不存在")
            
        player = self.players[player_id]
        if not player.is_active:
            raise ValueError(f"玩家 {player_id} 已经弃牌")
            
        # 计算需要的总金额（当前下注加上新的加注）
        total_amount = amount
        
        # 实际可加注金额不能超过玩家剩余筹码
        if total_amount > player.chips + player.current_bet:
            raise ValueError("筹码不足")
            
        # 更新玩家状态
        actual_amount = total_amount - player.current_bet
        player.chips -= actual_amount
        player.current_bet = total_amount
        player.total_bet += actual_amount  # 更新总下注
        self.pot += actual_amount  # 将加注金额加入底池
        
        logger.info(f"玩家 {player_id} 加注到 {total_amount} 筹码")
        
    def all_in(self, player_id: str) -> None:
        """
        玩家全下
        """
        if player_id not in self.players:
            raise ValueError(f"玩家 {player_id} 不存在")
            
        player = self.players[player_id]
        amount = player.chips
        
        # 更新玩家状态
        player.chips = 0
        player.current_bet += amount
        player.total_bet += amount  # 更新总下注
        player.is_all_in = True
        
        # 更新底池
        self.pot += amount
        
        # 如果全下金额大于当前最大注，更新最小加注额
        if player.current_bet > self.min_raise:
            self.min_raise = player.current_bet
            
        logger.info(f"Player {player_id} went all-in with {amount} chips")
        
    def reset_bets(self) -> None:
        """重置所有玩家的下注"""
        for player in self.players.values():
            player.current_bet = 0
            player.total_bet = 0  # 重置总下注
            player.has_acted = False
            
    def get_player_by_position(self, position: int) -> Optional[PlayerState]:
        """
        根据位置获取玩家
        
        Args:
            position: 座位位置
            
        Returns:
            Optional[PlayerState]: 玩家状态或None
        """
        for player in self.players.values():
            if player.position == position:
                return player
        return None
    
    def reset_round(self) -> None:
        """重置回合状态"""
        self.pot = 0
        self.min_raise = 0
        self.game_result = None  # 清空游戏结果
        self.round_actions = []  # 清空回合动作历史
        for player in self.players.values():
            player.current_bet = 0
            player.total_bet = 0  # 重置总下注
            player.has_acted = False
            player.is_active = True
            player.is_all_in = False
            player.cards = []
        self.community_cards = []  # 清空公共牌
    
    def set_player_cards(self, player_id: str, cards: List[str]) -> None:
        """
        设置玩家手牌
        
        Args:
            player_id: 玩家ID
            cards: 手牌列表
        """
        if player_id not in self.players:
            raise ValueError(f"Player {player_id} not found")
            
        self.players[player_id].cards = cards
        logger.debug(f"Set cards for player {player_id}")
    
    def bet(self, player_id: str, amount: int) -> None:
        """
        玩家下注
        
        Args:
            player_id: 玩家ID
            amount: 下注金额
        """
        if player_id not in self.players:
            raise ValueError(f"玩家 {player_id} 不存在")
            
        player = self.players[player_id]
        if amount > player.chips:
            # 如果筹码不足，转为全下
            amount = player.chips
            player.is_all_in = True
            
        # 更新玩家状态
        player.chips -= amount
        player.current_bet += amount
        player.total_bet += amount  # 更新总下注
        self.pot += amount  # 将下注金额加入底池
        
        if player.is_all_in:
            logger.info(f"玩家 {player_id} 筹码不足，转为全下 {amount} 筹码")
        else:
            logger.info(f"玩家 {player_id} 下注 {amount} 筹码")
            
    def apply_action(self, player_id: str, action: PlayerAction, amount: int = 0) -> bool:
        """
        应用玩家动作
        
        Args:
            player_id: 玩家ID
            action: 动作类型
            amount: 动作金额
            
        Returns:
            bool: 是否成功应用动作
        """
        player = self.players.get(player_id)
        if not player or not player.is_active:
            logger.warning(f"玩家 {player_id} 不存在或已弃牌")
            return False
            
        try:
            # 获取当前最大下注
            current_max_bet = self.get_max_bet()
            logger.info(f"当前最大下注: {current_max_bet}")
            
            if action == PlayerAction.FOLD:
                logger.info(f"玩家 {player_id} 选择弃牌")
                self.fold_player(player_id)
            elif action == PlayerAction.CHECK:
                # 只有当前下注等于最大下注时才能过牌
                if current_max_bet > player.current_bet:
                    logger.warning(f"玩家 {player_id} 无法过牌，当前最大下注 {current_max_bet} 大于玩家下注 {player.current_bet}")
                    return False
                logger.info(f"玩家 {player_id} 选择过牌")
            elif action == PlayerAction.CALL:
                # 跟注时需要有足够的筹码
                call_amount = current_max_bet - player.current_bet
                if call_amount > player.chips:
                    logger.warning(f"玩家 {player_id} 筹码不足以跟注，需要 {call_amount} 筹码但只有 {player.chips}")
                    return False
                logger.info(f"玩家 {player_id} 跟注 {call_amount} 筹码")
                self.call(player_id)
            elif action == PlayerAction.RAISE:
                # 加注金额必须大于当前最大下注
                if amount <= current_max_bet:
                    logger.warning(f"玩家 {player_id} 加注金额 {amount} 不能小于等于当前最大下注 {current_max_bet}")
                    return False
                # 加注金额必须大于最小加注
                if amount - current_max_bet < self.min_raise:
                    logger.warning(f"玩家 {player_id} 加注金额 {amount} 小于最小加注 {self.min_raise}")
                    return False
                # 加注金额必须在玩家筹码范围内
                raise_amount = amount - player.current_bet
                if raise_amount > player.chips:
                    logger.warning(f"玩家 {player_id} 筹码不足以加注，需要 {raise_amount} 筹码但只有 {player.chips}")
                    return False
                logger.info(f"玩家 {player_id} 加注到 {amount} 筹码")
                self.raise_bet(player_id, amount)
            elif action == PlayerAction.ALL_IN:
                logger.info(f"玩家 {player_id} 选择全下 {player.chips} 筹码")
                self.all_in(player_id)
                
            player.has_acted = True
            logger.info(f"玩家 {player_id} 动作已完成")
            return True
            
        except ValueError as e:
            logger.error(f"处理玩家 {player_id} 动作时出错: {str(e)}")
            return False
    
    def is_round_complete(self) -> bool:
        """
        检查当前回合是否完成
        
        Returns:
            bool: 是否完成
        """
        active_players = self.get_active_players()
        
        # 如果只剩一个玩家，回合完成
        if len(active_players) <= 1:
            return True
            
        # 检查所有活跃玩家是否都已行动
        if not all(p.has_acted for p in active_players):
            return False
            
        # 获取当前最大下注
        max_bet = max(p.current_bet for p in active_players)
        
        # 检查所有活跃玩家是否都已经下注相等或者全下
        for player in active_players:
            if not player.is_all_in and player.current_bet != max_bet:
                return False
                
        return True
    
    def award_pot(self, winner_id: str) -> None:
        """
        将底池奖励给获胜者
        
        Args:
            winner_id: 获胜玩家ID
        """
        if winner_id not in self.players:
            raise ValueError(f"获胜玩家 {winner_id} 不存在")
            
        winner = self.players[winner_id]
        winner.chips += self.pot
        logger.info(f"玩家 {winner_id} 获得底池 {self.pot} 筹码，当前筹码: {winner.chips}")
        self.pot = 0  # 清空底池
    
    def create_side_pot(self) -> None:
        """创建边池"""
        # 找出所有全下玩家中下注最小的
        all_in_bets = [
            p.current_bet for p in self.players.values()
            if p.is_all_in and p.is_active
        ]
        if not all_in_bets:
            return
            
        min_bet = min(all_in_bets)
        side_pot = 0
        
        # 将每个玩家的超额部分转移到边池
        for player in self.players.values():
            if player.current_bet > min_bet:
                excess = player.current_bet - min_bet
                player.current_bet = min_bet
                side_pot += excess
                self.pot -= excess
                
        if side_pot > 0:
            self.side_pots.append(side_pot)
            logger.info(f"Created side pot of {side_pot} chips")

    def advance_stage(self) -> bool:
        """
        推进游戏阶段
        
        Returns:
            bool: 是否成功推进
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
                if self.stage == GameStage.FINISHED:
                    self.end_time = datetime.now()
                return True
        except ValueError:
            pass
            
        return False

    def model_dump(self) -> Dict[str, Any]:
        """
        将游戏状态转换为字典格式
        
        Returns:
            Dict[str, Any]: 游戏状态字典
        """
        return {
            "game_id": self.game_id,  # 包含game_id
            "players": [
                {
                    "id": player.id,
                    "chips": player.chips,
                    "cards": player.cards if player.id == "player_0" else [],
                    "current_bet": player.current_bet,
                    "total_bet": player.total_bet,  # 添加总下注
                    "is_active": player.is_active,
                    "is_all_in": player.is_all_in,
                    "position": player.position
                }
                for player in self.players.values()
            ],
            "pot_size": self.pot,
            "community_cards": self.community_cards,
            "current_bet": self.current_bet,
            "min_raise": self.min_raise,
            "max_raise": self.max_raise,
            "phase": self.phase,
            "current_player": self.current_player
        }

    def get_max_bet(self) -> int:
        """
        获取当前最大下注额
        
        Returns:
            int: 当前最大下注额
        """
        active_players = self.get_active_players()
        if not active_players:
            return 0
        return max(p.current_bet for p in active_players)
        
    def get_min_bet(self) -> int:
        """
        获取当前最小下注额
        
        Returns:
            int: 当前最小下注额
        """
        return self.min_raise if self.min_raise > 0 else self.current_bet

    def add_action(self, action: PlayerAction) -> None:
        """
        添加动作到历史记录
        
        Args:
            action: 玩家动作
        """
        self.round_actions.append(action)
        self.game_actions.append(action)
        logger.info(f"添加动作到历史记录: {action.action_type.name} by {action.player_id}")

    def get_winner(self) -> Tuple[str, int, str]:
        """
        确定获胜者并返回获胜信息
        
        Returns:
            Tuple[str, int, str]: (获胜者ID, 赢得的筹码数, 获胜牌型描述)
        """
        active_players = [player_id for player_id, player in self.players.items() if player.is_active]
        
        if len(active_players) == 1:
            # 只有一个玩家存活，直接获胜
            return active_players[0], self.pot, "其他玩家弃牌"
        
        # 获取所有活跃玩家的手牌评估结果
        player_hands = []
        for player_id in active_players:
            try:
                result, description = self.game.evaluate_hand(player_id)
                player_hands.append((player_id, result, description))
            except Exception as e:
                logger.error(f"评估玩家 {player_id} 手牌时出错: {str(e)}")
                continue
        
        if not player_hands:
            raise ValueError("没有有效的手牌评估结果")
        
        # 按照牌型大小排序
        player_hands.sort(key=lambda x: (x[1].rank.value, x[1].best_five), reverse=True)
        
        # 返回获胜者信息
        winner_id, winner_hand, description = player_hands[0]
        return winner_id, self.pot, description
