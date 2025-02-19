import unittest
from src.engine.game import TexasHoldemGame, GamePhase, ActionType, PlayerAction
from datetime import datetime

class TestGameFlow(unittest.TestCase):
    """测试游戏流程"""

    def setUp(self):
        """测试前的准备工作"""
        # 创建一个新的游戏实例
        self.game_id = "test_game"
        self.game = TexasHoldemGame(
            game_id=self.game_id,
            players=[],  # 初始化时不传入玩家列表
            initial_stack=1000,
            small_blind=10
        )
        
        # 添加三个玩家
        class MockPlayer:
            def __init__(self, agent_id):
                self.agent_id = agent_id
                self.id = agent_id
                self.cards = []
                self.chips = 1000
                self.total_bet = 0
                self.is_all_in = False
                self.position = 0
                self.has_acted = False
                self.is_active = True

        # 添加玩家
        self.game.add_player(MockPlayer("player_0"))  # 人类玩家
        self.game.add_player(MockPlayer("player_1"))  # AI玩家1
        self.game.add_player(MockPlayer("player_2"))  # AI玩家2

    def test_game_initialization(self):
        """测试游戏初始化"""
        # 验证初始状态
        self.assertEqual(self.game.phase, GamePhase.WAITING)
        self.assertEqual(len(self.game.state.players), 3)
        self.assertEqual(self.game.small_blind, 10)
        self.assertEqual(self.game.big_blind, 20)

    def test_game_start(self):
        """测试游戏开始流程"""
        # 开始游戏
        self.game.start_game()
        
        # 验证游戏阶段
        self.assertEqual(self.game.phase, GamePhase.PRE_FLOP)
        
        # 验证盲注是否正确收取
        players = list(self.game.state.players.values())
        self.assertEqual(players[1].current_bet, 10)  # 小盲注
        self.assertEqual(players[2].current_bet, 20)  # 大盲注

    def test_preflop_actions(self):
        """测试翻牌前的行动"""
        self.game.start_game()
        
        # player_0 跟注
        action = PlayerAction(
            player_id="player_0",
            action_type=ActionType.CALL,
            amount=20,
            timestamp=datetime.now()
        )
        self.game.process_action(action)
        
        # 验证玩家筹码和下注
        player = self.game.state.players["player_0"]
        self.assertEqual(player.current_bet, 20)
        self.assertEqual(player.chips, 980)

    def test_round_completion(self):
        """测试回合完成和阶段转换"""
        self.game.start_game()
        
        # 所有玩家都跟注
        actions = [
            ("player_0", ActionType.CALL),
            ("player_1", ActionType.CALL),
            ("player_2", ActionType.CHECK)
        ]
        
        for player_id, action_type in actions:
            action = PlayerAction(
                player_id=player_id,
                action_type=action_type,
                timestamp=datetime.now()
            )
            self.game.process_action(action)
        
        # 验证是否进入翻牌阶段
        self.assertEqual(self.game.phase, GamePhase.FLOP)

    def test_fold_action(self):
        """测试弃牌动作"""
        self.game.start_game()
        
        # player_0 弃牌
        action = PlayerAction(
            player_id="player_0",
            action_type=ActionType.FOLD,
            timestamp=datetime.now()
        )
        self.game.process_action(action)
        
        # 验证玩家状态
        player = self.game.state.players["player_0"]
        self.assertFalse(player.is_active)
        
        # 验证活跃玩家数量
        active_players = self.game.state.get_active_players()
        self.assertEqual(len(active_players), 2)

    def test_raise_action(self):
        """测试加注动作"""
        self.game.start_game()
        
        # player_0 加注到 40
        action = PlayerAction(
            player_id="player_0",
            action_type=ActionType.RAISE,
            amount=40,
            timestamp=datetime.now()
        )
        self.game.process_action(action)
        
        # 验证玩家筹码和下注
        player = self.game.state.players["player_0"]
        self.assertEqual(player.current_bet, 40)
        self.assertEqual(player.chips, 960)
        
        # 验证其他玩家的行动状态被重置
        for player in self.game.state.get_active_players():
            if player.id != "player_0":
                self.assertFalse(player.has_acted)

    def test_all_in_action(self):
        """测试全下动作"""
        self.game.start_game()
        
        # player_0 全下
        action = PlayerAction(
            player_id="player_0",
            action_type=ActionType.ALL_IN,
            timestamp=datetime.now()
        )
        self.game.process_action(action)
        
        # 验证玩家状态
        player = self.game.state.players["player_0"]
        self.assertTrue(player.is_all_in)
        self.assertEqual(player.chips, 0)
        
        # 验证其他玩家的行动状态被重置
        for player in self.game.state.get_active_players():
            if player.id != "player_0":
                self.assertFalse(player.has_acted)

if __name__ == '__main__':
    unittest.main() 