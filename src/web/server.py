from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime, timezone
import uuid
from fastapi.routing import APIRouter
import asyncio
import time

# 添加项目根目录到Python路径
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from src.utils.logger import get_logger
from src.utils.config import load_config
from src.engine.game import TexasHoldemGame, GamePhase, ActionType, PlayerAction
from src.engine.state import GameState, PlayerState
from src.agents.base import GameObservation

logger = get_logger(__name__)

# 获取当前文件的目录
current_dir = Path(__file__).parent.absolute()
web_dir = current_dir

# 加载配置
game_config = load_config('game')
llm_config = load_config('llm')

# 存储活动游戏
active_games: Dict[str, TexasHoldemGame] = {}

# 请求模型
class GameConfig(BaseModel):
    num_players: int = game_config['game']['max_players']
    initial_stack: int = game_config['game']['initial_chips']
    small_blind: int = game_config['game']['small_blind']

class WebSocketManager:
    def __init__(self):
        self.active_connections = {}  # game_id -> WebSocket
        self.ping_interval = 5  # 30秒发送一次心跳
        self.last_ping = {}  # game_id -> timestamp

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        self.active_connections[game_id] = websocket
        self.last_ping[game_id] = time.time()
        logger.info(f"WebSocket连接已建立: {game_id}")

    def disconnect(self, game_id: str):
        if game_id in self.active_connections:
            del self.active_connections[game_id]
        if game_id in self.last_ping:
            del self.last_ping[game_id]
        logger.info(f"WebSocket连接已断开: {game_id}")

    async def send_game_state(self, game_id: str, game_state: dict):
        if game_id in self.active_connections:
            try:
                await self.active_connections[game_id].send_json(game_state)
            except WebSocketDisconnect:
                self.disconnect(game_id)
                logger.error(f"发送游戏状态时连接断开: {game_id}")
            except Exception as e:
                logger.error(f"发送游戏状态时出错: {str(e)}")

    async def ping(self, game_id: str):
        if game_id in self.active_connections:
            try:
                await self.active_connections[game_id].send_text('ping')
                self.last_ping[game_id] = time.time()
            except Exception as e:
                logger.error(f"发送心跳包时出错: {str(e)}")
                self.disconnect(game_id)

manager = WebSocketManager()

