"""
游戏主逻辑模块。
负责德州扑克游戏的核心流程控制，包括状态管理、回合控制和动作验证。
"""

from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from src.engine.state import GameState, PlayerState
from src.engine.dealer import Dealer
from src.engine.rules import HandEvaluator, HandResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

class GamePhase(Enum):
    """游戏阶段枚举"""
    WAITING = auto()        # 等待开始
    DEALING = auto()        # 发牌阶段
    PRE_FLOP = auto()      # 翻牌前
    FLOP = auto()          # 翻牌
    TURN = auto()          # 转牌
    RIVER = auto()         # 河牌
    SHOWDOWN = auto()      # 摊牌
    FINISHED = auto()      # 结束

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
    
    def model_dump(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "player_id": self.player_id,
            "action_type": self.action_type.name,  # 使用枚举的名称
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
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
        self.phase = GamePhase.WAITING
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
        if self.phase != GamePhase.WAITING:
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
        if self.phase != GamePhase.WAITING:
            raise ValueError("Game already started")
            
        # 移动庄家位置
        active_players = self.state.get_active_players()
        max_position = max(p.position for p in active_players)
        self.button_position = (self.button_position + 1) % (max_position + 1)
        logger.info(f"庄家位置移动到: {self.button_position}")
        
        # 重置游戏状态
        self.dealer.shuffle()
        self.phase = GamePhase.DEALING
        self.state.reset_round()
        
        # 发手牌
        hole_cards = self.dealer.deal_hole_cards(len(active_players))
        for player, cards in zip(active_players, hole_cards):
            self.state.set_player_cards(player.id, cards)
            
        # 设置盲注
        self.post_blinds()
        
        self.phase = GamePhase.PRE_FLOP
        logger.info(f"Game {self.game_id} started")
    
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
        active_players = self.state.get_active_players()
        if not active_players:
            return None
        return active_players[self.current_player_idx]
    
    def is_round_complete(self) -> bool:
        """检查当前回合是否结束"""
        active_players = self.state.get_active_players()
        if len(active_players) <= 1:
            logger.info("只剩一个活跃玩家，回合结束")
            return True
            
        # 获取当前最大下注额
        max_bet = self.state.get_max_bet()
        logger.info(f"当前最大下注额: {max_bet}")
        
        # 检查所有活跃玩家是否都已行动且下注相等
        for player in active_players:
            logger.info(f"检查玩家 {player.id}: has_acted={player.has_acted}, current_bet={player.current_bet}, is_all_in={player.is_all_in}")
            # 如果有玩家未行动且不是全下状态，回合未结束
            if not player.has_acted and not player.is_all_in:
                logger.info(f"玩家 {player.id} 未行动且未全下，回合继续")
                return False
            # 如果玩家下注不等于最大下注且不是全下状态，回合未结束
            if player.current_bet != max_bet and not player.is_all_in:
                logger.info(f"玩家 {player.id} 下注不等于最大下注且未全下，回合继续")
                return False
        
        # 如果所有玩家都已行动且下注相等，检查是否在河牌阶段
        if self.phase == GamePhase.RIVER:
            logger.info("河牌阶段结束，进入摊牌")
            return True
            
        logger.info("所有玩家都已行动且下注相等或全下，回合结束")
        return True
    
    def next_phase(self) -> None:
        """进入下一个游戏阶段"""
        if self.phase == GamePhase.PRE_FLOP:
            self.phase = GamePhase.FLOP
            # 发放三张翻牌
            flop_cards = self.dealer.deal_flop()
            self.state.community_cards = flop_cards
            logger.info(f"发放翻牌: {flop_cards}")
        elif self.phase == GamePhase.FLOP:
            self.phase = GamePhase.TURN
            # 发放转牌
            turn_card = self.dealer.deal_turn()
            self.state.community_cards.append(turn_card)
            logger.info(f"发放转牌: {turn_card}")
        elif self.phase == GamePhase.TURN:
            self.phase = GamePhase.RIVER
            # 发放河牌
            river_card = self.dealer.deal_river()
            self.state.community_cards.append(river_card)
            logger.info(f"发放河牌: {river_card}")
        elif self.phase == GamePhase.RIVER:
            # 进入摊牌阶段并直接结算
            self.phase = GamePhase.SHOWDOWN
            logger.info("进入摊牌阶段")
            self._end_game()
            return
        else:
            raise ValueError(f"Invalid phase transition from {self.phase}")
            
        # 重置玩家行动状态和当前下注
        active_players = self.state.get_active_players()
        for player in active_players:
            player.has_acted = False
            player.current_bet = 0  # 重置当前下注
            
        # 设置第一个行动玩家（庄家后第一位）
        self.current_player_idx = 0  # 重置为第一个位置，因为get_active_players已经按正确顺序排序
        self.state.current_player = active_players[0].id
        
        logger.info(f"Game {self.game_id} entered {self.phase}")
        logger.info(f"当前公共牌: {self.state.community_cards}")
        logger.info(f"当前玩家: {self.state.current_player}")
    
    def get_next_player(self) -> Optional[PlayerState]:
        """获取下一个应该行动的玩家"""
        active_players = self.state.get_active_players()
        if not active_players:
            return None
            
        # 获取当前最大下注额
        max_bet = self.state.get_max_bet()
        logger.info(f"当前最大下注额: {max_bet}")
        
        # 获取当前玩家的位置
        current_player = next((p for p in active_players if p.id == self.state.current_player), None)
        if not current_player:
            # 如果找不到当前玩家，从第一个位置开始
            return active_players[0]
            
        # 获取最大位置编号
        max_position = max(p.position for p in active_players)
        
        # 从当前玩家位置开始，按顺序检查下一个玩家
        next_position = (current_player.position + 1) % (max_position + 1)
        start_position = next_position
        
        # 遍历一圈
        while True:
            # 找到下一个位置的玩家
            next_player = next((p for p in active_players if p.position == next_position), None)
            
            if next_player:
                logger.info(f"检查玩家 {next_player.id}: has_acted={next_player.has_acted}, current_bet={next_player.current_bet}, is_all_in={next_player.is_all_in}")
                
                # 如果玩家未行动且不是全下状态
                if not next_player.has_acted and not next_player.is_all_in:
                    logger.info(f"玩家 {next_player.id} 未行动且未全下，轮到他行动")
                    return next_player
                    
                # 如果玩家下注不等于最大下注且不是全下状态
                if next_player.current_bet != max_bet and not next_player.is_all_in:
                    logger.info(f"玩家 {next_player.id} 下注不等于最大下注且未全下，轮到他行动")
                    return next_player
                    
            # 移动到下一个位置
            next_position = (next_position + 1) % (max_position + 1)
            
            # 如果已经检查了一圈，结束
            if next_position == start_position:
                break
                
        # 如果所有玩家都已完成行动，返回None表示回合结束
        logger.info("所有玩家都已完成行动，回合结束")
        return None

    def update_current_player(self) -> None:
        """更新当前行动玩家"""
        next_player = self.get_next_player()
        if next_player:
            self.state.current_player = next_player.id
            # 更新current_player_idx以匹配新的当前玩家
            active_players = self.state.get_active_players()
            self.current_player_idx = active_players.index(next_player)
            logger.info(f"当前玩家更新为: {next_player.id}")
        else:
            logger.info("所有玩家都已完成行动")
            self.state.current_player = None

    def process_action(self, action: PlayerAction) -> None:
        """
        处理玩家动作
        
        Args:
            action: 玩家动作
        """
        current_player = self.get_current_player()
        if not current_player or current_player.id != action.player_id:
            raise ValueError("现在不是您的回合")
            
        # 验证动作合法性
        self._validate_action(current_player, action)
        
        # 记录动作到历史记录
        logger.info(f"处理玩家 {action.player_id} 的动作: {action.action_type.name}")
        self.state.round_actions.append(action)
        
        # 执行动作
        if action.action_type == ActionType.FOLD:
            self.state.fold_player(action.player_id)
            logger.info(f"玩家 {action.player_id} 弃牌")
        elif action.action_type == ActionType.CALL:
            self.state.call(action.player_id)
            logger.info(f"玩家 {action.player_id} 跟注")
        elif action.action_type == ActionType.RAISE:
            self.state.raise_bet(action.player_id, action.amount)
            logger.info(f"玩家 {action.player_id} 加注到 {action.amount}")
        elif action.action_type == ActionType.ALL_IN:
            self.state.all_in(action.player_id)
            logger.info(f"玩家 {action.player_id} 全下")
        elif action.action_type == ActionType.CHECK:
            logger.info(f"玩家 {action.player_id} 过牌")
        
        # 标记玩家已行动
        current_player.has_acted = True
        logger.info(f"玩家 {action.player_id} 已标记为已行动")
        
        # 如果是加注，重置其他玩家的has_acted状态
        if action.action_type == ActionType.RAISE or action.action_type == ActionType.ALL_IN:
            for player in self.state.get_active_players():
                if player.id != action.player_id and not player.is_all_in:
                    player.has_acted = False
                    logger.info(f"由于{action.action_type.name}，重置玩家 {player.id} 的行动状态")
        
        # 更新当前玩家
        self.update_current_player()
        
        # 检查回合是否结束
        if self.is_round_complete():
            logger.info("回合结束，所有玩家都已行动")
            self.next_phase()
    
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
            if (self.phase == GamePhase.PRE_FLOP and 
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
            
            if len(active_players) == 1:
                # 只剩一个玩家，直接获胜
                winner = active_players[0]
                logger.info(f"只剩一个玩家 {winner.id}，直接获胜")
                # 在记录日志前先获取底池金额
                pot_amount = self.state.pot
                self.state.award_pot(winner.id)
                logger.info(f"玩家 {winner.id} 获胜，赢得底池 {pot_amount} 筹码")
                winning_hand = None
            else:
                # 比较手牌大小
                results = []
                logger.info("开始比较手牌:")
                for player in active_players:
                    try:
                        hand_result = HandEvaluator.evaluate_hand(
                            player.cards,
                            self.state.community_cards
                        )
                        results.append((player, hand_result))
                        logger.info(f"玩家 {player.id} 的手牌: {player.cards}, 公共牌: {self.state.community_cards}, 牌型: {hand_result.rank}")
                    except Exception as e:
                        logger.error(f"评估玩家 {player.id} 手牌时出错: {str(e)}")
                        raise
                
                # 按手牌大小排序
                results.sort(key=lambda x: x[1], reverse=True)
                winner = results[0][0]
                winning_hand = results[0][1]
                
                logger.info(f"获胜者是 {winner.id}，牌型: {winning_hand.rank}")
                self.state.award_pot(winner.id)
                logger.info(f"玩家 {winner.id} 获胜，赢得底池 {self.state.pot} 筹码")
            
            # 设置游戏状态为结束
            self.phase = GamePhase.FINISHED
            
            # 广播游戏结果
            self.state.game_result = {
                "winner_id": winner.id,
                "pot_amount": self.state.pot,
                "winning_hand": winning_hand.rank.name if winning_hand else None,
                "community_cards": self.state.community_cards
            }
            logger.info(f"游戏结果: {self.state.game_result}")
            
            # 重置游戏状态，准备下一局
            self.dealer.reset_deck()
            self.state.reset_round()
            self.phase = GamePhase.WAITING
            self.current_player_idx = 0
            self.button_position = (self.button_position + 1) % len(self.state.players)  # 移动庄家位置
            
            logger.info("游戏结算完成，准备开始新一局")
            
            # 开始新的一局
            self.start_game()
            
        except Exception as e:
            logger.error(f"游戏结算过程中出错: {str(e)}")
            raise

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
