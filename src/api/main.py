"""
德州扑克游戏API服务。
提供RESTful API和WebSocket接口。
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
from pydantic import BaseModel

from src.engine.game import TexasHoldemGame as Game, ActionType, PlayerAction
from src.engine.state import PlayerState, GameState
from src.agents.llm import LLMAgent
from src.utils.logger import get_logger
from src.utils.config import load_config
from src.api.models import GameConfig, GameState, PlayerInfo, WebSocketMessage

# 获取日志记录器
logger = get_logger(__name__)

# 存储活动游戏和连接
active_games: Dict[str, Game] = {}
active_connections: Dict[str, List[WebSocket]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时的处理
    logger.info("API服务启动")
    yield
    # 关闭时的处理
    # 关闭所有WebSocket连接
    for connections in active_connections.values():
        for websocket in connections:
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"关闭WebSocket连接失败: {e}")
            
    # 清理游戏实例
    active_games.clear()
    active_connections.clear()
    logger.info("API服务关闭")

# 创建FastAPI应用
app = FastAPI(
    title="Texas Hold'em with LLM",
    description="基于大语言模型的多人德州扑克游戏系统",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定义JSON编码器
class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理特殊类型的序列化"""
    def default(self, obj):
        if isinstance(obj, ActionType):
            return obj.name
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, PlayerState):
            return {
                "id": obj.id,
                "chips": obj.chips,
                "is_active": obj.is_active,
                "current_bet": obj.current_bet,
                "cards": obj.cards if obj.id.startswith("player_") else []
            }
        return super().default(obj)

@app.get("/")
async def root():
    """API根路由"""
    return {
        "message": "Texas Hold'em with LLM API服务",
        "version": "1.0.0",
        "status": "running",
        "active_games": len(active_games)
    }

@app.post("/games", response_model=Dict[str, Any])
async def create_game(config: GameConfig):
    """创建新游戏"""
    try:
        # 生成游戏ID
        game_id = str(int(datetime.now().timestamp()))
        logger.info(f"创建新游戏: {game_id}, 配置: {config.model_dump()}")
        
        # 创建玩家列表
        players = []
        for i in range(config.num_players):
            if i == 0:
                # 第一个玩家是人类玩家
                players.append(f"player_{i}")
            else:
                # 其他玩家是AI
                players.append(f"ai_{i}")
        
        # 创建游戏实例
        game = Game(game_id, players, config.initial_stack)
        
        # 初始化玩家位置和AI玩家实例
        for i, player_id in enumerate(players):
            game.state.add_player(player_id, config.initial_stack, i)
            if player_id.startswith("ai_"):
                # 创建AI玩家实例
                ai_config = load_config("config/llm.yml")
                ai_player = LLMAgent(player_id, ai_config)
                game.ai_players[player_id] = ai_player
                logger.info(f"已创建AI玩家: {player_id}")
            
        active_games[game_id] = game
        
        # 初始化WebSocket连接列表
        active_connections[game_id] = []
        
        # 开始游戏
        game.start_game()
        logger.info(f"游戏 {game_id} 已开始")
        
        # 返回游戏状态
        current_player = game.get_current_player()
        game_state = GameState(
            game_id=game_id,
            phase=game.phase.name,
            pot_size=game.state.pot_size,
            community_cards=game.dealer.community_cards,
            current_player=current_player.id if current_player else None,
            players=[
                PlayerInfo(
                    player_id=player.id,
                    chips=player.chips,
                    is_active=player.is_active,
                    is_ai=player.id.startswith("ai_"),
                    current_bet=player.current_bet,
                    is_all_in=player.is_all_in,
                    hand_cards=player.cards if player.id == "player_0" else []
                )
                for player in game.state.get_active_players()
            ],
            current_bet=game.state.current_bet,
            min_raise=game.min_raise,
            max_raise=game.state.max_raise
        )
        
        return {
            "success": True,
            "game_id": game_id,
            "config": config.model_dump(),
            "state": game_state.model_dump()
        }
    except Exception as e:
        logger.error(f"创建游戏失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/games/{game_id}", response_model=Dict[str, Any])
