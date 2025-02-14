"""
发牌系统模块。
负责扑克牌的生成、洗牌、发牌等操作。
"""

import random
from typing import List, Set, Tuple
from dataclasses import dataclass, field

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 扑克牌花色和点数
SUITS = ['♠', '♥', '♦', '♣']  # 黑桃、红心、方块、梅花
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

@dataclass
class Dealer:
    """发牌员类，负责管理和发放扑克牌"""
    
    deck: List[str] = field(default_factory=list)  # 牌堆
    dealt_cards: Set[str] = field(default_factory=set)  # 已发出的牌
    burnt_cards: List[str] = field(default_factory=list)  # 烧牌
    
    def __post_init__(self):
        """初始化牌堆"""
        self.logger = get_logger(__name__)
        self.reset_deck()
        
    def reset_deck(self):
        """重置牌堆到初始状态"""
        self.deck = [f"{rank}{suit}" for suit in SUITS for rank in RANKS]
        self.dealt_cards.clear()
        self.burnt_cards.clear()
        self.shuffle()
        self.logger.info("Deck has been reset and shuffled")
        
    def shuffle(self):
        """洗牌"""
        random.shuffle(self.deck)
        self.logger.debug("Deck has been shuffled")
        
    def burn_card(self) -> str:
        """
        烧一张牌
        
        Returns:
            str: 烧掉的牌
        """
        if not self.deck:
            self.logger.error("No cards left to burn")
            raise ValueError("No cards left to burn")
            
        card = self.deck.pop()
        self.burnt_cards.append(card)
        self.logger.debug(f"Burned card: {card}")
        return card
        
    def deal_card(self) -> str:
        """
        发一张牌
        
        Returns:
            str: 发出的牌
        """
        if not self.deck:
            self.logger.error("No cards left to deal")
            raise ValueError("No cards left to deal")
            
        card = self.deck.pop()
        self.dealt_cards.add(card)
        self.logger.debug(f"Dealt card: {card}")
        return card
        
    def deal_hole_cards(self, num_players: int) -> List[Tuple[str, str]]:
        """
        发手牌给多个玩家
        
        Args:
            num_players: 玩家数量
            
        Returns:
            List[Tuple[str, str]]: 每个玩家的两张手牌
        """
        if num_players * 2 > len(self.deck):
            self.logger.error(f"Not enough cards for {num_players} players")
            raise ValueError(f"Not enough cards for {num_players} players")
            
        hole_cards = []
        for _ in range(num_players):
            player_cards = (self.deal_card(), self.deal_card())
            hole_cards.append(player_cards)
            
        self.logger.info(f"Dealt hole cards to {num_players} players")
        return hole_cards
        
    def deal_community_cards(self, count: int) -> List[str]:
        """
        发公共牌
        
        Args:
            count: 要发的牌数量
            
        Returns:
            List[str]: 发出的公共牌
        """
        if count > len(self.deck):
            self.logger.error(f"Not enough cards to deal {count} community cards")
            raise ValueError(f"Not enough cards to deal {count} community cards")
            
        # 先烧一张牌
        self.burn_card()
        
        # 发指定数量的公共牌
        cards = []
        for _ in range(count):
            cards.append(self.deal_card())
            
        self.logger.info(f"Dealt {count} community cards: {cards}")
        return cards
        
    def deal_flop(self) -> List[str]:
        """
        发翻牌圈的三张公共牌
        
        Returns:
            List[str]: 三张翻牌
        """
        return self.deal_community_cards(3)
        
    def deal_turn(self) -> str:
        """
        发转牌
        
        Returns:
            str: 转牌
        """
        return self.deal_community_cards(1)[0]
        
    def deal_river(self) -> str:
        """
        发河牌
        
        Returns:
            str: 河牌
        """
        return self.deal_community_cards(1)[0]
        
    def get_remaining_cards(self) -> List[str]:
        """
        获取剩余的牌
        
        Returns:
            List[str]: 牌堆中剩余的牌
        """
        return self.deck.copy()
        
    def get_dealt_cards(self) -> Set[str]:
        """
        获取已经发出的牌
        
        Returns:
            Set[str]: 已发出的牌的集合
        """
        return self.dealt_cards.copy()
        
    def get_burnt_cards(self) -> List[str]:
        """
        获取已经烧掉的牌
        
        Returns:
            List[str]: 烧掉的牌列表
        """
        return self.burnt_cards.copy()
