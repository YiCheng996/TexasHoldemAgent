"""
游戏状态管理模块测试。
测试游戏状态的创建、修改和查询功能。
"""

import pytest
from datetime import datetime

from src.engine.state import GameState, PlayerState, GameStage, PlayerAction

@pytest.fixture
def game_state():
    """创建基本的游戏状态"""
    return GameState()

@pytest.fixture
def game_with_players(game_state):
    """创建包含玩家的游戏状态"""
    game_state.add_player("player1", 1000)
    game_state.add_player("player2", 1000)
    game_state.add_player("player3", 1000)
    return game_state

def test_game_state_creation(game_state):
    """测试游戏状态创建"""
    assert game_state.stage == GameStage.WAITING
    assert len(game_state.players) == 0
    assert len(game_state.community_cards) == 0
    assert game_state.pot == 0
    assert isinstance(game_state.start_time, datetime)
    assert game_state.end_time is None

def test_add_player(game_state):
    """测试添加玩家"""
    # 测试正常添加
    assert game_state.add_player("player1", 1000)
    assert "player1" in game_state.players
    assert game_state.players["player1"].chips == 1000
    assert game_state.players["player1"].position == 0
    
    # 测试重复添加
    assert not game_state.add_player("player1", 1000)
    
    # 测试添加满员
    for i in range(2, 6):
        game_state.add_player(f"player{i}", 1000)
    assert not game_state.add_player("player6", 1000)

def test_get_active_players(game_with_players):
    """测试获取活跃玩家"""
    assert len(game_with_players.get_active_players()) == 3
    
    # 测试玩家弃牌后
    game_with_players.apply_action("player1", PlayerAction.FOLD)
    active_players = game_with_players.get_active_players()
    assert len(active_players) == 2
    assert all(p.is_active for p in active_players)

def test_get_next_player(game_with_players):
    """测试获取下一个玩家"""
    # 测试正常顺序
    next_player = game_with_players.get_next_player(0)
    assert next_player.position == 1
    
    # 测试最后一个位置
    next_player = game_with_players.get_next_player(2)
    assert next_player.position == 0
    
    # 测试跳过弃牌玩家
    game_with_players.apply_action("player2", PlayerAction.FOLD)
    next_player = game_with_players.get_next_player(0)
    assert next_player.position == 2

def test_player_actions(game_with_players):
    """测试玩家动作"""
    # 测试弃牌
    assert game_with_players.apply_action("player1", PlayerAction.FOLD)
    assert not game_with_players.players["player1"].is_active
    
    # 测试过牌
    assert game_with_players.apply_action("player2", PlayerAction.CHECK)
    
    # 测试加注
    assert game_with_players.apply_action("player3", PlayerAction.RAISE, 50)
    assert game_with_players.players["player3"].current_bet == 50
    assert game_with_players.pot == 50
    
    # 测试跟注
    assert game_with_players.apply_action("player2", PlayerAction.CALL)
    assert game_with_players.players["player2"].current_bet == 50
    assert game_with_players.pot == 100
    
    # 测试全下
    assert game_with_players.apply_action("player2", PlayerAction.ALL_IN)
    assert game_with_players.players["player2"].chips == 0
    assert game_with_players.players["player2"].is_all_in

def test_invalid_actions(game_with_players):
    """测试无效动作"""
    # 测试无效玩家
    assert not game_with_players.apply_action("invalid_player", PlayerAction.CHECK)
    
    # 测试已弃牌玩家的动作
    game_with_players.apply_action("player1", PlayerAction.FOLD)
    assert not game_with_players.apply_action("player1", PlayerAction.CHECK)
    
    # 测试筹码不足
    game_with_players.players["player2"].chips = 10
    assert not game_with_players.apply_action("player2", PlayerAction.RAISE, 100)

def test_advance_stage(game_with_players):
    """测试游戏阶段推进"""
    assert game_with_players.stage == GameStage.WAITING
    
    # 测试正常推进
    assert game_with_players.advance_stage()
    assert game_with_players.stage == GameStage.PRE_FLOP
    
    assert game_with_players.advance_stage()
    assert game_with_players.stage == GameStage.FLOP
    
    assert game_with_players.advance_stage()
    assert game_with_players.stage == GameStage.TURN
    
    assert game_with_players.advance_stage()
    assert game_with_players.stage == GameStage.RIVER
    
    assert game_with_players.advance_stage()
    assert game_with_players.stage == GameStage.SHOWDOWN
    
    assert game_with_players.advance_stage()
    assert game_with_players.stage == GameStage.FINISHED
    
    # 测试无法继续推进
    assert not game_with_players.advance_stage()

