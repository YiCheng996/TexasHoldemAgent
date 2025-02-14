"""
数据模型定义模块。
使用SQLAlchemy ORM定义数据表结构。
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Game(Base):
    """游戏表"""
    __tablename__ = 'games'
    
    game_id = Column(String, primary_key=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    players = Column(JSON)  # 玩家列表，JSON数组
    initial_stakes = Column(Integer)
    winner = Column(String)
    final_pot = Column(Integer)

class Round(Base):
    """回合表"""
    __tablename__ = 'rounds'
    
    round_id = Column(String, primary_key=True)
    game_id = Column(String, ForeignKey('games.game_id'))
    round_type = Column(String)  # PRE_FLOP, FLOP, TURN, RIVER
    community_cards = Column(JSON)  # 公共牌，JSON数组
    pot_size = Column(Integer)

class Action(Base):
    """动作表"""
    __tablename__ = 'actions'
    
    action_id = Column(String, primary_key=True)
    round_id = Column(String, ForeignKey('rounds.round_id'))
    player_id = Column(String)
    action_type = Column(String)
    amount = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    hand_cards = Column(JSON)  # 玩家手牌，JSON数组
    reasoning = Column(JSON)  # AI决策理由，JSON对象

class PlayerStats(Base):
    """玩家统计表"""
    __tablename__ = 'player_stats'
    
    player_id = Column(String, primary_key=True)
    games_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    total_profit = Column(Integer, default=0)
    play_style = Column(JSON)  # 玩家风格分析，JSON对象
    last_updated = Column(DateTime, default=datetime.utcnow) 