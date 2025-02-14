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
    # 初始状态
    assert game_with_players.is_round_complete()
    
    # 有人加注后未完成
    game_with_players.apply_action("player1", PlayerAction.RAISE, 50)
    assert not game_with_players.is_round_complete()
    
    # 其他玩家跟注后完成
    game_with_players.apply_action("player2", PlayerAction.CALL)
    game_with_players.apply_action("player3", PlayerAction.CALL)
    assert game_with_players.is_round_complete()
    
    # 只剩一个玩家时完成
    game_with_players.apply_action("player2", PlayerAction.FOLD)
    game_with_players.apply_action("player3", PlayerAction.FOLD)
    assert game_with_players.is_round_complete()

def test_betting_rules(game_with_players):
    """测试下注规则"""
    # 测试最小加注
    assert not game_with_players.apply_action("player1", PlayerAction.RAISE, 10)
    assert game_with_players.apply_action("player1", PlayerAction.RAISE, 20)
    
    # 测试加注必须大于上一次加注
    game_with_players.apply_action("player2", PlayerAction.RAISE, 40)
    assert not game_with_players.apply_action("player3", PlayerAction.RAISE, 30)
    assert game_with_players.apply_action("player3", PlayerAction.RAISE, 60)

def test_chip_tracking(game_with_players):
    """测试筹码计算"""
    initial_chips = game_with_players.players["player1"].chips
    bet_amount = 100
    
    # 测试下注后的筹码变化
    game_with_players.apply_action("player1", PlayerAction.RAISE, bet_amount)
    assert game_with_players.players["player1"].chips == initial_chips - bet_amount
    assert game_with_players.players["player1"].total_bet == bet_amount
    assert game_with_players.pot == bet_amount 