def test_round_completion(game_with_players):
    """测试回合完成检查"""
    # 初始状态，没有玩家行动过
    assert not game_with_players.is_round_complete()
    
    # 第一个玩家加注
    game_with_players.apply_action("player1", PlayerAction.RAISE, 50)
    assert not game_with_players.is_round_complete()
    
    # 其他玩家跟注
    game_with_players.apply_action("player2", PlayerAction.CALL)
    assert not game_with_players.is_round_complete()
    
    game_with_players.apply_action("player3", PlayerAction.CALL)
    assert game_with_players.is_round_complete()
    
    # 重置回合
    game_with_players.reset_round()
    
    # 测试弃牌情况
    game_with_players.apply_action("player1", PlayerAction.RAISE, 50)
    game_with_players.apply_action("player2", PlayerAction.FOLD)
    game_with_players.apply_action("player3", PlayerAction.FOLD)
    assert game_with_players.is_round_complete()

def test_betting_rules(game_with_players):
    """测试下注规则"""
    # 设置初始最小加注为20
    game_with_players.min_raise = 20
    
    # 测试小于最小加注的情况
    assert not game_with_players.apply_action("player1", PlayerAction.RAISE, 10)
    
    # 测试有效加注
    assert game_with_players.apply_action("player1", PlayerAction.RAISE, 40)
    
    # 测试加注必须大于上一次加注
    assert not game_with_players.apply_action("player2", PlayerAction.RAISE, 30)
    assert game_with_players.apply_action("player2", PlayerAction.RAISE, 80)
    
    # 测试筹码不足的情况
    game_with_players.players["player3"].chips = 50
    assert not game_with_players.apply_action("player3", PlayerAction.RAISE, 100)
    assert game_with_players.apply_action("player3", PlayerAction.ALL_IN)

def test_chip_tracking(game_with_players):
    """测试筹码计算"""
    initial_chips = game_with_players.players["player1"].chips
    bet_amount = 100
    
    # 测试下注后的筹码变化
    game_with_players.apply_action("player1", PlayerAction.RAISE, bet_amount)
    assert game_with_players.players["player1"].chips == initial_chips - bet_amount
    assert game_with_players.players["player1"].total_bet == bet_amount
    assert game_with_players.pot == bet_amount

def test_player_state_initialization():
    """测试玩家状态初始化"""
    player = PlayerState(id="player1", chips=1000)
    assert player.id == "player1"
    assert player.chips == 1000
    assert player.cards == []
    assert player.current_bet == 0
    assert player.total_bet == 0
    assert player.has_acted is False
    assert player.is_active is True
    assert player.is_all_in is False

def test_game_state_initialization():
    """测试游戏状态初始化"""
    state = GameState()
    assert state.players == {}
    assert state.pot == 0
    assert state.side_pots == []
    assert state.active_players == []

def test_add_player():
    """测试添加玩家"""
    state = GameState()
    state.add_player("player1", 1000)
    
    assert "player1" in state.players
    assert state.players["player1"].chips == 1000
    assert len(state.active_players) == 1
    
    # 测试添加重复玩家
    with pytest.raises(ValueError):
        state.add_player("player1", 1000)

def test_remove_player():
    """测试移除玩家"""
    state = GameState()
    state.add_player("player1", 1000)
    state.remove_player("player1")
    
    assert "player1" not in state.players
    assert len(state.active_players) == 0
    
    # 测试移除不存在的玩家
    with pytest.raises(ValueError):
        state.remove_player("player2")

def test_reset_round():
    """测试回合重置"""
    state = GameState()
    state.add_player("player1", 1000)
    state.add_player("player2", 1000)
    
    # 设置一些状态
    state.bet("player1", 100)
    state.players["player1"].has_acted = True
    state.players["player1"].cards = ["A♠", "K♠"]
    state.players["player2"].is_all_in = True
    
    # 重置回合
    state.reset_round()
    
    # 验证状态已重置
    for player in state.players.values():
        assert player.current_bet == 0
        assert player.total_bet == 0
        assert player.has_acted is False
        assert player.is_active is True
        assert player.is_all_in is False
        assert player.cards == []
    assert state.pot == 0
    assert state.side_pots == []

