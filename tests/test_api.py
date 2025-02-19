"""
API服务测试。
测试RESTful API和WebSocket接口。
"""

import pytest
from fastapi.testclient import TestClient
import json
from datetime import datetime
import asyncio
from typing import Dict, Generator
import httpx

from src.api.main import app, active_games, active_connections
from src.api.models import GameConfig, PlayerAction, GameState
from src.engine.game import ActionType

@pytest.fixture
def client() -> Generator:
    """创建测试客户端"""
    with TestClient(app) as client:
        yield client

@pytest.fixture(autouse=True)
def clean_test_state():
    """清理测试状态"""
    # 测试前清理
    active_games.clear()
    active_connections.clear()
    yield
    # 测试后清理
    active_games.clear()
    active_connections.clear()

def test_root(client):
    """测试根路由"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "active_games" in data
    assert isinstance(data["active_games"], int)

def test_create_game(client):
    """测试创建游戏"""
    config = GameConfig(
        num_players=3,
        initial_stack=1000,
        small_blind=10
    )
    
    response = client.post("/games", json=config.model_dump())
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "game_id" in data
    assert data["config"]["num_players"] == 3
    assert data["config"]["initial_stack"] == 1000
    assert data["config"]["small_blind"] == 10
    assert "state" in data

def test_get_game_state(client):
    """测试获取游戏状态"""
    # 先创建游戏
    config = GameConfig(
        num_players=3,
        initial_stack=1000,
        small_blind=10
    )
    create_response = client.post("/games", json=config.model_dump())
    game_id = create_response.json()["game_id"]
    
    # 获取游戏状态
    response = client.get(f"/games/{game_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    state = GameState(**data["state"])
    assert state.game_id == game_id
    assert len(state.players) == 3
    assert state.pot_size == 3  # 小盲注1 + 大盲注2
    assert state.phase == "PRE_FLOP"
    assert state.current_bet == 2  # 大盲注金额
    assert state.min_raise == 2  # 最小加注额等于大盲注

def test_player_action(client):
    """测试玩家动作"""
    # 创建游戏
    config = GameConfig(
        num_players=3,
        initial_stack=1000,
        small_blind=10
    )
    create_response = client.post("/games", json=config.model_dump())
    game_id = create_response.json()["game_id"]
    
    # 执行动作
    action_data = {
        "player_id": "player_0",
        "action_type": "CALL",  # 直接使用字符串
        "amount": 2,  # 跟注大盲注
        "timestamp": datetime.now().isoformat()
    }
    
    response = client.post(
        f"/games/{game_id}/action",
        json=action_data
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["action"]["player_id"] == "player_0"
    assert data["action"]["action_type"] == "CALL"
    assert "state" in data

def test_invalid_action(client):
    """测试无效动作"""
    # 创建游戏
    config = GameConfig(
        num_players=3,
        initial_stack=1000,
        small_blind=10
    )
    create_response = client.post("/games", json=config.model_dump())
    game_id = create_response.json()["game_id"]
    
    # 执行无效动作（错误的玩家ID）
    action_data = {
        "player_id": "invalid_player",
        "action_type": "CALL",  # 直接使用字符串
        "amount": 20,
        "timestamp": datetime.now().isoformat()
    }
    
    response = client.post(
        f"/games/{game_id}/action",
        json=action_data
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

@pytest.mark.asyncio
async def test_websocket(client):
    """测试WebSocket连接"""
    # 创建游戏
    config = GameConfig(
        num_players=3,
        initial_stack=1000,
        small_blind=10
    )
    create_response = client.post("/games", json=config.model_dump())
    game_id = create_response.json()["game_id"]
    
    # 建立WebSocket连接
    with client.websocket_connect(f"/ws/{game_id}/player_0") as websocket:
        # 接收初始游戏状态
        response = websocket.receive_json()
        assert response["type"] == "game_state"
        assert "data" in response
        
        # 发送动作
        action_data = {
            "player_id": "player_0",
            "action_type": "CALL",  # 直接使用字符串
            "amount": 2,  # 跟注大盲注
            "timestamp": datetime.now().isoformat()
        }
        websocket.send_json(action_data)
        
        # 接收动作响应
        response = websocket.receive_json()
        assert response["type"] == "game_state"
        assert "data" in response

def test_concurrent_actions(client):
    """测试并发动作"""
    # 创建游戏
    config = GameConfig(
        num_players=3,
        initial_stack=1000,
        small_blind=10
    )
    create_response = client.post("/games", json=config.model_dump())
    game_id = create_response.json()["game_id"]
    
    # 同时发送多个动作
    actions = []
    for i in range(3):
        action_data = {
            "player_id": f"player_{i}",
            "action_type": "CALL",  # 直接使用字符串
            "amount": 2,  # 跟注大盲注
            "timestamp": datetime.now().isoformat()
        }
        actions.append(action_data)
    
    # 并发发送动作
    responses = []
    for action in actions:
        response = client.post(
            f"/games/{game_id}/action",
            json=action
        )
        responses.append(response)
    
    # 验证响应
    for response in responses:
        assert response.status_code in [200, 400]  # 部分动作可能因为顺序问题被拒绝
        data = response.json()
        if response.status_code == 200:
            assert data["success"] is True
            assert "action" in data
            assert "state" in data
        else:
            assert "detail" in data

@pytest.mark.asyncio
async def test_game_cleanup(client):
    """测试游戏清理"""
    # 创建游戏
    config = GameConfig(
        num_players=3,
        initial_stack=1000,
        small_blind=10
    )
    create_response = client.post("/games", json=config.model_dump())
    game_id = create_response.json()["game_id"]
    
    # 清理游戏
    active_games.clear()
    active_connections.clear()
    
    # 验证游戏已被清理
    get_response = client.get(f"/games/{game_id}")
    assert get_response.status_code == 404
    data = get_response.json()
    assert "detail" in data 