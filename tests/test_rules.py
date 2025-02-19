"""
规则系统模块测试。
测试德州扑克的牌型判断和大小比较功能。
"""

import pytest
from src.engine.rules import HandRank, HandResult, HandEvaluator

def test_hand_rank_order():
    """测试牌型大小顺序"""
    assert HandRank.HIGH_CARD.value < HandRank.PAIR.value
    assert HandRank.PAIR.value < HandRank.TWO_PAIR.value
    assert HandRank.TWO_PAIR.value < HandRank.THREE_OF_A_KIND.value
    assert HandRank.THREE_OF_A_KIND.value < HandRank.STRAIGHT.value
    assert HandRank.STRAIGHT.value < HandRank.FLUSH.value
    assert HandRank.FLUSH.value < HandRank.FULL_HOUSE.value
    assert HandRank.FULL_HOUSE.value < HandRank.FOUR_OF_A_KIND.value
    assert HandRank.FOUR_OF_A_KIND.value < HandRank.STRAIGHT_FLUSH.value
    assert HandRank.STRAIGHT_FLUSH.value < HandRank.ROYAL_FLUSH.value

def test_card_values():
    """测试牌面大小判断"""
    assert HandEvaluator.get_rank_value('2♠') == 2
    assert HandEvaluator.get_rank_value('A♥') == 14
    assert HandEvaluator.get_rank_value('K♦') == 13
    assert HandEvaluator.get_rank_value('10♣') == 10

def test_royal_flush():
    """测试皇家同花顺判断"""
    hand_cards = ['A♠', 'K♠']
    community_cards = ['Q♠', 'J♠', '10♠', '2♥', '3♦']
    result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
    assert result.rank == HandRank.ROYAL_FLUSH
    assert len(result.best_five) == 5
    assert all(card[-1] == '♠' for card in result.best_five)
    assert HandEvaluator.get_rank_value(result.best_five[0]) == 14  # Ace

def test_straight_flush():
    """测试同花顺判断"""
    hand_cards = ['9♥', '8♥']
    community_cards = ['7♥', '6♥', '5♥', '2♣', '3♦']
    result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
    assert result.rank == HandRank.STRAIGHT_FLUSH
    assert len(result.best_five) == 5
    assert all(card[-1] == '♥' for card in result.best_five)

def test_four_of_a_kind():
    """测试四条判断"""
    hand_cards = ['A♠', 'A♥']
    community_cards = ['A♦', 'A♣', 'K♠', 'Q♥', 'J♦']
    result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
    assert result.rank == HandRank.FOUR_OF_A_KIND
    assert len(result.best_five) == 4
    assert len(result.kickers) == 1
    assert result.kickers[0] == 'K♠'

def test_full_house():
    """测试葫芦判断"""
    hand_cards = ['K♠', 'K♥']
    community_cards = ['K♦', 'Q♣', 'Q♥', '2♦', '3♣']
    result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
    assert result.rank == HandRank.FULL_HOUSE
    assert len(result.best_five) == 5
    assert sum(1 for card in result.best_five if card[0] == 'K') == 3
    assert sum(1 for card in result.best_five if card[0] == 'Q') == 2

def test_flush():
    """测试同花判断"""
    hand_cards = ['A♣', 'K♣']
    community_cards = ['Q♣', '10♣', '5♣', '2♥', '3♦']
    result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
    assert result.rank == HandRank.FLUSH
    assert len(result.best_five) == 5
    assert all(card[-1] == '♣' for card in result.best_five)

def test_straight():
    """测试顺子判断"""
    hand_cards = ['9♠', '8♥']
    community_cards = ['7♦', '6♣', '5♥', '2♠', '3♦']
    result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
    assert result.rank == HandRank.STRAIGHT
    assert len(result.best_five) == 5
    values = [HandEvaluator.get_rank_value(card) for card in result.best_five]
    assert max(values) - min(values) == 4

def test_three_of_a_kind():
    """测试三条判断"""
    hand_cards = ['A♠', 'A♥']
    community_cards = ['A♦', 'K♣', 'Q♥', 'J♦', '10♠']
    result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
    assert result.rank == HandRank.THREE_OF_A_KIND
    assert len(result.best_five) == 3
    assert len(result.kickers) == 2
    assert all(card[0] == 'A' for card in result.best_five)

def test_two_pair():
    """测试两对判断"""
    hand_cards = ['A♠', 'A♥']
    community_cards = ['K♦', 'K♣', 'Q♥', 'J♦', '10♠']
    result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
    assert result.rank == HandRank.TWO_PAIR
    assert len(result.best_five) == 4
    assert len(result.kickers) == 1
    assert sum(1 for card in result.best_five if card[0] == 'A') == 2
    assert sum(1 for card in result.best_five if card[0] == 'K') == 2