def test_set_player_cards():
    """测试设置玩家手牌"""
    state = GameState()
    state.add_player("player1", 1000)
    
    cards = ["A♠", "K♠"]
    state.set_player_cards("player1", cards)
    assert state.players["player1"].cards == cards
    
    # 测试设置不存在玩家的手牌
    with pytest.raises(ValueError):
        state.set_player_cards("player2", cards)

def test_bet():
    """测试下注功能"""
    state = GameState()
    state.add_player("player1", 1000)
    
    # 正常下注
    state.bet("player1", 100)
    player = state.players["player1"]
    assert player.chips == 900
    assert player.current_bet == 100
    assert player.total_bet == 100
    assert state.pot == 100
    
    # 测试筹码不足
    with pytest.raises(ValueError):
        state.bet("player1", 1000)
    
    # 测试不存在的玩家下注
    with pytest.raises(ValueError):
        state.bet("player2", 100)

def test_call():
    """测试跟注功能"""
    state = GameState()
    state.add_player("player1", 1000)
    state.add_player("player2", 1000)
    
    # player1先下注
    state.bet("player1", 100)
    
    # player2跟注
    state.call("player2")
    assert state.players["player2"].current_bet == 100
    assert state.players["player2"].chips == 900
    assert state.pot == 200
    
    # 测试筹码不足时自动全下
    state.add_player("player3", 50)
    state.call("player3")
    assert state.players["player3"].is_all_in
    assert state.players["player3"].chips == 0
    assert state.players["player3"].current_bet == 50

def test_raise_bet():
    """测试加注功能"""
    state = GameState()
    state.add_player("player1", 1000)
    state.add_player("player2", 1000)
    
    # player1下注100
    state.bet("player1", 100)
    
    # player2加注到300
    state.raise_bet("player2", 300)
    assert state.players["player2"].current_bet == 300
    assert state.players["player2"].chips == 700
    assert state.pot == 400
    
    # 测试加注金额不足
    with pytest.raises(ValueError):
        state.raise_bet("player1", 200)  # 200小于当前最大注300

def test_all_in():
    """测试全下功能"""
    state = GameState()
    state.add_player("player1", 1000)
    
    state.all_in("player1")
    player = state.players["player1"]
    assert player.chips == 0
    assert player.current_bet == 1000
    assert player.total_bet == 1000
    assert player.is_all_in
    assert state.pot == 1000

def test_fold_player():
    """测试弃牌功能"""
    state = GameState()
    state.add_player("player1", 1000)
    state.set_player_cards("player1", ["A♠", "K♠"])
    
    state.fold_player("player1")
    player = state.players["player1"]
    assert not player.is_active
    assert player.cards == []
    assert len(state.active_players) == 0

def test_award_pot():
    """测试奖池分配"""
    state = GameState()
    state.add_player("player1", 1000)
    state.add_player("player2", 1000)
    
    # 两个玩家各下注100
    state.bet("player1", 100)
    state.bet("player2", 100)
    assert state.pot == 200
    
    # 将奖池分配给player1
    state.award_pot("player1")
    assert state.players["player1"].chips == 1100
    assert state.pot == 0

def test_create_side_pot():
    """测试边池创建"""
    state = GameState()
    state.add_player("player1", 1000)  # 正常玩家
    state.add_player("player2", 200)   # 全下玩家
    state.add_player("player3", 1000)  # 正常玩家
    
    # player2全下
    state.all_in("player2")  # 下注200
    
    # 其他玩家继续加注
    state.bet("player1", 500)
    state.bet("player3", 500)
    
    # 创建边池
    state.create_side_pot()
    
    # 验证边池金额
    assert len(state.side_pots) == 1
    assert state.side_pots[0] == 600  # (500-200)*2 = 600
    assert state.pot == 600  # 200*3 = 600

def test_active_players_property():
    """测试活跃玩家属性"""
    state = GameState()
    state.add_player("player1", 1000)
    state.add_player("player2", 1000)
    state.add_player("player3", 1000)
    
    assert len(state.active_players) == 3
    
    # player1弃牌
    state.fold_player("player1")
    assert len(state.active_players) == 2
    assert state.players["player1"] not in state.active_players
    
    # player2全下
    state.all_in("player2")
    assert len(state.active_players) == 2  # 全下玩家仍然算作活跃 