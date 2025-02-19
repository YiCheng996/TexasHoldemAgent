"""
WebSocket连接管理器。
处理WebSocket连接的创建、维护和清理。
"""

from fastapi import WebSocket, status
from typing import Dict, Set, Optional
import json
import asyncio
from datetime import datetime

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        """初始化连接管理器"""
        # 存储所有活动连接
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 存储每个游戏的玩家连接
        self.game_connections: Dict[str, Set[str]] = {}
        # 存储ping任务
        self.ping_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("WebSocket连接管理器已初始化")
    
    async def connect(self, websocket: WebSocket, game_id: str, player_id: str) -> None:
        """
        处理新的WebSocket连接
        
        Args:
            websocket: WebSocket连接
            game_id: 游戏ID
            player_id: 玩家ID
        """
        try:
            # 接受连接
            await websocket.accept()
            logger.info(f"接受WebSocket连接: 游戏={game_id}, 玩家={player_id}")
            
            # 初始化游戏连接字典
            if game_id not in self.active_connections:
                self.active_connections[game_id] = {}
                self.game_connections[game_id] = set()
                
            # 如果玩家已有连接，关闭旧连接
            if player_id in self.active_connections[game_id]:
                old_websocket = self.active_connections[game_id][player_id]
                try:
                    await old_websocket.close(code=status.WS_1012_SERVICE_RESTART)
                    logger.info(f"关闭旧连接: 游戏={game_id}, 玩家={player_id}")
                except Exception as e:
                    logger.error(f"关闭旧连接失败: {e}")
                
            # 存储新连接
            self.active_connections[game_id][player_id] = websocket
            self.game_connections[game_id].add(player_id)
            
            # 启动ping任务
            if game_id not in self.ping_tasks:
                self.ping_tasks[game_id] = asyncio.create_task(
                    self.start_ping(game_id)
                )
            
            logger.info(f"玩家 {player_id} 加入游戏 {game_id}")
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except:
                pass
            raise
            
    async def disconnect(self, game_id: str, player_id: str) -> None:
        """
        处理WebSocket连接断开
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
        """
        try:
            # 移除连接
            if game_id in self.active_connections:
                if player_id in self.active_connections[game_id]:
                    websocket = self.active_connections[game_id][player_id]
                    try:
                        await websocket.close()
                    except Exception as e:
                        logger.error(f"关闭WebSocket连接失败: {e}")
                    del self.active_connections[game_id][player_id]
                    
                self.game_connections[game_id].remove(player_id)
                
                # 如果游戏没有玩家了，清理游戏连接
                if not self.game_connections[game_id]:
                    del self.active_connections[game_id]
                    del self.game_connections[game_id]
                    # 取消ping任务
                    if game_id in self.ping_tasks:
                        self.ping_tasks[game_id].cancel()
                        del self.ping_tasks[game_id]
                    
            logger.info(f"玩家 {player_id} 离开游戏 {game_id}")
            
        except Exception as e:
            logger.error(f"断开WebSocket连接失败: {e}")
            
    async def broadcast(self, game_id: str, message: dict) -> None:
        """
        向游戏中的所有玩家广播消息
        
        Args:
            game_id: 游戏ID
            message: 要广播的消息
        """
        if game_id not in self.active_connections:
            return
            
        # 转换消息为JSON字符串
        try:
            json_message = json.dumps(message)
        except Exception as e:
            logger.error(f"消息序列化失败: {e}")
            return
            
        # 广播消息
        disconnected_players = []
        for player_id, connection in self.active_connections[game_id].items():
            try:
                await connection.send_text(json_message)
                logger.debug(f"向玩家 {player_id} 发送消息: {message['type']}")
            except Exception as e:
                logger.error(f"向玩家 {player_id} 发送消息失败: {e}")
                disconnected_players.append(player_id)
                
        # 清理断开的连接
        for player_id in disconnected_players:
            await self.disconnect(game_id, player_id)
                
    async def send_personal(self, game_id: str, player_id: str, message: dict) -> None:
        """
        向特定玩家发送消息
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
            message: 要发送的消息
        """
        if (game_id not in self.active_connections or
            player_id not in self.active_connections[game_id]):
            return
            
        try:
            # 转换消息为JSON字符串
            json_message = json.dumps(message)
            
            # 发送消息
            await self.active_connections[game_id][player_id].send_text(json_message)
            logger.debug(f"向玩家 {player_id} 发送个人消息: {message['type']}")
            
        except Exception as e:
            logger.error(f"向玩家 {player_id} 发送消息失败: {e}")
            await self.disconnect(game_id, player_id)
            
    def get_connected_players(self, game_id: str) -> Set[str]:
        """
        获取游戏中的已连接玩家
        
        Args:
            game_id: 游戏ID
            
        Returns:
            已连接玩家ID集合
        """
        return self.game_connections.get(game_id, set())
        
    async def close_all(self) -> None:
        """关闭所有连接"""
        # 取消所有ping任务
        for task in self.ping_tasks.values():
            task.cancel()
        self.ping_tasks.clear()
        
        # 关闭所有连接
        for game_id in list(self.active_connections.keys()):
            for player_id in list(self.active_connections[game_id].keys()):
                await self.disconnect(game_id, player_id)
                
        logger.info("所有WebSocket连接已关闭")
        
    async def ping(self, game_id: str) -> None:
        """
        向游戏中的所有玩家发送ping消息
        
        Args:
            game_id: 游戏ID
        """
        ping_message = {
            "type": "ping",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "game_id": game_id
            }
        }
        await self.broadcast(game_id, ping_message)
        
    async def start_ping(self, game_id: str, interval: int = 30) -> None:
        """
        开始定期ping
        
        Args:
            game_id: 游戏ID
            interval: ping间隔（秒）
        """
        try:
            while game_id in self.active_connections:
                await self.ping(game_id)
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info(f"Ping任务已取消: 游戏={game_id}")
        except Exception as e:
            logger.error(f"Ping任务异常: 游戏={game_id}, 错误={e}")
            
    def __del__(self):
        """析构函数，确保资源被正确清理"""
        # 取消所有ping任务
        for task in self.ping_tasks.values():
            if not task.done():
                task.cancel() 