def test_one_pair():
    """测试一对判断"""
    hand_cards = ['A♠', 'A♥']
    community_cards = ['K♦', 'Q♣', 'J♥', '10♦', '9♠']
    result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
    assert result.rank == HandRank.PAIR
    assert len(result.best_five) == 2
    assert len(result.kickers) == 3
    assert all(card[0] == 'A' for card in result.best_five)

def test_high_card():
    """测试高牌判断"""
    hand_cards = ['A♠', 'K♥']
    community_cards = ['Q♦', 'J♣', '9♥', '7♦', '5♠']
    result = HandEvaluator.evaluate_hand(hand_cards, community_cards)
    assert result.rank == HandRank.HIGH_CARD
    assert len(result.best_five) == 5
    assert HandEvaluator.get_rank_value(result.best_five[0]) == 14  # Ace

def test_compare_different_ranks():
    """测试不同牌型的大小比较"""
    # 同花顺 vs 四条
    straight_flush = HandResult(
        HandRank.STRAIGHT_FLUSH,
        ['9♥', '8♥'],
        ['7♥', '6♥', '5♥', '2♣', '3♦'],
        ['9♥', '8♥', '7♥', '6♥', '5♥'],
        []
    )
    four_kind = HandResult(
        HandRank.FOUR_OF_A_KIND,
        ['A♠', 'A♥'],
        ['A♦', 'A♣', 'K♠', 'Q♥', 'J♦'],
        ['A♠', 'A♥', 'A♦', 'A♣'],
        ['K♠']
    )
    assert HandEvaluator.compare_hands(straight_flush, four_kind) == 1
    assert HandEvaluator.compare_hands(four_kind, straight_flush) == -1

def test_compare_same_rank():
    """测试相同牌型的大小比较"""
    # 两个对子，但点数不同
    two_pair1 = HandResult(
        HandRank.TWO_PAIR,
        ['A♠', 'A♥'],
        ['K♦', 'K♣', 'Q♥', 'J♦', '10♠'],
        ['A♠', 'A♥', 'K♦', 'K♣'],
        ['Q♥']
    )
    two_pair2 = HandResult(
        HandRank.TWO_PAIR,
        ['K♠', 'K♥'],
        ['Q♦', 'Q♣', 'J♥', '10♦', '9♠'],
        ['K♠', 'K♥', 'Q♦', 'Q♣'],
        ['J♥']
    )
    assert HandEvaluator.compare_hands(two_pair1, two_pair2) == 1
    assert HandEvaluator.compare_hands(two_pair2, two_pair1) == -1

def test_compare_kickers():
    """测试踢脚牌比较"""
    # 相同的一对，比较踢脚牌
    pair1 = HandResult(
        HandRank.PAIR,
        ['A♠', 'A♥'],
        ['K♦', 'Q♣', 'J♥', '10♦', '9♠'],
        ['A♠', 'A♥'],
        ['K♦', 'Q♣', 'J♥']
    )
    pair2 = HandResult(
        HandRank.PAIR,
        ['A♣', 'A♦'],
        ['Q♥', 'J♣', '10♥', '9♦', '8♠'],
        ['A♣', 'A♦'],
        ['Q♥', 'J♣', '10♥']
    )
    assert HandEvaluator.compare_hands(pair1, pair2) == 1
    assert HandEvaluator.compare_hands(pair2, pair1) == -1

def test_compare_equal():
    """测试相等的情况"""
    # 完全相同的牌型
    flush1 = HandResult(
        HandRank.FLUSH,
        ['A♠', 'K♠'],
        ['Q♠', 'J♠', '9♠', '7♦', '5♣'],
        ['A♠', 'K♠', 'Q♠', 'J♠', '9♠'],
        []
    )
    flush2 = HandResult(
        HandRank.FLUSH,
        ['A♠', 'K♠'],
        ['Q♠', 'J♠', '9♠', '7♦', '5♣'],
        ['A♠', 'K♠', 'Q♠', 'J♠', '9♠'],
        []
    )
    assert HandEvaluator.compare_hands(flush1, flush2) == 0

def test_compare_same_pair_different_rank():
    """测试相同牌型但不同大小的一对"""
    # 一对6 vs 一对5
    pair_six = HandResult(
        HandRank.PAIR,
        ['6♠', '6♥'],
        ['K♦', 'Q♣', 'J♥', '10♦', '9♠'],
        ['6♠', '6♥'],
        ['K♦', 'Q♣', 'J♥']
    )
    pair_five = HandResult(
        HandRank.PAIR,
        ['5♣', '5♦'],
        ['K♥', 'Q♠', 'J♣', '10♥', '9♦'],
        ['5♣', '5♦'],
        ['K♥', 'Q♠', 'J♣']
    )
    assert HandEvaluator.compare_hands(pair_six, pair_five) == 1
    assert HandEvaluator.compare_hands(pair_five, pair_six) == -1

