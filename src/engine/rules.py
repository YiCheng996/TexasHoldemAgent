"""
规则系统模块。
负责德州扑克的牌型判断、大小比较和胜负判定。
"""

from enum import Enum, auto
from typing import List, Tuple, Set
from dataclasses import dataclass
from collections import Counter

from src.utils.logger import get_logger

logger = get_logger(__name__)

class HandRank(Enum):
    """德州扑克牌型枚举，按照大小排序"""
    HIGH_CARD = 1        # 高牌
    PAIR = 2             # 一对
    TWO_PAIR = 3         # 两对
    THREE_OF_A_KIND = 4  # 三条
    STRAIGHT = 5         # 顺子
    FLUSH = 6            # 同花
    FULL_HOUSE = 7       # 葫芦
    FOUR_OF_A_KIND = 8   # 四条
    STRAIGHT_FLUSH = 9   # 同花顺
    ROYAL_FLUSH = 10     # 皇家同花顺

@dataclass
class HandResult:
    """手牌结果类，用于存储牌型判断结果"""
    rank: HandRank                # 牌型
    hand_cards: List[str]         # 手牌
    community_cards: List[str]    # 公共牌
    best_five: List[str]         # 最佳五张牌组合
    kickers: List[str]           # 踢脚牌

class HandEvaluator:
    """手牌评估器，负责判断牌型和比较大小"""
    
    # 扑克牌点数到数值的映射
    RANK_VALUES = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
        '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }
    
    @staticmethod
    def get_rank_value(card: str) -> int:
        """获取牌面点数的数值"""
        return HandEvaluator.RANK_VALUES[card[:-1]]
    
    @staticmethod
    def get_suit(card: str) -> str:
        """获取牌的花色"""
        return card[-1]
    
    @staticmethod
    def evaluate_hand(hand_cards: List[str], community_cards: List[str]) -> HandResult:
        """
        评估一手牌的牌型
        
        Args:
            hand_cards: 两张手牌
            community_cards: 公共牌（3-5张）
            
        Returns:
            HandResult: 牌型判断结果
        """
        all_cards = hand_cards + community_cards
        
        # 检查同花顺（包括皇家同花顺）
        flush_result = HandEvaluator._check_flush(all_cards)
        if flush_result:
            straight_result = HandEvaluator._check_straight(flush_result)
            if straight_result:
                if HandEvaluator.get_rank_value(straight_result[0]) == 14:
                    return HandResult(
                        HandRank.ROYAL_FLUSH,
                        hand_cards,
                        community_cards,
                        straight_result,
                        []
                    )
                return HandResult(
                    HandRank.STRAIGHT_FLUSH,
                    hand_cards,
                    community_cards,
                    straight_result,
                    []
                )
        
        # 检查四条
        four_kind = HandEvaluator._check_four_of_a_kind(all_cards)
        if four_kind:
            return HandResult(
                HandRank.FOUR_OF_A_KIND,
                hand_cards,
                community_cards,
                four_kind[0],
                four_kind[1]
            )
        
        # 检查葫芦
        full_house = HandEvaluator._check_full_house(all_cards)
        if full_house:
            return HandResult(
                HandRank.FULL_HOUSE,
                hand_cards,
                community_cards,
                full_house,
                []
            )
        
        # 检查同花
        if flush_result:
            return HandResult(
                HandRank.FLUSH,
                hand_cards,
                community_cards,
                flush_result[:5],
                []
            )
        
        # 检查顺子
        straight = HandEvaluator._check_straight(all_cards)
        if straight:
            # 确保不是因为重复牌导致的假顺子
            values = [HandEvaluator.get_rank_value(card) for card in straight]
            if len(set(values)) == 5:  # 确保五张牌的点数都不同
                return HandResult(
                    HandRank.STRAIGHT,
                    hand_cards,
                    community_cards,
                    straight,
                    []
                )
        
        # 检查三条
        three_kind = HandEvaluator._check_three_of_a_kind(all_cards)
        if three_kind:
            return HandResult(
                HandRank.THREE_OF_A_KIND,
                hand_cards,
                community_cards,
                three_kind[0],
                three_kind[1]
            )
        
        # 检查两对
        two_pair = HandEvaluator._check_two_pair(all_cards)
        if two_pair:
            return HandResult(
                HandRank.TWO_PAIR,
                hand_cards,
                community_cards,
                two_pair[0],
                two_pair[1]
            )
        
        # 检查一对
        pair = HandEvaluator._check_pair(all_cards)
        if pair:
            return HandResult(
                HandRank.PAIR,
                hand_cards,
                community_cards,
                pair[0],
                pair[1]
            )
        
        # 高牌
        high_cards = sorted(
            all_cards,
            key=HandEvaluator.get_rank_value,
            reverse=True
        )
        return HandResult(
            HandRank.HIGH_CARD,
            hand_cards,
            community_cards,
            high_cards[:5],
            []
        )
    
    @staticmethod
    def _check_flush(cards: List[str]) -> List[str]:
        """检查同花"""
        suit_groups = {}
        for card in cards:
            suit = HandEvaluator.get_suit(card)
            suit_groups.setdefault(suit, []).append(card)
        
        for suit_cards in suit_groups.values():
            if len(suit_cards) >= 5:
                return sorted(
                    suit_cards,
                    key=HandEvaluator.get_rank_value,
                    reverse=True
                )
        return []
    
    @staticmethod
    def _check_straight(cards: List[str]) -> List[str]:
        """检查顺子"""
        # 获取所有点数的集合，并去除重复
        values = sorted(set(
            HandEvaluator.get_rank_value(card)
            for card in cards
        ))
        
        # 处理A可以作为1的特殊情况
        if 14 in values:
            values.append(1)
            
        # 寻找连续的五个数
        straight = []
        for i in range(len(values) - 4):
            if values[i+4] - values[i] == 4:
                # 找到对应的牌
                target_values = set(range(values[i], values[i] + 5))
                # 对于每个点数，只取一张牌
                straight = []
                used_values = set()
                for card in sorted(cards, key=HandEvaluator.get_rank_value, reverse=True):
                    value = HandEvaluator.get_rank_value(card)
                    if value in target_values and value not in used_values:
                        straight.append(card)
                        used_values.add(value)
                    if len(straight) == 5:
                        break
                break
                
        return straight
    
    @staticmethod
    def _check_four_of_a_kind(cards: List[str]) -> Tuple[List[str], List[str]]:
        """检查四条"""
        rank_groups = {}
        for card in cards:
            rank = card[:-1]
            rank_groups.setdefault(rank, []).append(card)
        
        four_cards = []
        for rank_cards in rank_groups.values():
            if len(rank_cards) == 4:
                four_cards = rank_cards
                break
                
        if four_cards:
            kickers = [
                card for card in cards
                if card not in four_cards
            ]
            kickers.sort(key=HandEvaluator.get_rank_value, reverse=True)
            return four_cards, kickers[:1]
            
        return None
    
    @staticmethod
    def _check_full_house(cards: List[str]) -> List[str]:
        """检查葫芦"""
        rank_groups = {}
        for card in cards:
            rank = card[:-1]
            rank_groups.setdefault(rank, []).append(card)
        
        three_cards = None
        pair_cards = None
        
        # 找最大的三条
        for rank_cards in sorted(
            rank_groups.values(),
            key=lambda x: (len(x), HandEvaluator.get_rank_value(x[0])),
            reverse=True
        ):
            if len(rank_cards) >= 3 and not three_cards:
                three_cards = rank_cards[:3]
            elif len(rank_cards) >= 2 and not pair_cards:
                pair_cards = rank_cards[:2]
            
            if three_cards and pair_cards:
                return three_cards + pair_cards
                
        return None
    
    @staticmethod
    def _check_three_of_a_kind(cards: List[str]) -> Tuple[List[str], List[str]]:
        """检查三条"""
        rank_groups = {}
        for card in cards:
            rank = card[:-1]
            rank_groups.setdefault(rank, []).append(card)
        
        three_cards = None
        for rank_cards in rank_groups.values():
            if len(rank_cards) == 3:
                three_cards = rank_cards
                break
                
        if three_cards:
            kickers = [
                card for card in cards
                if card not in three_cards
            ]
            kickers.sort(key=HandEvaluator.get_rank_value, reverse=True)
            return three_cards, kickers[:2]
            
        return None
    
    @staticmethod
    def _check_two_pair(cards: List[str]) -> Tuple[List[str], List[str]]:
        """检查两对"""
        rank_groups = {}
        for card in cards:
            rank = card[:-1]
            rank_groups.setdefault(rank, []).append(card)
        
        pairs = []
        for rank_cards in sorted(
            rank_groups.values(),
            key=lambda x: HandEvaluator.get_rank_value(x[0]),
            reverse=True
        ):
            if len(rank_cards) >= 2:
                pairs.append(rank_cards[:2])
            if len(pairs) == 2:
                break
                
        if len(pairs) == 2:
            pair_cards = pairs[0] + pairs[1]
            kickers = [
                card for card in cards
                if card not in pair_cards
            ]
            kickers.sort(key=HandEvaluator.get_rank_value, reverse=True)
            return pair_cards, kickers[:1]
            
        return None
    
    @staticmethod
    def _check_pair(cards: List[str]) -> Tuple[List[str], List[str]]:
        """检查一对"""
        rank_groups = {}
        for card in cards:
            rank = card[:-1]
            rank_groups.setdefault(rank, []).append(card)
        
        pair_cards = None
        for rank_cards in sorted(
            rank_groups.values(),
            key=lambda x: HandEvaluator.get_rank_value(x[0]),
            reverse=True
        ):
            if len(rank_cards) == 2:
                pair_cards = rank_cards
                break
                
        if pair_cards:
            kickers = [
                card for card in cards
                if card not in pair_cards
            ]
            kickers.sort(key=HandEvaluator.get_rank_value, reverse=True)
            return pair_cards, kickers[:3]
            
        return None
    
    @staticmethod
    def compare_hands(result1: HandResult, result2: HandResult) -> int:
        """
        比较两手牌的大小
        
        Args:
            result1: 第一手牌的结果
            result2: 第二手牌的结果
            
        Returns:
            int: 1表示result1赢，-1表示result2赢，0表示平局
        """
        # 首先比较牌型
        if result1.rank.value > result2.rank.value:
            return 1
        if result1.rank.value < result2.rank.value:
            return -1
            
        # 牌型相同，比较最佳五张牌
        for card1, card2 in zip(result1.best_five, result2.best_five):
            value1 = HandEvaluator.get_rank_value(card1)
            value2 = HandEvaluator.get_rank_value(card2)
            if value1 > value2:
                return 1
            if value1 < value2:
                return -1
                
        # 如果有踢脚牌，比较踢脚牌
        for card1, card2 in zip(result1.kickers, result2.kickers):
            value1 = HandEvaluator.get_rank_value(card1)
            value2 = HandEvaluator.get_rank_value(card2)
            if value1 > value2:
                return 1
            if value1 < value2:
                return -1
                
        # 所有牌都相同，平局
        return 0