# 创建应用
def create_app():
    app = FastAPI()
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
    
    # 静态文件服务
    app.mount("/css", StaticFiles(directory=str(web_dir / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(web_dir / "js")), name="js")
    
    # API路由
    api_router = APIRouter(prefix="/api")
    
    @api_router.post("/create_game")
    async def create_game(config: GameConfig):
        """创建新游戏"""
        try:
            game_id = str(uuid.uuid4())
            # 使用配置文件中的值
            num_players = game_config['game']['max_players']
            logger.info(f"正在创建游戏: {game_id}, 玩家数量: {num_players}")
            
            # 创建游戏实例
            game = TexasHoldemGame(
                game_id=game_id,
                players=[],  # 初始化时不传入玩家列表
                initial_stack=config.initial_stack,
                small_blind=config.small_blind
            )
            
            # 添加人类玩家
            game.state.add_player("player_0", config.initial_stack, 0)
            logger.info(f"添加人类玩家: player_0, 初始筹码: {config.initial_stack}")
            
            # 创建并添加AI玩家，使用配置文件中的玩家数量
            from src.agents.llm import LLMAgent
            
            # 创建AI玩家，数量由配置文件决定
            for i in range(1, num_players):
                agent_id = f"ai_{i}"
                try:
                    ai_player = LLMAgent(agent_id, llm_config)
                    game.add_player(ai_player)
                    # 保存AI玩家的模型信息
                    if "ai_players" in llm_config and agent_id in llm_config["ai_players"]:
                        game.state.players[agent_id].model_name = llm_config["ai_players"][agent_id]["model"]
                        logger.info(f"成功创建AI玩家: {agent_id}, 模型: {llm_config['ai_players'][agent_id]['model']}")
                    else:
                        logger.info(f"成功创建AI玩家: {agent_id}, 使用默认模型")
                except Exception as e:
                    logger.error(f"创建AI玩家失败: {e}")
                    raise ValueError(f"无法创建AI玩家: {e}")
            
            # 开始游戏
            game.start_game()
            logger.info(f"游戏 {game_id} 已开始")
            
            # 保存游戏实例
            active_games[game_id] = game
            
            # 获取初始游戏状态
            current_player = game.get_current_player()
            initial_state = {
                "phase": game.phase.name,
                "pot_size": game.state.pot,
                "community_cards": game.state.community_cards,
                "current_player": game.state.current_player or "player_0",
                "min_raise": max(game.state.get_max_bet() * 2, game.big_blind * 2),
                "max_raise": game.state.players["player_0"].chips if "player_0" in game.state.players else 0,
                "game_result": game.state.game_result,
                "players": []
            }
            
            logger.info(f"游戏初始状态: {initial_state}")
            
            return {
                "success": True,
                "game_id": game_id,
                "config": {
                    "num_players": config.num_players,
                    "initial_stack": config.initial_stack,
                    "small_blind": config.small_blind
                },
                "state": initial_state
            }
            
        except Exception as e:
            logger.error(f"创建游戏失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
                
    @api_router.get("/games/{game_id}")
    async def get_game_state(game_id: str):
        """获取游戏状态"""
        try:
            game = active_games.get(game_id)
            if not game:
                raise HTTPException(status_code=404, detail="游戏不存在")
            
            state = {
                "phase": game.state.phase,
                "pot_size": game.state.pot,
                "community_cards": game.state.community_cards,
                "current_player": game.state.current_player,
                "min_raise": game.state.get_min_bet(),
                "max_raise": game.state.get_max_bet(),
                "game_result": None,
                "players": []
            }
            
            # 转换玩家信息
            for player in game.state.players:
                player_info = {
                    "id": player.id,
                    "chips": player.chips,
                    "current_bet": player.current_bet,
                    "is_active": player.is_active,
                    "cards": list(player.cards) if player.id == "player_0" else [],  # 将元组转换为列表
                    "is_all_in": player.is_all_in,
                    "position": player.position,
                    "model_name": getattr(player, "model_name", None)  # 添加模型名称
                }
                state["players"].append(player_info)
            
            return state
            
        except Exception as e:
            logger.error(f"获取游戏状态失败: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
                
    @api_router.post("/games/{game_id}/action")
    async def handle_action(game_id: str, action: Dict[str, Any]):
        """处理玩家动作"""
        game = active_games.get(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
            
        try:
            # 检查游戏状态
            if game.phase == GamePhase.FINISHED:
                raise HTTPException(
                    status_code=400,
                    detail="Game is finished. Please start a new game."
                )
            
            logger.info(f"处理玩家动作: {action}")
            
            # 修复加注金额处理
            amount = action.get("amount", 0)
            if action["action_type"] == "RAISE":
                logger.info(f"收到加注请求，金额: {amount}")
                if amount <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Raise amount must be greater than 0"
                    )
                
                # 验证加注金额是否合法
                player = game.state.players.get(action["player_id"])
                if not player:
                    raise HTTPException(status_code=400, detail="Player not found")
                    
                if amount > player.chips:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Raise amount {amount} exceeds player chips {player.chips}"
                    )
                    
                if amount < game.state.min_raise:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Raise amount {amount} is less than minimum raise {game.state.min_raise}"
                    )
            
            # 创建动作对象
            player_action = PlayerAction(
                player_id=action["player_id"],
                action_type=ActionType[action["action_type"]],
                amount=amount,
                timestamp=datetime.now()
            )
            
            logger.info(f"创建的玩家动作: {player_action.model_dump()}")
            
            # 处理动作
            game.process_action(player_action)
            
            # 获取更新后的游戏状态
            updated_state = {
                "phase": game.phase.name,
                "pot_size": game.state.pot,
                "community_cards": game.state.community_cards,
                "current_player": game.state.current_player,
                "min_raise": game.state.min_raise,
                "max_raise": game.state.max_raise,
                "game_result": game.state.game_result,
                "players": [
                    {
                        "id": p.id,
                        "chips": p.chips,
                        "current_bet": p.current_bet,
                        "is_active": p.is_active,
                        "cards": p.cards if p.id == "player_0" or game.phase == GamePhase.FINISHED else [],
                        "is_all_in": p.is_all_in,
                        "position": p.position,
                        "model_name": getattr(p, "model_name", None),  # 添加模型名称
                        "last_action": player_action.action_type.name if p.id == player_action.player_id else None,
                        "last_amount": player_action.amount if p.id == player_action.player_id else None
                    }
                    for p in game.state.players.values()
                ]
            }
            
            logger.info(f"发送更新后的游戏状态: {updated_state}")
            
            # 直接返回更新后的状态，不使用WebSocket发送
            return updated_state
            
        except Exception as e:
            logger.error(f"处理动作失败: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
                
    @api_router.post("/games/{game_id}/new_game")
    async def start_new_game(game_id: str):
        """开始新的一局游戏"""
        try:
            game = active_games.get(game_id)
            if not game:
                raise HTTPException(status_code=404, detail="Game not found")
            
            if game.phase != GamePhase.FINISHED:
                raise HTTPException(status_code=400, detail="Game is not finished")
            
            # 开始新的一局
            game.start_new_game()
            
            # 返回新的游戏状态
            return {
                "success": True,
                "state": {
                    "phase": game.phase.name,
                    "pot_size": game.state.pot,
                    "community_cards": game.state.community_cards,
                    "current_player": game.state.current_player,
                    "min_raise": game.state.min_raise or game.big_blind,
                    "max_raise": game.state.max_raise,
                    "players": [
                        {
                            "id": p.id,
                            "chips": p.chips,
                            "current_bet": p.current_bet,
                            "is_active": p.is_active,
                            "cards": p.cards if p.id == "player_0" else [],
                            "is_all_in": p.is_all_in,
                            "position": p.position,
                            "model_name": getattr(p, "model_name", None),  # 添加模型名称
                            "last_action": None,
                            "last_amount": None
                        }
                        for p in game.state.players.values()
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"开始新游戏失败: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
                
    # 主页路由
    @app.get("/")
    async def root():
        """返回主页"""
        try:
            index_path = web_dir / "index.html"
            if not index_path.exists():
                logger.error(f"找不到主页文件: {index_path}")
                raise HTTPException(status_code=404, detail="index.html not found")
            logger.info(f"返回主页: {index_path}")
            return FileResponse(index_path)
        except Exception as e:
            logger.error(f"返回主页时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    # WebSocket路由
    @app.websocket("/ws/{game_id}")
    async def websocket_endpoint(websocket: WebSocket, game_id: str):
        try:
            await manager.connect(websocket, game_id)
            
            # 发送初始游戏状态
            game = active_games.get(game_id)
            if game:
                initial_state = {
                    "phase": game.phase.name,
                    "pot_size": game.state.pot,
                    "community_cards": game.state.community_cards,
                    "current_player": game.state.current_player,
                    "min_raise": max(game.state.get_max_bet() * 2, game.big_blind * 2),
                    "max_raise": game.state.players["player_0"].chips if "player_0" in game.state.players else 0,
                    "game_result": game.state.game_result,
                    "players": []
                }
                
                # 处理玩家数据
                for player_id, player_state in game.state.players.items():
                    player_data = {
                        "id": player_id,
                        "chips": player_state.chips,
                        "current_bet": player_state.current_bet,
                        "is_active": player_state.is_active,
                        "cards": player_state.cards if player_id == "player_0" else [],
                        "is_all_in": player_state.is_all_in,
                        "position": player_state.position,
                        "model_name": getattr(player_state, "model_name", None),  # 添加模型名称
                        "last_action": None,
                        "last_amount": None
                    }
                    initial_state["players"].append(player_data)
                
                logger.info(f"发送初始游戏状态: {initial_state}")
                await manager.send_game_state(game_id, initial_state)
                
                # 开始心跳检测
                ping_task = asyncio.create_task(periodic_ping(game_id))
                
                try:
                    while True:
                        # 如果当前玩家是AI，自动处理AI的行动
                        current_player = game.get_current_player()
                        if current_player and current_player.id.startswith("ai_"):
                            logger.info(f"当前AI玩家: {current_player.id}")
                            ai_player = game.ai_players.get(current_player.id)
                            if not ai_player:
                                logger.error(f"找不到AI玩家实例: {current_player.id}")
                                continue
                                
                            # 创建观察对象
                            observation = GameObservation(
                                game_id=game_id,
                                player_id=current_player.id,
                                phase=game.phase.name,
                                position=current_player.position,
                                timestamp=datetime.now(),
                                hand_cards=current_player.cards,
                                community_cards=game.state.community_cards,
                                pot_size=game.state.pot,
                                current_bet=game.state.get_max_bet(),
                                min_raise=game.state.min_raise or game.big_blind,
                                chips=current_player.chips,
                                is_all_in=current_player.is_all_in,
                                opponents=[
                                    {
                                        "player_id": p.id,
                                        "chips": p.chips,
                                        "current_bet": p.current_bet,
                                        "is_active": p.is_active,
                                        "is_all_in": p.is_all_in,
                                        "position": p.position
                                    }
                                    for p in game.state.get_active_players()
                                    if p.id != current_player.id
                                ],
                                round_actions=game.state.round_actions,
                                game_actions=game.state.game_actions
                            )
                            
                            try:
                                # AI观察并行动
                                logger.info(f"AI玩家 {current_player.id} 开始观察游戏状态")
                                ai_player.observe(observation)
                                ai_action = ai_player.act()
                                
                                logger.info(f"AI玩家 {current_player.id} 决定执行动作: {ai_action.action_type.name}, 金额: {ai_action.amount}")
                                game.process_action(ai_action)
                                
                                # 更新游戏状态
                                updated_state = {
                                    "phase": game.phase.name,
                                    "pot_size": game.state.pot,
                                    "community_cards": game.state.community_cards,
                                    "current_player": game.state.current_player,
                                    "min_raise": game.state.min_raise,
                                    "max_raise": game.state.max_raise,
                                    "game_result": game.state.game_result,
                                    "players": [
                                        {
                                            "id": p.id,
                                            "chips": p.chips,
                                            "current_bet": p.current_bet,
                                            "is_active": p.is_active,
                                            "cards": p.cards if p.id == "player_0" or game.phase == GamePhase.FINISHED else [],
                                            "is_all_in": p.is_all_in,
                                            "position": p.position,
                                            "model_name": getattr(p, "model_name", None),  # 添加模型名称
                                            "last_action": ai_action.action_type.name if p.id == ai_action.player_id else None,
                                            "last_amount": ai_action.amount if p.id == ai_action.player_id else None
                                        }
                                        for p in game.state.players.values()
                                    ]
                                }
                                
                                # 如果是AI玩家的动作，添加table_talk消息
                                if hasattr(ai_action, 'table_talk') and ai_action.table_talk:
                                    updated_state["table_talk"] = ai_action.table_talk
                                
                                # 发送更新后的状态
                                logger.info(f"发送AI行动后的游戏状态: {updated_state}")
                                await manager.send_game_state(game_id, updated_state)
                                
                                # 检查是否需要进入下一阶段
                                if game.is_round_complete():
                                    logger.info("回合结束，进入下一阶段")
                                    game.next_phase()
                                    # 更新并发送新的游戏状态
                                    updated_state = {
                                        "phase": game.phase.name,
                                        "pot_size": game.state.pot,
                                        "community_cards": game.state.community_cards,
                                        "current_player": game.state.current_player,
                                        "min_raise": game.state.min_raise,
                                        "max_raise": game.state.max_raise,
                                        "game_result": game.state.game_result,
                                        "players": [
                                            {
                                                "id": p.id,
                                                "chips": p.chips,
                                                "current_bet": p.current_bet,
                                                "is_active": p.is_active,
                                                "cards": p.cards if p.id == "player_0" or game.phase == GamePhase.FINISHED else [],
                                                "is_all_in": p.is_all_in,
                                                "position": p.position,
                                                "model_name": getattr(p, "model_name", None),  # 添加模型名称
                                                "last_action": ai_action.action_type.name if p.id == ai_action.player_id else None,
                                                "last_amount": ai_action.amount if p.id == ai_action.player_id else None
                                            }
                                            for p in game.state.players.values()
                                        ]
                                    }
                                    logger.info(f"游戏进入新阶段: {game.phase.name}")
                                    await manager.send_game_state(game_id, updated_state)
                                
                            except Exception as e:
                                logger.error(f"处理AI动作时出错: {str(e)}")
                                continue
                                
                        # 等待人类玩家的动作
                        try:
                            data = await websocket.receive_text()
                            if data == 'pong':
                                continue
                                
                            message = json.loads(data)
                            logger.info(f"收到玩家行动: {message}")
                            
                            # 处理玩家动作
                            try:
                                timestamp = datetime.now(timezone.utc)
                                action = PlayerAction(
                                    player_id=message["player_id"],
                                    action_type=ActionType[message["action"]],
                                    amount=message.get("amount", 0),
                                    timestamp=timestamp
                                )
                                
                                game.process_action(action)
                                
                                # 更新游戏状态
                                updated_state = {
                                    "phase": game.phase.name,
                                    "pot_size": game.state.pot,
                                    "community_cards": game.state.community_cards,
                                    "current_player": game.state.current_player,
                                    "min_raise": game.state.min_raise,
                                    "max_raise": game.state.max_raise,
                                    "game_result": game.state.game_result,
                                    "players": [
                                        {
                                            "id": p.id,
                                            "chips": p.chips,
                                            "current_bet": p.current_bet,
                                            "is_active": p.is_active,
                                            "cards": p.cards if p.id == "player_0" or game.phase == GamePhase.FINISHED else [],
                                            "is_all_in": p.is_all_in,
                                            "position": p.position,
                                            "model_name": getattr(p, "model_name", None),  # 添加模型名称
                                            "last_action": action.action_type.name if p.id == action.player_id else None,
                                            "last_amount": action.amount if p.id == action.player_id else None
                                        }
                                        for p in game.state.players.values()
                                    ]
                                }
                                
                                # 如果是AI玩家的动作，添加table_talk消息
                                if hasattr(action, 'table_talk') and action.table_talk:
                                    updated_state["table_talk"] = action.table_talk
                                
                                logger.info(f"发送更新后的游戏状态: {updated_state}")
                                await manager.send_game_state(game_id, updated_state)
                                
                                # 检查是否需要进入下一阶段
                                if game.is_round_complete():
                                    logger.info("回合结束，进入下一阶段")
                                    game.next_phase()
                                    # 更新并发送新的游戏状态
                                    updated_state = {
                                        "phase": game.phase.name,
                                        "pot_size": game.state.pot,
                                        "community_cards": game.state.community_cards,
                                        "current_player": game.state.current_player,
                                        "min_raise": game.state.min_raise,
                                        "max_raise": game.state.max_raise,
                                        "game_result": game.state.game_result,
                                        "players": [
                                            {
                                                "id": p.id,
                                                "chips": p.chips,
                                                "current_bet": p.current_bet,
                                                "is_active": p.is_active,
                                                "cards": p.cards if p.id == "player_0" or game.phase == GamePhase.FINISHED else [],
                                                "is_all_in": p.is_all_in,
                                                "position": p.position,
                                                "model_name": getattr(p, "model_name", None),  # 添加模型名称
                                                "last_action": action.action_type.name if p.id == action.player_id else None,
                                                "last_amount": action.amount if p.id == action.player_id else None
                                            }
                                            for p in game.state.players.values()
                                        ]
                                    }
                                    logger.info(f"游戏进入新阶段: {game.phase.name}")
                                    await manager.send_game_state(game_id, updated_state)
                                
                            except Exception as e:
                                logger.error(f"处理玩家动作时出错: {str(e)}")
                                await websocket.send_json({"error": str(e)})
                                
                        except json.JSONDecodeError:
                            logger.error("无效的JSON消息")
                            await websocket.send_json({"error": "无效的消息格式"})
                        except WebSocketDisconnect:
                            break
                        except Exception as e:
                            logger.error(f"处理WebSocket消息时出错: {str(e)}")
                            await websocket.send_json({"error": str(e)})
                            
                except WebSocketDisconnect:
                    manager.disconnect(game_id)
                    ping_task.cancel()
                
        except Exception as e:
            logger.error(f"WebSocket连接出错: {str(e)}")
            manager.disconnect(game_id)

    async def periodic_ping(game_id: str):
        """定期发送心跳包"""
        while True:
            try:
                await asyncio.sleep(5)  # 每30秒发送一次心跳
                await manager.send_game_state(game_id, "ping")
            except Exception as e:
                logger.error(f"发送心跳包时出错: {str(e)}")
                break

    # 包含API路由
    app.include_router(api_router)
    
    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["src/web"],
        ws_ping_interval=20,  # 添加 WebSocket ping 间隔
        ws_ping_timeout=5    # 添加 WebSocket ping 超时
    ) 