def test_compare_same_pair_same_rank():
    """测试相同大小的一对但踢脚牌不同"""
    # 都是一对2，比较踢脚牌
    pair_ace_kicker = HandResult(
        HandRank.PAIR,
        ['2♠', '2♥'],
        ['A♦', '3♣', '5♥', '7♦', '9♠'],
        ['2♠', '2♥'],
        ['A♦', '3♣', '5♥']
    )
    pair_eight_kicker = HandResult(
        HandRank.PAIR,
        ['2♣', '2♦'],
        ['8♥', '4♠', '5♣', '6♥', '7♦'],
        ['2♣', '2♦'],
        ['8♥', '4♠', '5♣']
    )
    assert HandEvaluator.compare_hands(pair_ace_kicker, pair_eight_kicker) == 1
    assert HandEvaluator.compare_hands(pair_eight_kicker, pair_ace_kicker) == -1

def test_compare_same_two_pairs():
    """测试相同的两对但大小不同"""
    # AA-KK vs AA-QQ
    two_pairs_ak = HandResult(
        HandRank.TWO_PAIR,
        ['A♠', 'A♥'],
        ['K♦', 'K♣', '2♥', '3♦', '4♠'],
        ['A♠', 'A♥', 'K♦', 'K♣'],
        ['2♥']
    )
    two_pairs_aq = HandResult(
        HandRank.TWO_PAIR,
        ['A♣', 'A♦'],
        ['Q♥', 'Q♠', '2♣', '3♥', '4♦'],
        ['A♣', 'A♦', 'Q♥', 'Q♠'],
        ['2♣']
    )
    assert HandEvaluator.compare_hands(two_pairs_ak, two_pairs_aq) == 1
    assert HandEvaluator.compare_hands(two_pairs_aq, two_pairs_ak) == -1

def test_compare_same_two_pairs_same_rank():
    """测试完全相同的两对但踢脚牌不同"""
    # 都是AA-KK，比较踢脚牌
    two_pairs_ace_kicker = HandResult(
        HandRank.TWO_PAIR,
        ['A♠', 'A♥'],
        ['K♦', 'K♣', 'Q♥', '3♦', '4♠'],
        ['A♠', 'A♥', 'K♦', 'K♣'],
        ['Q♥']
    )
    two_pairs_five_kicker = HandResult(
        HandRank.TWO_PAIR,
        ['A♣', 'A♦'],
        ['K♥', 'K♠', '5♣', '3♥', '4♦'],
        ['A♣', 'A♦', 'K♥', 'K♠'],
        ['5♣']
    )
    assert HandEvaluator.compare_hands(two_pairs_ace_kicker, two_pairs_five_kicker) == 1
    assert HandEvaluator.compare_hands(two_pairs_five_kicker, two_pairs_ace_kicker) == -1

def test_compare_same_three_kind():
    """测试相同的三条但大小不同"""
    # 三条A vs 三条K
    three_aces = HandResult(
        HandRank.THREE_OF_A_KIND,
        ['A♠', 'A♥'],
        ['A♦', 'K♣', 'Q♥', 'J♦', '10♠'],
        ['A♠', 'A♥', 'A♦'],
        ['K♣', 'Q♥']
    )
    three_kings = HandResult(
        HandRank.THREE_OF_A_KIND,
        ['K♠', 'K♥'],
        ['K♦', 'Q♣', 'J♥', '10♦', '9♠'],
        ['K♠', 'K♥', 'K♦'],
        ['Q♣', 'J♥']
    )
    assert HandEvaluator.compare_hands(three_aces, three_kings) == 1
    assert HandEvaluator.compare_hands(three_kings, three_aces) == -1

def test_compare_same_straight():
    """测试相同的顺子但大小不同"""
    # A-5顺子 vs 5-9顺子
    straight_ace = HandResult(
        HandRank.STRAIGHT,
        ['A♠', '2♥'],
        ['3♦', '4♣', '5♥', 'J♦', '10♠'],
        ['5♥', '4♣', '3♦', '2♥', 'A♠'],
        []
    )
    straight_nine = HandResult(
        HandRank.STRAIGHT,
        ['9♠', '8♥'],
        ['7♦', '6♣', '5♥', 'J♦', '10♠'],
        ['9♠', '8♥', '7♦', '6♣', '5♥'],
        []
    )
    assert HandEvaluator.compare_hands(straight_nine, straight_ace) == 1
    assert HandEvaluator.compare_hands(straight_ace, straight_nine) == -1