async def get_game_state(game_id: str):
    """获取游戏状态"""
    try:
        if game_id not in active_games:
            logger.warning(f"游戏不存在: {game_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="游戏不存在"
            )
            
        game = active_games[game_id]
        current_player = game.get_current_player()
        
        # 构建玩家信息列表
        players = []
        for player in game.state.players.values():
            player_info = PlayerInfo(
                player_id=player.id,
                chips=player.chips,
                is_active=player.is_active,
                is_ai=player.id.startswith("ai_"),
                current_bet=player.current_bet,
                is_all_in=player.is_all_in,
                # 只向当前玩家展示手牌
                hand_cards=player.cards if current_player and player.id == current_player.id else []
            )
            players.append(player_info)
            
        # 构建游戏状态
        state = GameState(
            game_id=game_id,
            phase=game.phase.name,
            pot_size=game.state.pot_size,
            community_cards=game.dealer.community_cards,
            current_player=current_player.id if current_player else None,
            players=players,
            current_bet=game.state.current_bet,
            min_raise=game.min_raise,
            max_raise=game.state.max_raise
        )
        
        return {
            "success": True,
            "state": state.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取游戏状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/games/{game_id}/action", response_model=Dict[str, Any])
async def handle_action(game_id: str, action: PlayerAction):
    """处理玩家动作"""
    try:
        if game_id not in active_games:
            logger.warning(f"游戏不存在: {game_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="游戏不存在"
            )
            
        game = active_games[game_id]
        logger.info(f"处理玩家动作: {action.model_dump()}")
        
        # 验证是否轮到该玩家
        current_player = game.get_current_player()
        if not current_player or current_player.id != action.player_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不是该玩家的回合"
            )
            
        # 验证动作金额
        if action.action_type in [ActionType.RAISE, ActionType.ALL_IN]:
            max_bet = game.state.get_max_bet()
            min_raise = game.min_raise
            min_raise_to = max_bet + min_raise
            
            if action.amount < min_raise_to:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"加注金额必须至少是 {min_raise_to}"
                )
                
            if action.amount > current_player.chips:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"加注金额不能超过剩余筹码 {current_player.chips}"
                )
        
        # 创建游戏引擎动作对象
        game_action = PlayerAction(
            player_id=action.player_id,
            action_type=action.action_type,
            amount=action.amount,
            timestamp=action.timestamp or datetime.now()
        )
        
        # 处理动作
        try:
            game.process_action(game_action)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
            
        # 获取更新后的游戏状态
        current_player = game.get_current_player()
        updated_state = {
            "success": True,
            "action": action.model_dump(),
            "state": {
                "phase": game.phase.name,
                "pot_size": game.state.pot,
                "community_cards": game.state.community_cards,
                "current_player": game.state.current_player,
                "min_raise": game.state.min_raise,
                "max_raise": game.state.max_raise,
                "players": [
                    {
                        "id": p.id,
                        "chips": p.chips,
                        "current_bet": p.current_bet,
                        "is_active": p.is_active,
                        "is_all_in": p.is_all_in,
                        "cards": p.cards if p.id == action.player_id else [],
                        "position": p.position
                    }
                    for p in game.state.players.values()
                ]
            }
        }
        
        # 如果游戏结束，添加结果
        if game.state.game_result:
            updated_state["state"]["game_result"] = game.state.game_result
            logger.info(f"游戏结束，结果: {game.state.game_result}")
            
        logger.info(f"动作处理完成，更新后的状态: {updated_state}")
        return updated_state
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理动作失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    """WebSocket连接端点"""
    try:
        # 验证游戏和玩家
        if game_id not in active_games:
            logger.warning(f"WebSocket连接失败: 游戏不存在 {game_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        game = active_games[game_id]
        
        await websocket.accept()
        logger.info(f"WebSocket连接已建立: 游戏={game_id}")
        
        # 添加连接到活动连接列表
        if game_id not in active_connections:
            active_connections[game_id] = []
        active_connections[game_id].append(websocket)
        
        try:
            # 发送初始游戏状态
            current_player = game.get_current_player()
            state = GameState(
                game_id=game_id,
                phase=game.phase.name,
                pot_size=game.state.pot_size,
                community_cards=game.dealer.community_cards,
                current_player=current_player.id if current_player else None,
                players=[
                    PlayerInfo(
                        player_id=p.id,
                        chips=p.chips,
                        is_active=p.is_active,
                        is_ai=p.id.startswith("ai_"),
                        current_bet=p.current_bet,
                        is_all_in=p.is_all_in,
                        hand_cards=p.cards if p.id == "player_0" else []
                    )
                    for p in game.state.get_active_players()
                ],
                current_bet=game.state.current_bet,
                min_raise=game.min_raise,
                max_raise=game.state.max_raise
            )
            
            await websocket.send_json({
                "type": "game_state",
                "data": state.model_dump()
            })
            
            # 等待玩家动作
            while True:
                try:
                    # 接收消息
                    message = await websocket.receive_json()
                    logger.debug(f"收到WebSocket消息: {message}")
                    
                    # 验证消息格式
                    if not isinstance(message, dict) or "action" not in message:
                        await websocket.send_json({
                            "type": "error",
                            "data": "无效的消息格式"
                        })
                        continue
                        
                    action_type = message.get("action")
                    amount = message.get("amount", 0)
                    
                    # 验证动作类型
                    if action_type not in ["FOLD", "CHECK", "CALL", "RAISE", "ALL_IN"]:
                        await websocket.send_json({
                            "type": "error",
                            "data": f"无效的动作类型: {action_type}"
                        })
                        continue
                        
                    # 验证是否轮到玩家行动
                    current_player = game.get_current_player()
                    if not current_player or current_player.id != "player_0":
                        await websocket.send_json({
                            "type": "error",
                            "data": "现在不是您的回合"
                        })
                        continue
                        
                    # 验证加注金额
                    if action_type in ["RAISE", "ALL_IN"]:
                        max_bet = game.state.get_max_bet()
                        min_raise = game.min_raise
                        min_raise_to = max_bet + min_raise
                        
                        if amount < min_raise_to:
                            await websocket.send_json({
                                "type": "error",
                                "data": f"加注金额必须至少是 {min_raise_to}"
                            })
                            continue
                            
                        if amount > current_player.chips:
                            await websocket.send_json({
                                "type": "error",
                                "data": f"加注金额不能超过剩余筹码 {current_player.chips}"
                            })
                            continue
                    
                    # 创建动作对象
                    player_action = PlayerAction(
                        player_id="player_0",
                        action_type=ActionType[action_type],
                        amount=amount,
                        timestamp=datetime.now()
                    )
                    
                    # 处理动作
                    try:
                        game.process_action(player_action)
                    except ValueError as e:
                        await websocket.send_json({
                            "type": "error",
                            "data": str(e)
                        })
                        continue
                    
                    # 发送更新后的游戏状态
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
                                "is_all_in": p.is_all_in,
                                "cards": p.cards if p.id == "player_0" else [],
                                "position": p.position
                            }
                            for p in game.state.players.values()
                        ]
                    }
                    
                    logger.info(f"发送更新后的游戏状态: {updated_state}")
                    await websocket.send_json({
                        "type": "game_state",
                        "data": updated_state
                    })
                    
                    # 如果游戏结束，发送结果
                    if game.state.game_result:
                        logger.info(f"游戏结束，结果: {game.state.game_result}")
                        await websocket.send_json({
                            "type": "game_result",
                            "data": game.state.game_result
                        })
                    
                except WebSocketDisconnect:
                    logger.info(f"WebSocket连接已断开: {game_id}")
                    break
                except json.JSONDecodeError:
                    logger.warning("无效的JSON消息")
                    await websocket.send_json({
                        "type": "error",
                        "data": "无效的消息格式"
                    })
                except Exception as e:
                    logger.error(f"处理WebSocket消息失败: {str(e)}")
                    await websocket.send_json({
                        "type": "error",
                        "data": str(e)
                    })
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket连接已断开: {game_id}")
        finally:
            # 移除连接
            if game_id in active_connections and websocket in active_connections[game_id]:
                active_connections[game_id].remove(websocket)
                logger.info(f"移除WebSocket连接: 游戏={game_id}")
                
    except Exception as e:
        logger.error(f"WebSocket处理失败: {str(e)}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass

async def broadcast_game_state(game_id: str, state: GameState):
    """广播游戏状态更新"""
    if game_id not in active_games:
        return
        
    try:
        message = WebSocketMessage(
            type="game_state",
            data=state.model_dump()
        ).model_dump()
        
        # 向所有连接的客户端发送更新
        disconnected_clients = []
        for websocket in active_connections.get(game_id, []):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送状态更新失败: {e}")
                disconnected_clients.append(websocket)
                
        # 清理断开的连接
        for websocket in disconnected_clients:
            if websocket in active_connections[game_id]:
                active_connections[game_id].remove(websocket)
                logger.info(f"移除断开的WebSocket连接: 游戏={game_id}")
                    
    except Exception as e:
        logger.error(f"广播游戏状态失败: {e}") 