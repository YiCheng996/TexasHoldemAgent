"""
游戏主逻辑模块测试。
测试德州扑克游戏的核心流程控制。
"""

import pytest
from datetime import datetime
from src.engine.game import TexasHoldemGame, GamePhase, ActionType, PlayerAction

@pytest.fixture
def game():
    """创建基本的游戏实例"""
    players = ["player1", "player2", "player3"]
    return TexasHoldemGame("test_game", players, initial_chips=1000)

def test_game_initialization(game):
    """测试游戏初始化"""
    assert game.game_id == "test_game"
    assert len(game.state.players) == 3
    assert game.phase == GamePhase.WAITING
    assert game.current_player_idx == 0
    assert game.button_idx == 0
    assert game.min_raise == 0
    
    # 验证玩家初始状态
    for player in game.state.players.values():
        assert player.chips == 1000
        assert player.cards == []
        assert player.current_bet == 0
        assert player.is_active

def test_start_game(game):
    """测试游戏开始"""
    game.start_game()
    
    assert game.phase == GamePhase.PRE_FLOP
    assert len(game.dealer.deck) == 52 - (2 * 3)  # 发了6张手牌
    
    # 验证盲注
    sb_pos = (game.button_idx + 1) % 3
    bb_pos = (game.button_idx + 2) % 3
    
    sb_player = game.state.active_players[sb_pos]
    bb_player = game.state.active_players[bb_pos]
    
    assert sb_player.current_bet == 1
    assert bb_player.current_bet == 2
    assert game.state.pot == 3
    assert game.min_raise == 2

def test_post_blinds(game):
    """测试收取盲注"""
    game.phase = GamePhase.WAITING
    game.post_blinds()
    
    sb_pos = (game.button_idx + 1) % 3
    bb_pos = (game.button_idx + 2) % 3
    
    sb_player = game.state.active_players[sb_pos]
    bb_player = game.state.active_players[bb_pos]
    
    assert sb_player.current_bet == 1
    assert sb_player.chips == 999
    assert bb_player.current_bet == 2
    assert bb_player.chips == 998
    assert game.state.pot == 3
    assert game.min_raise == 2
    assert game.current_player_idx == (bb_pos + 1) % 3

def test_get_current_player(game):
    """测试获取当前玩家"""
    game.start_game()
    current_player = game.get_current_player()
    assert current_player is not None
    assert current_player.id == game.state.active_players[game.current_player_idx].id

def test_is_round_complete(game):
    """测试回合完成检查"""
    game.start_game()
    
    # 初始状态，回合未完成
    assert not game.is_round_complete()
    
    # 所有玩家行动且下注相等
    for player in game.state.active_players:
        player.has_acted = True
        player.current_bet = 2
    
    assert game.is_round_complete()

def test_next_phase(game):
    """测试阶段推进"""
    game.start_game()  # PRE_FLOP
    
    game.next_phase()  # FLOP
    assert game.phase == GamePhase.FLOP
    assert len(game.dealer.community_cards) == 3
    
    game.next_phase()  # TURN
    assert game.phase == GamePhase.TURN
    assert len(game.dealer.community_cards) == 4
    
    game.next_phase()  # RIVER
    assert game.phase == GamePhase.RIVER
    assert len(game.dealer.community_cards) == 5
    
    game.next_phase()  # SHOWDOWN
    assert game.phase == GamePhase.SHOWDOWN

def test_process_action(game):
    """测试动作处理"""
    game.start_game()
    current_player = game.get_current_player()
    
    # 测试跟注
    action = PlayerAction(
        player_id=current_player.id,
        action_type=ActionType.CALL,
        timestamp=datetime.now()
    )
    game.process_action(action)
    
    assert current_player.has_acted
    assert current_player.current_bet == 2
    assert game.state.pot == 5  # 3(盲注) + 2(跟注)
    
    # 测试加注
    next_player = game.get_current_player()
    action = PlayerAction(
        player_id=next_player.id,
        action_type=ActionType.RAISE,
        amount=6,
        timestamp=datetime.now()
    )
    game.process_action(action)
    
    assert next_player.has_acted
    assert next_player.current_bet == 6
    assert game.state.pot == 9  # 5 + 4(加注)
    assert game.min_raise == 6

