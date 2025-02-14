"""
数据库管理模块测试
"""

import os
import pytest
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from src.db.manager import DatabaseManager, init_database, get_db
from src.db.models import Game, Round, Action, PlayerStats

@pytest.fixture(scope="session")
def test_db_path():
    """测试数据库路径"""
    return "data/test_poker.db"

@pytest.fixture(scope="session")
def db_manager(test_db_path):
    """创建测试用的数据库管理器"""
    # 修改配置中的数据库路径
    manager = DatabaseManager()
    manager.config['url'] = f"sqlite:///{test_db_path}"
    manager.engine = manager._create_engine()
    manager.SessionLocal = manager.engine.sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=manager.engine
    )
    
    # 创建数据库表
    manager.create_database()
    
    yield manager
    
    # 清理测试数据库
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

@pytest.fixture
def db_session(db_manager):
    """获取测试用的数据库会话"""
    with db_manager.get_session() as session:
        yield session

def test_database_creation(test_db_path, db_manager):
    """测试数据库创建"""
    assert os.path.exists(test_db_path)

def test_game_crud(db_session: Session):
    """测试游戏表的CRUD操作"""
    # 创建测试数据
    game = Game(
        game_id="test_game_1",
        players=["player1", "player2"],
        initial_stakes=1000,
        final_pot=2000
    )
    
    # 创建
    db_session.add(game)
    db_session.commit()
    
    # 读取
    saved_game = db_session.query(Game).filter_by(game_id="test_game_1").first()
    assert saved_game is not None
    assert saved_game.initial_stakes == 1000
    
    # 更新
    saved_game.winner = "player1"
    db_session.commit()
    
    updated_game = db_session.query(Game).filter_by(game_id="test_game_1").first()
    assert updated_game.winner == "player1"
    
    # 删除
    db_session.delete(saved_game)
    db_session.commit()
    
    deleted_game = db_session.query(Game).filter_by(game_id="test_game_1").first()
    assert deleted_game is None

def test_round_creation(db_session: Session):
    """测试回合创建"""
    # 创建游戏
    game = Game(
        game_id="test_game_2",
        players=["player1", "player2"],
        initial_stakes=1000
    )
    db_session.add(game)
    
    # 创建回合
    round = Round(
        round_id="test_round_1",
        game_id=game.game_id,
        round_type="PRE_FLOP",
        community_cards=[],
        pot_size=100
    )
    db_session.add(round)
    db_session.commit()
    
    # 验证
    saved_round = db_session.query(Round).filter_by(round_id="test_round_1").first()
    assert saved_round is not None
    assert saved_round.game_id == "test_game_2"

def test_action_creation(db_session: Session):
    """测试动作创建"""
    # 创建动作
    action = Action(
        action_id="test_action_1",
        round_id="test_round_1",
        player_id="player1",
        action_type="RAISE",
        amount=100,
        hand_cards=["AS", "KS"],
        reasoning={"confidence": 0.8}
    )
    db_session.add(action)
    db_session.commit()
    
    # 验证
    saved_action = db_session.query(Action).filter_by(action_id="test_action_1").first()
    assert saved_action is not None
    assert saved_action.amount == 100
    assert saved_action.hand_cards == ["AS", "KS"]

def test_player_stats(db_session: Session):
    """测试玩家统计"""
    # 创建玩家统计
    stats = PlayerStats(
        player_id="player1",
        games_played=10,
        wins=3,
        total_profit=500,
        play_style={"aggression": 0.7}
    )
    db_session.add(stats)
    db_session.commit()
    
    # 验证
    saved_stats = db_session.query(PlayerStats).filter_by(player_id="player1").first()
    assert saved_stats is not None
    assert saved_stats.games_played == 10
    assert saved_stats.wins == 3
    assert saved_stats.play_style["aggression"] == 0.7 