"""
游戏主逻辑模块。
负责德州扑克游戏的核心流程控制，包括状态管理、回合控制和动作验证。
"""

from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from src.engine.state import GameState, PlayerState, GameStage
from src.engine.dealer import Dealer
from src.engine.rules import HandEvaluator, HandResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ActionType(Enum):
    """玩家动作类型"""
    FOLD = auto()          # 弃牌
    CHECK = auto()         # 过牌
    CALL = auto()          # 跟注
    RAISE = auto()         # 加注
    ALL_IN = auto()        # 全下

@dataclass
class PlayerAction:
    """玩家动作数据类"""
    player_id: str         # 玩家ID
    action_type: ActionType  # 动作类型
    amount: int = 0        # 动作金额
    timestamp: Optional[datetime] = None  # 动作时间戳
    table_talk: Optional[Dict[str, str]] = None  # 对话内容
    
    def model_dump(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "player_id": self.player_id,
            "action_type": self.action_type.name,  # 使用枚举的名称
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "table_talk": self.table_talk
        }

class TexasHoldemGame:
    """德州扑克游戏类"""
    
    def __init__(self, game_id: str, players: List[str], initial_stack: int = 1000, small_blind: int = 10):
        """
        初始化游戏
        
        Args:
            game_id: 游戏ID
            players: 玩家ID列表
            initial_stack: 初始筹码数量
            small_blind: 小盲注金额
        """
        self.game_id = game_id
        self.dealer = Dealer()
        self.state = GameState()
        self.state.game_id = game_id  # 设置game_id
        self.state.initial_chips = initial_stack  # 设置初始筹码
        self.phase = GameStage.WAITING
        self.state.phase = GameStage.WAITING  # 确保两个phase保持同步
        self.current_player_idx = 0
        self.button_position = 0  # 庄家位置（基于玩家位置）
        self.small_blind = small_blind  # 小盲注金额
        self.big_blind = small_blind * 2  # 大盲注金额
        self.min_raise = self.big_blind  # 最小加注额为大盲注
        self.ai_players = {}  # 存储AI玩家实例
        
        logger.info(f"游戏 {game_id} 已初始化，玩家数量: {len(players)}，初始筹码: {initial_stack}，小盲注: {small_blind}")
    
    def add_player(self, player: Any) -> None:
        """
        添加玩家到游戏
        
        Args:
            player: 玩家对象（可以是AI或人类玩家）
        """
        if self.phase != GameStage.WAITING:
            raise ValueError("Cannot add player after game started")
            
        if len(self.state.players) >= 9:
            raise ValueError("Maximum number of players reached")
            
        # 获取玩家ID
        player_id = player.agent_id
        
        # 检查玩家ID是否已存在
        if any(p.id == player_id for p in self.state.players.values()):
            raise ValueError(f"Player {player_id} already exists")
            
        # 添加玩家，位置为当前玩家数量
        position = len(self.state.players)
        self.state.add_player(player_id, self.state.initial_chips, position)
        
        # 如果是AI玩家，保存实例
        if player_id != "player_0":
            self.ai_players[player_id] = player
        
        logger.info(f"Added player {player_id} to game {self.game_id}")
    
    def start_game(self) -> None:
        """开始新的一局游戏"""
        if self.phase != GameStage.WAITING:
            raise ValueError("Game already started")
            
        # 检查活跃玩家
        active_players = self.state.get_active_players()
        if not active_players:
            logger.warning("没有活跃玩家，无法开始游戏")
            self.phase = GameStage.FINISHED
            self.state.phase = GameStage.FINISHED
            self.state.is_game_over = True
            return
            
        logger.info(f"开始新的一局游戏，活跃玩家: {[p.id for p in active_players]}")
        
        # 重置游戏状态
        self.dealer.shuffle()
        self.phase = GameStage.DEALING
        self.state.phase = GameStage.DEALING
        self.state.is_game_over = False
        
        # 发手牌
        hole_cards = self.dealer.deal_hole_cards(len(active_players))
        for player, cards in zip(active_players, hole_cards):
            self.state.set_player_cards(player.id, cards)
            logger.info(f"玩家 {player.id} 手牌: {cards}")
            
        # 设置盲注
        self.post_blinds()
        
        # 进入翻牌前阶段
        self.phase = GameStage.PRE_FLOP
        self.state.phase = GameStage.PRE_FLOP
        logger.info(f"游戏 {self.game_id} 开始，进入翻牌前阶段")
        
        # 设置第一个行动玩家（大盲注后一位）
        max_position = max(p.position for p in active_players)
        sb_position = (self.button_position + 1) % (max_position + 1)
        bb_position = (self.button_position + 2) % (max_position + 1)
        first_position = (bb_position + 1) % (max_position + 1)
        
        # 找到对应位置的玩家
        first_player = next((p for p in active_players if p.position == first_position), None)
        
        # 如果找不到玩家（可能是因为位置上没有玩家）,则找到第一个可用的位置
        if not first_player:
            # 按位置排序，找到第一个大于大盲注位置的玩家
            sorted_players = sorted(active_players, key=lambda p: p.position)
            
            for player in sorted_players:
                if player.position > bb_position:
                    first_player = player
                    break
                    
            # 如果还是找不到，使用第一个玩家
            if not first_player and sorted_players:
                first_player = sorted_players[0]
        
        # 设置当前玩家
        if first_player:
            self.state.current_player = first_player.id
            sorted_players = sorted(active_players, key=lambda p: p.position)
            self.current_player_idx = sorted_players.index(first_player)
            logger.info(f"第一个行动玩家: {first_player.id}, 位置: {first_player.position}")
        else:
            logger.warning("无法确定第一个行动玩家")
            self.state.current_player = None
    
    def post_blinds(self) -> None:
        """收取盲注"""
        active_players = self.state.get_active_players()
        if len(active_players) < 2:
            raise ValueError("玩家数量不足")
            
        # 找到小盲注位置（庄家位置的下一个位置）
        max_position = max(p.position for p in active_players)
        sb_position = (self.button_position + 1) % (max_position + 1)
        bb_position = (self.button_position + 2) % (max_position + 1)
        
        # 找到对应位置的玩家
        sb_player = next((p for p in active_players if p.position == sb_position), None)
        bb_player = next((p for p in active_players if p.position == bb_position), None)
        
        if not sb_player or not bb_player:
            raise ValueError("无法找到小盲注或大盲注玩家")
            
        # 收取小盲注
        self.state.bet(sb_player.id, self.small_blind)
        logger.info(f"玩家 {sb_player.id} 下注小盲注 {self.small_blind}")
        
        # 收取大盲注
        self.state.bet(bb_player.id, self.big_blind)
        logger.info(f"玩家 {bb_player.id} 下注大盲注 {self.big_blind}")
        
        self.min_raise = self.big_blind  # 设置最小加注额为大盲注
        
        # 设置当前玩家为大盲注后一位
        next_position = (bb_position + 1) % (max_position + 1)
        current_player = next((p for p in active_players if p.position == next_position), None)
        if current_player:
            self.current_player_idx = active_players.index(current_player)
            self.state.current_player = current_player.id
        else:
            # 如果找不到下一个位置的玩家，就从头开始
            self.current_player_idx = 0
            self.state.current_player = active_players[0].id
        
        logger.info(f"已收取盲注: 小盲注={sb_player.id}({self.small_blind})，大盲注={bb_player.id}({self.big_blind})")
        logger.info(f"当前玩家: {self.state.current_player}")
    
    def get_current_player(self) -> Optional[PlayerState]:
        """获取当前行动玩家"""
        # 如果没有当前玩家ID，返回None
        if not self.state.current_player:
            return None
        
        # 查找当前玩家
        active_players = self.state.get_active_players()
        if not active_players:
            logger.info("没有活跃玩家")
            return None
        
        # 直接通过ID获取当前玩家，确保使用正确的玩家
        for player in active_players:
            if player.id == self.state.current_player:
                return player
            
        # 如果找不到当前玩家（可能是因为已经弃牌），则从active_players列表中选择第一个
        logger.warning(f"当前玩家 {self.state.current_player} 不在活跃列表中，使用第一个活跃玩家替代")
        return active_players[0] if active_players else None
    
    def is_round_complete(self) -> bool:
        """
        检查当前回合是否完成
        
        回合完成的条件：
        1. 所有活跃玩家都已经行动
        2. 所有活跃玩家的下注金额相等
        """
        logger.info("检查回合是否完成")
        
        # 获取活跃玩家
        active_players = self.state.get_active_players()
        logger.info(f"活跃玩家数量: {len(active_players)}, 玩家ID: {[p.id for p in active_players]}")
        
        if not active_players:
            logger.info("没有活跃玩家，回合完成")
            return True
        
        # 获取当前最大下注额
        max_bet = self.state.get_max_bet()
        logger.info(f"当前最大下注额: {max_bet}")
        
        # 记录所有活跃玩家的状态
        all_acted = True
        all_bets_equal = True
        
        for player in active_players:
            logger.info(f"检查玩家 {player.id}: has_acted={player.has_acted}, current_bet={player.current_bet}, is_all_in={player.is_all_in}")
            
            # 跳过已全下的玩家，他们不能再行动
            if player.is_all_in:
                logger.debug(f"玩家 {player.id} 已全下，无需检查")
                continue
            
            # 检查是否所有玩家都已行动
            if not player.has_acted:
                logger.info(f"玩家 {player.id} 未行动，回合继续")
                all_acted = False
                break
            
            # 检查是否所有玩家的下注金额相等
            if player.current_bet != max_bet:
                logger.info(f"玩家 {player.id} 下注额({player.current_bet})不等于最大下注额({max_bet})，回合继续")
                all_bets_equal = False
                break
        
        # 最终判断
        round_complete = all_acted and all_bets_equal
        logger.info(f"回合完成判断: 所有玩家已行动={all_acted}, 所有下注相等={all_bets_equal}, 回合完成={round_complete}")
        
        return round_complete
    
    def next_phase(self) -> None:
        """进入下一个游戏阶段"""
        current_phase = self.state.phase
        logger.info(f"从阶段 {current_phase} 进入下一阶段")
        
        # 如果游戏已经结束，不要再尝试进入新阶段
        if self.state.is_game_over:
            logger.info("游戏已结束，不进入下一阶段")
            return
        
        # 重置所有活跃玩家的状态
        active_players = self.state.get_active_players()
        logger.info(f"活跃玩家数量: {len(active_players)}, 玩家ID: {[p.id for p in active_players]}")
        
        # 如果没有足够的活跃玩家，游戏结束
        if len(active_players) <= 1:
            logger.info("没有足够的活跃玩家，游戏结束")
            self.end_game()
            return
        
        # 重置所有活跃玩家的行动状态和当前下注
        for player in active_players:
            player.has_acted = False
            player.current_bet = 0
            logger.info(f"重置玩家 {player.id} 状态: has_acted=False, current_bet=0")
        
        # 根据当前阶段进入下一阶段
        if current_phase == GameStage.PRE_FLOP:
            # 发放翻牌
            self.state.community_cards.extend(self.dealer.deal_flop())
            self.state.phase = GameStage.FLOP
            self.phase = GameStage.FLOP  # 同步 phase
            logger.info(f"进入翻牌阶段，公共牌: {self.state.community_cards}")
        
        elif current_phase == GameStage.FLOP:
            # 发放转牌
            self.state.community_cards.append(self.dealer.deal_turn())
            self.state.phase = GameStage.TURN
            self.phase = GameStage.TURN  # 同步 phase
            logger.info(f"进入转牌阶段，公共牌: {self.state.community_cards}")
        
        elif current_phase == GameStage.TURN:
            # 发放河牌
            self.state.community_cards.append(self.dealer.deal_river())
            self.state.phase = GameStage.RIVER
            self.phase = GameStage.RIVER  # 同步 phase
            logger.info(f"进入河牌阶段，公共牌: {self.state.community_cards}")
        
        elif current_phase == GameStage.RIVER:
            # 进入摊牌阶段
            logger.info("河牌阶段结束，进入摊牌阶段")
            self.state.phase = GameStage.SHOWDOWN
            self.phase = GameStage.SHOWDOWN  # 同步 phase
            self.end_game()
            return
        
        elif current_phase == GameStage.SHOWDOWN or current_phase == GameStage.FINISHED:
            # 已经在结束阶段，不需要再处理
            logger.info("游戏已处于结束阶段，不再进入下一阶段")
            return
        
        # 只有在非结束阶段才需要设置下一个行动玩家
        if self.state.phase != GameStage.SHOWDOWN and self.state.phase != GameStage.FINISHED:
            # 重新获取活跃玩家列表（因为可能有玩家弃牌）
            active_players = self.state.get_active_players()
            if not active_players:
                logger.warning("没有活跃玩家，无法设置行动顺序")
                return
            
            # 按位置排序活跃玩家
            sorted_players = sorted(active_players, key=lambda p: p.position)
            logger.info(f"按位置排序后的活跃玩家: {[(p.id, p.position) for p in sorted_players]}")
            
            # 确定第一个行动玩家（德州扑克规则：从庄家左侧第一个活跃玩家开始）
            dealer_position = self.button_position
            logger.info(f"庄家位置: {dealer_position}")
            
            # 找到庄家后面的第一个活跃玩家
            first_player = None
            for player in sorted_players:
                if player.position > dealer_position:
                    first_player = player
                    logger.info(f"找到庄家后的第一个活跃玩家: {player.id}, 位置: {player.position}")
                    break
            
            # 如果没找到（庄家是最后一个位置），则从第一个位置开始
            if not first_player and sorted_players:
                first_player = sorted_players[0]
                logger.info(f"庄家是最后一个位置，从第一个位置开始: {first_player.id}, 位置: {first_player.position}")
            
            # 更新当前玩家
            if first_player:
                self.state.current_player = first_player.id
                self.current_player_idx = sorted_players.index(first_player)
                logger.info(f"新阶段第一个行动玩家: {first_player.id}, 位置: {first_player.position}")
            else:
                logger.warning("没有活跃玩家，无法设置第一个行动玩家")
                self.state.current_player = None

    def get_next_player(self) -> Optional[PlayerState]:
        """
        获取下一个应该行动的玩家
        
        根据玩家位置顺序，获取下一个有效的玩家
        """
        # 获取所有活跃玩家
        active_players = self.state.get_active_players()
        if not active_players:
            logger.info("没有活跃玩家")
            return None
        
        # 获取当前最大下注额
        max_bet = self.state.get_max_bet()
        logger.info(f"当前最大下注额: {max_bet}")
        
        # 如果当前没有玩家，则从庄家后第一个开始
        if not self.state.current_player:
            # 按位置排序
            sorted_players = sorted(active_players, key=lambda p: p.position)
            # 找到庄家后第一个活跃玩家
            dealer_position = self.state.dealer_position
            
            # 庄家后面的玩家
            next_players = [p for p in sorted_players if p.position > dealer_position]
            if next_players:
                logger.info(f"从庄家位置 {dealer_position} 后找到下一个玩家: {next_players[0].id}")
                return next_players[0]
            
            # 如果庄家后面没有玩家，则从头开始
            logger.info(f"庄家位置 {dealer_position} 后没有玩家，从头开始: {sorted_players[0].id}")
            return sorted_players[0]
        
        # 获取所有玩家（包括弃牌的）
        all_players = list(self.state.players.values())
        
        # 找到当前玩家，即使已经弃牌
        current_player = None
        for player in all_players:
            if player.id == self.state.current_player:
                current_player = player
                break
        
        if not current_player:
            logger.warning(f"找不到当前玩家: {self.state.current_player}")
            return active_players[0]
        
        # 根据位置排序所有活跃玩家
        sorted_players = sorted(active_players, key=lambda p: p.position)
        logger.debug(f"排序后的活跃玩家: {[(p.id, p.position) for p in sorted_players]}")
        
        # 找到当前玩家之后的第一个活跃玩家
        found_next = False
        for player in sorted_players:
            # 跳过当前玩家和之前的玩家
            if player.position <= current_player.position and not found_next:
                continue
            
            found_next = True
            
            # 找到的玩家如果没有行动或者下注不等于最大下注，则返回
            if not player.has_acted or (player.current_bet != max_bet and not player.is_all_in):
                logger.info(f"找到下一个玩家: {player.id}, 位置: {player.position}")
                return player
        
        # 从头开始找，直到当前玩家
        for player in sorted_players:
            # 如果到达当前玩家，停止查找
            if player.position >= current_player.position:
                break
            
            # 找到的玩家如果没有行动或者下注不等于最大下注，则返回
            if not player.has_acted or (player.current_bet != max_bet and not player.is_all_in):
                logger.info(f"找到下一个玩家(从头开始): {player.id}, 位置: {player.position}")
                return player
        
        # 没找到需要行动的玩家，说明回合已结束
        logger.info("没有找到需要行动的玩家，回合已结束")
        return None

    def update_current_player(self) -> None:
        """更新当前玩家"""
        # 获取所有活跃玩家
        active_players = self.state.get_active_players()
        
        # 记录原始当前玩家ID
        old_player_id = self.state.current_player
        logger.info(f"更新当前玩家，原始玩家: {old_player_id}")
        
        # 如果没有活跃玩家，将当前玩家设为None
        if not active_players:
            logger.info("没有活跃玩家，当前玩家设为None")
            self.state.current_player = None
            return
        
        # 如果只有一个活跃玩家，将当前玩家设为该玩家
        if len(active_players) == 1:
            self.state.current_player = active_players[0].id
            logger.info(f"只有一个活跃玩家，当前玩家设为: {self.state.current_player}")
            return
        
        # 获取下一个未行动玩家
        next_player = self.get_next_player()
        
        # 如果没有找到下一个玩家，说明所有玩家都已行动
        if next_player is None:
            logger.info("所有玩家都已行动，当前玩家设为None")
            self.state.current_player = None
            return
        
        # 更新当前玩家
        self.state.current_player = next_player.id
        logger.info(f"当前玩家从 {old_player_id} 更新为 {self.state.current_player}")
        
        # 更新current_player_idx
        for i, player in enumerate(active_players):
            if player.id == self.state.current_player:
                self.current_player_idx = i
                break

    def process_action(self, action: PlayerAction) -> Tuple[bool, Optional[Dict]]:
        """
        处理玩家行动
        
        返回值: (游戏是否结束, 结果字典)
        """
        # 如果游戏已经结束，直接返回
        if self.state.is_game_over:
            logger.warning("游戏已结束，无法处理行动")
            return True, self.get_results()
        
        # 获取当前玩家
        current_player = self.get_current_player()
        if current_player is None:
            logger.error("当前玩家为空，无法处理行动")
            return True, {"error": "当前玩家为空"}
        
        # 记录当前玩家ID
        player_id = current_player.id
        logger.info(f"处理玩家 {player_id} 的行动: {action.action_type}")
        
        # 确保行动的玩家ID与当前玩家匹配
        if action.player_id != player_id:
            logger.error(f"行动玩家ID({action.player_id})与当前玩家ID({player_id})不匹配")
            return False, None
        
        # 根据行动类型处理
        if action.action_type == ActionType.FOLD:
            self.state.fold_player(current_player.id)
            logger.info(f"玩家 {current_player.id} 弃牌")
            
            # 检查是否只剩一个玩家
            active_players = self.state.get_active_players()
            if len(active_players) == 1:
                logger.info(f"只剩一个活跃玩家: {active_players[0].id}")
                # 直接结束游戏
                self.state.is_game_over = True  # 设置游戏结束标志
                self._end_game()
                return True, self.get_results()
            
        elif action.action_type == ActionType.CHECK:
            # 设置玩家已行动标志
            current_player.has_acted = True
            logger.info(f"玩家 {current_player.id} 过牌，已标记为已行动")
            
        elif action.action_type == ActionType.CALL:
            self.state.call(current_player.id)
            logger.info(f"玩家 {current_player.id} 跟注")
            
        elif action.action_type == ActionType.RAISE:
            self.state.raise_bet(current_player.id, action.amount)
            logger.info(f"玩家 {current_player.id} 加注到 {action.amount}")
        
        # 记录行动
        self.state.add_action(action)
        logger.info(f"已记录玩家 {current_player.id} 的行动")
        
        # 立即更新当前玩家 - 确保在检查回合是否完成前更新
        self.update_current_player()
        logger.info(f"更新当前玩家为: {self.state.current_player}")
        
        # 检查回合是否完成
        round_complete = self.is_round_complete()
        logger.info(f"回合是否完成: {round_complete}")
        
        if round_complete:
            logger.info("回合完成，准备进入下一阶段")
            
            # 检查游戏是否应该结束（只有一个活跃玩家或到达摊牌阶段）
            active_players = self.state.get_active_players()
            logger.info(f"活跃玩家数量: {len(active_players)}, 当前游戏阶段: {self.state.phase}")
            
            if len(active_players) <= 1 or self.state.phase == GameStage.SHOWDOWN:
                logger.info("游戏结束条件满足，准备结束游戏")
                self.state.is_game_over = True
                return True, self.get_results()
            
            # 进入下一阶段
            logger.info("调用next_phase()进入下一阶段")
            self.next_phase()
        
        return False, None
    
    def _validate_action(self, player: PlayerState, action: PlayerAction) -> None:
        """验证动作合法性"""
        # 如果action_type已经是ActionType类型，直接使用
        if isinstance(action.action_type, ActionType):
            action_type = action.action_type
        else:
            # 如果是字符串，则转换为ActionType
            action_type = ActionType[str(action.action_type).upper()]
            
        # 获取当前最大下注
        max_bet = self.state.get_max_bet()
        
        if action_type == ActionType.CHECK:
            # 只有在当前最大下注等于玩家已下注时才能过牌
            if max_bet > player.current_bet:
                raise ValueError("当前无法过牌，必须跟注或弃牌")
                
        elif action_type == ActionType.CALL:
            # 计算需要跟注的金额
            call_amount = max_bet - player.current_bet
            
            # 特殊处理小盲注在第一轮的跟注
            if (self.phase == GameStage.PRE_FLOP and 
                player.current_bet == self.small_blind and
                not any(p.current_bet > self.big_blind for p in self.state.get_active_players())):
                call_amount = self.small_blind  # 只需要补齐到大盲注
                
            # 验证筹码是否足够
            if call_amount > player.chips:
                raise ValueError("筹码不足，可以选择全下")
                
        elif action_type == ActionType.RAISE:
            # 计算最小加注额
            min_raise_to = max_bet * 2  # 最小加注必须是当前最大注的两倍
            
            if action.amount < min_raise_to:
                raise ValueError(f"加注金额必须至少是当前最大注的两倍 ({min_raise_to})")
            if action.amount > player.chips:
                raise ValueError("筹码不足，可以选择全下")
    
    def _end_game(self) -> None:
        """结束游戏并结算"""
        try:
            logger.info("开始游戏结算")
            active_players = self.state.get_active_players()
            logger.info(f"活跃玩家数量: {len(active_players)}")
            
            # 设置游戏状态为结束
            self.phase = GameStage.FINISHED
            self.state.phase = GameStage.FINISHED  # 同步 phase
            self.state.is_game_over = True  # 设置游戏结束标志
            
            # 准备摊牌数据
            showdown_data = []
            winning_hand = None  # 初始化 winning_hand 变量
            
            # 结算逻辑
            if len(active_players) == 1:
                # 只剩一个玩家，直接获胜
                winner = active_players[0]
                pot_amount = self.state.pot
                self.state.award_pot(winner.id)
                logger.info(f"玩家 {winner.id} 获得底池 {pot_amount} 筹码")
                
                # 添加获胜者信息（因弃牌获胜）
                showdown_data.append({
                    "player_id": winner.id,
                    "hole_cards": winner.cards,  # 直接使用cards，不需要转换
                    "hand_rank": "WINNER_BY_FOLD",
                    "is_winner": True
                })
                
            else:
                # 比较手牌
                results = []
                for player in active_players:
                    try:
                        # 确保卡牌格式正确
                        player_cards = player.cards
                        community_cards = self.state.community_cards
                        
                        hand_result = HandEvaluator.evaluate_hand(
                            player_cards,
                            community_cards
                        )
                        results.append((player, hand_result))
                        # 添加玩家摊牌数据
                        showdown_data.append({
                            "player_id": player.id,
                            "hole_cards": player_cards,  # 直接使用cards，不需要转换
                            "hand_rank": hand_result.rank.name,
                            "is_winner": False  # 稍后更新获胜者
                        })
                    except Exception as e:
                        logger.error(f"评估玩家 {player.id} 手牌时出错: {str(e)}")
                        raise
                
                # 按手牌大小排序
                results.sort(key=lambda x: x[1], reverse=True)
                winner = results[0][0]
                winning_hand = results[0][1]
                pot_amount = self.state.pot
                
                # 更新获胜者标记
                for data in showdown_data:
                    if data["player_id"] == winner.id:
                        data["is_winner"] = True
                
                self.state.award_pot(winner.id)
                logger.info(f"玩家 {winner.id} 获胜，赢得底池 {pot_amount} 筹码")
            
            # 广播游戏结果
            self.state.game_result = {
                "winner_id": winner.id,
                "pot_amount": pot_amount,
                "winning_hand": winning_hand.rank.name if winning_hand else None,  # 处理 winning_hand 可能为 None 的情况
                "community_cards": self.state.community_cards,  # 直接使用community_cards，不需要转换
                "showdown_data": showdown_data  # 添加摊牌数据
            }
            
            # 停止所有AI玩家的行动
            self.state.stop_all_players()
            
            logger.info(f"游戏结果: {self.state.game_result}")
            
        except Exception as e:
            logger.error(f"游戏结算过程中出错: {str(e)}")
            raise

    def start_new_game(self) -> None:
        """开始新的一局游戏"""
        if self.phase != GameStage.FINISHED:
            raise ValueError("只能在游戏结束状态开始新一局")
        
        # 重置游戏状态
        self.dealer.reset_deck()
        self.state.reset_round()
        
        # 确保重置所有游戏结束标志和玩家状态
        self.state.is_game_over = False
        self.state.game_result = None  # 重置游戏结果
        
        # 重置所有玩家的行动状态
        for player in self.state.players.values():
            player.has_acted = False
            player.current_bet = 0
            player.total_bet = 0
            player.is_active = True  # 重新激活所有玩家
            player.is_all_in = False
            player.cards = []  # 清空手牌
        
        # 重置游戏阶段
        self.phase = GameStage.WAITING
        self.state.phase = GameStage.WAITING  # 同步 phase
        self.current_player_idx = 0
        
        # 检查玩家数量，避免除零错误
        if len(self.state.players) > 0:
            self.button_position = (self.button_position + 1) % len(self.state.players)
            logger.info(f"庄家位置轮动到: {self.button_position}")
        else:
            self.button_position = 0
            logger.warning("没有玩家，庄家位置重置为0")
        
        # 开始新的一局
        self.start_game()

    def evaluate_hand(self, player_id: str) -> tuple:
        """
        评估玩家的手牌
        
        Args:
            player_id: 玩家ID
            
        Returns:
            tuple: (HandResult, str) - 手牌评估结果和描述
        """
        player = self.state.players.get(player_id)
        if not player:
            raise ValueError(f"玩家 {player_id} 不存在")
            
        # 确保输入是列表类型
        hand_cards = list(player.cards) if isinstance(player.cards, list) else player.cards
        community_cards = list(self.state.community_cards) if isinstance(self.state.community_cards, list) else self.state.community_cards
        
        # 评估手牌
        result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
        
        # 生成描述
        descriptions = {
            HandRank.HIGH_CARD: "高牌",
            HandRank.PAIR: "一对",
            HandRank.TWO_PAIR: "两对",
            HandRank.THREE_OF_A_KIND: "三条",
            HandRank.STRAIGHT: "顺子",
            HandRank.FLUSH: "同花",
            HandRank.FULL_HOUSE: "葫芦",
            HandRank.FOUR_OF_A_KIND: "四条",
            HandRank.STRAIGHT_FLUSH: "同花顺",
            HandRank.ROYAL_FLUSH: "皇家同花顺"
        }
        
        description = descriptions.get(result.rank, "未知牌型")
        return result, description

    def get_next_position(self, current_position: int) -> int:
        """获取下一个有效位置"""
        active_players = self.state.get_active_players()
        positions = sorted(p.position for p in active_players)
        if not positions:
            return 0
        
        try:
            idx = positions.index(current_position)
            return positions[(idx + 1) % len(positions)]
        except ValueError:
            return positions[0]

    def end_game(self) -> None:
        """处理游戏结束"""
        logger.info("游戏结束，执行结算")
        
        # 设置游戏已结束标志
        self.state.is_game_over = True
        self.phase = GameStage.FINISHED
        self.state.phase = GameStage.FINISHED
        
        # 确保没有当前玩家
        self.state.current_player = None
        
        # 获取所有活跃玩家
        active_players = self.state.get_active_players()
        logger.info(f"结算时活跃玩家数量: {len(active_players)}")
        
        # 如果只有一个活跃玩家，直接将底池给他
        if len(active_players) == 1:
            winner = active_players[0]
            pot_amount = self.state.pot
            winner.chips += pot_amount
            logger.info(f"只有一个活跃玩家 {winner.id}，赢得底池 {pot_amount}")
            
            # 创建游戏结果
            self.state.game_result = {
                "winner_id": winner.id,
                "pot_amount": pot_amount,
                "winning_hand": None,
                "community_cards": self.state.community_cards,
                "showdown_data": [{
                    "player_id": winner.id,
                    "hole_cards": winner.cards,
                    "hand_rank": "WINNER_BY_FOLD",
                    "is_winner": True
                }]
            }
            
            # 清空底池
            self.state.pot = 0
            logger.info(f"游戏已结束，发送游戏结果: {self.state.game_result}")
            return
        
        # 如果有多个活跃玩家，需要比较牌面大小进行结算
        elif len(active_players) > 1:
            logger.info("需要比较牌面大小进行结算")
            
            # 比较牌面大小，找出获胜者
            best_hand = None
            winner = None
            showdown_data = []
            
            for player in active_players:
                try:
                    hand_result = HandEvaluator.evaluate_hand(
                        player.cards,
                        self.state.community_cards
                    )
                    
                    # 添加摊牌数据
                    player_data = {
                        "player_id": player.id,
                        "hole_cards": player.cards,
                        "hand_rank": hand_result.rank.name,
                        "is_winner": False  # 稍后更新
                    }
                    showdown_data.append(player_data)
                    
                    # 更新最佳手牌
                    if best_hand is None or hand_result > best_hand:
                        best_hand = hand_result
                        winner = player
                except Exception as e:
                    logger.error(f"评估玩家 {player.id} 手牌时出错: {str(e)}")
            
            # 找到获胜者后，分配底池
            if winner:
                pot_amount = self.state.pot
                winner.chips += pot_amount
                logger.info(f"玩家 {winner.id} 赢得底池 {pot_amount}")
                
                # 更新摊牌数据中的获胜者
                for data in showdown_data:
                    if data["player_id"] == winner.id:
                        data["is_winner"] = True
                
                # 创建游戏结果
                self.state.game_result = {
                    "winner_id": winner.id,
                    "pot_amount": pot_amount,
                    "winning_hand": best_hand.rank.name if best_hand else None,
                    "community_cards": self.state.community_cards,
                    "showdown_data": showdown_data
                }
                
                # 清空底池
                self.state.pot = 0
                logger.info(f"游戏已结束，发送游戏结果: {self.state.game_result}")
            else:
                logger.warning("无法确定获胜者，平分底池")
                self._split_pot(active_players)
        else:
            # 没有活跃玩家的情况
            logger.warning("没有活跃玩家，游戏无法正常结算")
            
            # 查找最后一个弃牌的玩家，暂时作为默认获胜者
            all_players = list(self.state.players.values())
            if all_players:
                default_winner = all_players[0]
                pot_amount = self.state.pot
                default_winner.chips += pot_amount
                
                # 创建游戏结果
                self.state.game_result = {
                    "winner_id": default_winner.id,
                    "pot_amount": pot_amount,
                    "winning_hand": None,
                    "community_cards": self.state.community_cards,
                    "showdown_data": [{
                        "player_id": default_winner.id,
                        "hole_cards": default_winner.cards,
                        "hand_rank": "DEFAULT_WINNER",
                        "is_winner": True
                    }]
                }
                
                logger.info(f"默认将底池 {pot_amount} 分配给玩家 {default_winner.id}")
                self.state.pot = 0
        
        # 停止所有玩家的行动，确保游戏结束
        self.state.stop_all_players()
    
    def _split_pot(self, players):
        """平分底池"""
        if not players:
            logger.warning("没有玩家，无法分配底池")
            return
            
        pot_per_player = self.state.pot // len(players)
        showdown_data = []
        
        for player in players:
            player.chips += pot_per_player
            logger.info(f"玩家 {player.id} 分得底池 {pot_per_player}")
            
            # 添加到摊牌数据
            showdown_data.append({
                "player_id": player.id,
                "hole_cards": player.cards,
                "hand_rank": "TIE",
                "is_winner": True  # 平局都是赢家
            })
        
        # 剩余的筹码给第一个玩家
        remainder = self.state.pot % len(players)
        if remainder > 0 and players:
            players[0].chips += remainder
            logger.info(f"玩家 {players[0].id} 额外分得余数 {remainder}")
        
        # 创建游戏结果（平局）
        self.state.game_result = {
            "winner_id": "TIE",
            "pot_amount": self.state.pot,
            "winning_hand": None,
            "community_cards": self.state.community_cards,
            "showdown_data": showdown_data
        }
        
        # 清空底池
        self.state.pot = 0

    def get_results(self) -> Dict:
        """获取游戏结果"""
        results = {
            "game_over": self.state.is_game_over,
            "pot": self.state.pot,
            "players": {},
            "winner_id": None,
            "pot_amount": 0,
            "community_cards": self.state.community_cards
        }
        
        # 如果游戏已结束且有游戏结果，添加结果信息
        if self.state.is_game_over and self.state.game_result:
            results.update({
                "winner_id": self.state.game_result["winner_id"],
                "pot_amount": self.state.game_result["pot_amount"],
                "winning_hand": self.state.game_result["winning_hand"],
                "showdown_data": self.state.game_result["showdown_data"]
            })
        
        # 添加玩家信息
        for player_id, player in self.state.players.items():
            # 直接使用player.cards，不进行转换
            results["players"][player_id] = {
                "chips": player.chips,
                "is_active": player.is_active,
                "cards": player.cards
            }
        
        return results
