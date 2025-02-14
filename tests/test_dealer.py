"""
发牌系统模块测试。
测试扑克牌的生成、洗牌、发牌等功能。
"""

import pytest
from src.engine.dealer import Dealer, SUITS, RANKS

@pytest.fixture
def dealer():
    """创建发牌员实例"""
    return Dealer()

def test_deck_initialization(dealer):
    """测试牌堆初始化"""
    # 检查牌堆大小
    assert len(dealer.deck) == len(SUITS) * len(RANKS)
    
    # 检查所有牌都存在且唯一
    all_cards = set(dealer.deck)
    assert len(all_cards) == len(SUITS) * len(RANKS)
    
    # 检查牌的格式
    for card in dealer.deck:
        rank = card[:-1]
        suit = card[-1]
        assert rank in RANKS
        assert suit in SUITS

def test_shuffle(dealer):
    """测试洗牌"""
    original_deck = dealer.deck.copy()
    dealer.shuffle()
    
    # 检查洗牌后的牌数量不变
    assert len(dealer.deck) == len(original_deck)
    
    # 检查所有牌都还在（只是顺序可能变了）
    assert set(dealer.deck) == set(original_deck)
    
    # 检查是否真的打乱了顺序（这个测试可能偶尔失败，但概率很小）
    assert dealer.deck != original_deck

def test_burn_card(dealer):
    """测试烧牌"""
    initial_deck_size = len(dealer.deck)
    
    # 烧一张牌
    burnt_card = dealer.burn_card()
    
    # 检查牌堆大小减少
    assert len(dealer.deck) == initial_deck_size - 1
    
    # 检查烧牌记录
    assert len(dealer.burnt_cards) == 1
    assert dealer.burnt_cards[0] == burnt_card
    
    # 检查烧牌不在牌堆中
    assert burnt_card not in dealer.deck

def test_deal_card(dealer):
    """测试发牌"""
    initial_deck_size = len(dealer.deck)
    
    # 发一张牌
    dealt_card = dealer.deal_card()
    
    # 检查牌堆大小减少
    assert len(dealer.deck) == initial_deck_size - 1
    
    # 检查发出的牌记录
    assert dealt_card in dealer.dealt_cards
    
    # 检查发出的牌不在牌堆中
    assert dealt_card not in dealer.deck

def test_deal_hole_cards(dealer):
    """测试发手牌"""
    num_players = 3
    initial_deck_size = len(dealer.deck)
    
    # 发手牌
    hole_cards = dealer.deal_hole_cards(num_players)
    
    # 检查发出的手牌数量
    assert len(hole_cards) == num_players
    assert all(len(cards) == 2 for cards in hole_cards)
    
    # 检查牌堆大小减少
    assert len(dealer.deck) == initial_deck_size - (num_players * 2)
    
    # 检查所有发出的牌都被记录
    dealt_cards = set()
    for cards in hole_cards:
        dealt_cards.update(cards)
    assert dealt_cards.issubset(dealer.dealt_cards)
    
    # 检查没有重复的牌
    assert len(dealt_cards) == num_players * 2

def test_deal_community_cards(dealer):
    """测试发公共牌"""
    initial_deck_size = len(dealer.deck)
    
    # 发三张翻牌
    flop = dealer.deal_flop()
    assert len(flop) == 3
    assert len(dealer.deck) == initial_deck_size - 4  # 3张翻牌 + 1张烧牌
    
    # 发转牌
    turn = dealer.deal_turn()
    assert isinstance(turn, str)
    assert len(dealer.deck) == initial_deck_size - 6  # 再加1张转牌 + 1张烧牌
    
    # 发河牌
    river = dealer.deal_river()
    assert isinstance(river, str)
    assert len(dealer.deck) == initial_deck_size - 8  # 再加1张河牌 + 1张烧牌
    
    # 检查所有牌都不重复
    all_cards = set(flop + [turn, river])
    assert len(all_cards) == 5
    assert all_cards.issubset(dealer.dealt_cards)

def test_deck_empty_error(dealer):
    """测试牌堆耗尽的错误处理"""
    # 发完所有牌
    while dealer.deck:
        dealer.deal_card()
        
    # 尝试继续发牌应该抛出异常
    with pytest.raises(ValueError):
        dealer.deal_card()
        
    with pytest.raises(ValueError):
        dealer.burn_card()
        
    with pytest.raises(ValueError):
        dealer.deal_hole_cards(1)
        
    with pytest.raises(ValueError):
        dealer.deal_community_cards(1)

def test_reset_deck(dealer):
    """测试重置牌堆"""
    # 发一些牌
    dealer.deal_hole_cards(2)
    dealer.deal_flop()
    
    # 重置牌堆
    dealer.reset_deck()
    
    # 检查状态重置
    assert len(dealer.deck) == len(SUITS) * len(RANKS)
    assert len(dealer.dealt_cards) == 0
    assert len(dealer.burnt_cards) == 0

def test_card_tracking(dealer):
    """测试牌的追踪"""
    # 发一些牌
    hole_cards = dealer.deal_hole_cards(2)
    flop = dealer.deal_flop()
    turn = dealer.deal_turn()
    river = dealer.deal_river()
    
    # 检查已发牌的记录
    dealt_cards = dealer.get_dealt_cards()
    assert len(dealt_cards) == 9  # 4张手牌 + 5张公共牌
    
    # 检查烧牌的记录
    burnt_cards = dealer.get_burnt_cards()
    assert len(burnt_cards) == 3  # 翻牌前、转牌前、河牌前各烧一张
    
    # 检查剩余牌的数量
    remaining_cards = dealer.get_remaining_cards()
    assert len(remaining_cards) == 52 - 9 - 3  # 总牌数 - 发出的牌 - 烧掉的牌 