def test_validate_action(game):
    """测试动作验证"""
    game.start_game()
    current_player = game.get_current_player()
    
    # 测试无效的加注
    action = PlayerAction(
        player_id=current_player.id,
        action_type=ActionType.RAISE,
        amount=1  # 小于最小加注
    )
    with pytest.raises(ValueError):
        game.process_action(action)
    
    # 测试筹码不足
    action = PlayerAction(
        player_id=current_player.id,
        action_type=ActionType.RAISE,
        amount=2000  # 超过玩家筹码
    )
    with pytest.raises(ValueError):
        game.process_action(action)

def test_next_player(game):
    """测试切换玩家"""
    game.start_game()
    initial_idx = game.current_player_idx
    
    # 正常切换
    game._next_player()
    assert game.current_player_idx == (initial_idx + 1) % 3
    
    # 跳过已行动的玩家
    game.state.active_players[game.current_player_idx].has_acted = True
    game._next_player()
    assert game.current_player_idx == (initial_idx + 2) % 3

def test_end_game_one_player(game):
    """测试一个玩家获胜的情况"""
    game.start_game()
    
    # 让两个玩家弃牌
    for _ in range(2):
        current_player = game.get_current_player()
        action = PlayerAction(
            player_id=current_player.id,
            action_type=ActionType.FOLD
        )
        game.process_action(action)
    
    assert game.phase == GamePhase.FINISHED
    assert len(game.state.active_players) == 1
    winner = game.state.active_players[0]
    assert winner.chips == 1003  # 初始1000 + 盲注3

def test_end_game_showdown(game):
    """测试摊牌阶段"""
    game.start_game()
    
    # 设置玩家手牌
    game.state.set_player_cards("player1", ["A♠", "K♠"])
    game.state.set_player_cards("player2", ["Q♥", "Q♦"])
    game.state.set_player_cards("player3", ["J♣", "J♠"])
    
    # 设置公共牌
    game.dealer.community_cards = ["A♥", "K♥", "2♣", "3♦", "4♠"]
    
    # 所有玩家跟注
    for player in game.state.active_players:
        action = PlayerAction(
            player_id=player.id,
            action_type=ActionType.CALL
        )
        game.process_action(action)
    
    # 进入摊牌阶段
    game.phase = GamePhase.SHOWDOWN
    game._end_game()
    
    assert game.phase == GamePhase.FINISHED
    # player1应该赢（一对A，K高牌）
    assert game.state.players["player1"].chips > 1000

def test_invalid_actions(game):
    """测试无效动作"""
    game.start_game()
    
    # 测试非当前玩家的动作
    invalid_player = None
    for player in game.state.active_players:
        if player.id != game.get_current_player().id:
            invalid_player = player
            break
    
    action = PlayerAction(
        player_id=invalid_player.id,
        action_type=ActionType.CALL
    )
    with pytest.raises(ValueError):
        game.process_action(action)
    
    # 测试在错误阶段的动作
    game.phase = GamePhase.FINISHED
    current_player = game.get_current_player()
    action = PlayerAction(
        player_id=current_player.id,
        action_type=ActionType.CALL
    )
    with pytest.raises(ValueError):
        game.process_action(action)

def test_game_flow(game):
    """测试完整游戏流程"""
    # 开始游戏
    game.start_game()
    assert game.phase == GamePhase.PRE_FLOP
    
    # PRE_FLOP阶段
    for _ in range(3):
        current_player = game.get_current_player()
        action = PlayerAction(
            player_id=current_player.id,
            action_type=ActionType.CALL
        )
        game.process_action(action)
    
    assert game.phase == GamePhase.FLOP
    assert len(game.dealer.community_cards) == 3
    
    # FLOP阶段
    for _ in range(3):
        current_player = game.get_current_player()
        action = PlayerAction(
            player_id=current_player.id,
            action_type=ActionType.CHECK
        )
        game.process_action(action)
    
    assert game.phase == GamePhase.TURN
    assert len(game.dealer.community_cards) == 4
    
    # TURN阶段
    for _ in range(3):
        current_player = game.get_current_player()
        action = PlayerAction(
            player_id=current_player.id,
            action_type=ActionType.CHECK
        )
        game.process_action(action)
    
    assert game.phase == GamePhase.RIVER
    assert len(game.dealer.community_cards) == 5
    
    # RIVER阶段
    for _ in range(3):
        current_player = game.get_current_player()
        action = PlayerAction(
            player_id=current_player.id,
            action_type=ActionType.CHECK
        )
        game.process_action(action)
    
    assert game.phase == GamePhase.SHOWDOWN
    
    # 游戏应该结束
    assert game.phase == GamePhase.FINISHED 