def test_compare_same_flush():
    """测试相同的同花但大小不同"""
    # A高同花 vs K高同花
    flush_ace = HandResult(
        HandRank.FLUSH,
        ['A♠', 'K♠'],
        ['Q♠', 'J♠', '9♠', '7♦', '5♣'],
        ['A♠', 'K♠', 'Q♠', 'J♠', '9♠'],
        []
    )
    flush_king = HandResult(
        HandRank.FLUSH,
        ['K♥', 'Q♥'],
        ['J♥', '10♥', '8♥', '7♦', '5♣'],
        ['K♥', 'Q♥', 'J♥', '10♥', '8♥'],
        []
    )
    assert HandEvaluator.compare_hands(flush_ace, flush_king) == 1
    assert HandEvaluator.compare_hands(flush_king, flush_ace) == -1

def test_compare_same_rank_different_suits():
    """测试相同牌型不同花色的比较"""
    # 一对A，不同花色
    pair_spades_hearts = HandResult(
        HandRank.PAIR,
        ['A♠', 'A♥'],
        ['K♦', 'Q♣', 'J♥', '10♦', '9♠'],
        ['A♠', 'A♥'],
        ['K♦', 'Q♣', 'J♥']
    )
    pair_clubs_diamonds = HandResult(
        HandRank.PAIR,
        ['A♣', 'A♦'],
        ['K♥', 'Q♠', 'J♣', '10♥', '9♦'],
        ['A♣', 'A♦'],
        ['K♥', 'Q♠', 'J♣']
    )
    assert HandEvaluator.compare_hands(pair_spades_hearts, pair_clubs_diamonds) == 0

def test_compare_different_suits_with_kickers():
    """测试不同花色但有相同踢脚牌的比较"""
    # 两对AK，不同花色
    two_pair1 = HandResult(
        HandRank.TWO_PAIR,
        ['A♠', 'A♥'],
        ['K♦', 'K♣', 'Q♥', '3♦', '4♠'],
        ['A♠', 'A♥', 'K♦', 'K♣'],
        ['Q♥']
    )
    two_pair2 = HandResult(
        HandRank.TWO_PAIR,
        ['A♣', 'A♦'],
        ['K♥', 'K♠', 'Q♥', '3♥', '4♦'],
        ['A♣', 'A♦', 'K♥', 'K♠'],
        ['Q♥']
    )
    assert HandEvaluator.compare_hands(two_pair1, two_pair2) == 0

def test_compare_straight_different_suits():
    """测试不同花色的顺子比较"""
    # 10-A顺子，不同花色组合
    straight1 = HandResult(
        HandRank.STRAIGHT,
        ['A♠', 'K♥'],
        ['Q♦', 'J♣', '10♥', '2♦', '3♠'],
        ['A♠', 'K♥', 'Q♦', 'J♣', '10♥'],
        []
    )
    straight2 = HandResult(
        HandRank.STRAIGHT,
        ['A♣', 'K♦'],
        ['Q♥', 'J♠', '10♣', '2♥', '3♦'],
        ['A♣', 'K♦', 'Q♥', 'J♠', '10♣'],
        []
    )
    assert HandEvaluator.compare_hands(straight1, straight2) == 0

def test_compare_three_kind_different_suits():
    """测试不同花色的三条比较"""
    # 三条A，不同花色组合
    three_kind1 = HandResult(
        HandRank.THREE_OF_A_KIND,
        ['A♠', 'A♥'],
        ['A♦', 'K♣', 'Q♥', 'J♦', '10♠'],
        ['A♠', 'A♥', 'A♦'],
        ['K♣', 'Q♥']
    )
    three_kind2 = HandResult(
        HandRank.THREE_OF_A_KIND,
        ['A♣', 'A♦'],
        ['A♥', 'K♠', 'Q♦', 'J♥', '10♣'],
        ['A♣', 'A♦', 'A♥'],
        ['K♠', 'Q♦']
    )
    assert HandEvaluator.compare_hands(three_kind1, three_kind2) == 0

def test_compare_four_kind_different_suits():
    """测试不同花色的四条比较"""
    # 四条A，不同花色组合顺序
    four_kind1 = HandResult(
        HandRank.FOUR_OF_A_KIND,
        ['A♠', 'A♥'],
        ['A♦', 'A♣', 'K♠', 'Q♥', 'J♦'],
        ['A♠', 'A♥', 'A♦', 'A♣'],
        ['K♠']
    )
    four_kind2 = HandResult(
        HandRank.FOUR_OF_A_KIND,
        ['A♣', 'A♦'],
        ['A♥', 'A♠', 'K♠', 'Q♥', 'J♦'],
        ['A♣', 'A♦', 'A♥', 'A♠'],
        ['K♠']
    )
    assert HandEvaluator.compare_hands(four_kind1, four_kind2) == 0 