"""
API数据模型定义。
包含请求和响应的Pydantic模型。
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from src.engine.game import ActionType

class GameConfig(BaseModel):
    """游戏配置模型"""
    model_config = ConfigDict(from_attributes=True)
    
    num_players: int = Field(..., ge=2, le=9, description="玩家数量")
    initial_stack: int = Field(1000, ge=100, description="初始筹码")
    small_blind: int = Field(10, ge=1, description="小盲注")

class PlayerInfo(BaseModel):
    """玩家信息模型"""
    model_config = ConfigDict(from_attributes=True)
    
    player_id: str = Field(..., description="玩家ID")
    chips: int = Field(..., description="当前筹码")
    is_active: bool = Field(..., description="是否在游戏中")
    is_ai: bool = Field(False, description="是否是AI玩家")
    current_bet: int = Field(0, description="当前下注")
    total_bet: int = Field(0, description="本局游戏总下注")
    is_all_in: bool = Field(False, description="是否全下")
    hand_cards: List[str] = Field(default_factory=list, description="手牌")

class GameState(BaseModel):
    """游戏状态模型"""
    model_config = ConfigDict(from_attributes=True)
    
    game_id: str = Field(..., description="游戏ID")
    phase: str = Field(..., description="游戏阶段")
    pot_size: int = Field(0, description="当前底池大小")
    community_cards: List[str] = Field(default_factory=list, description="公共牌")
    current_player: Optional[str] = Field(None, description="当前行动玩家")
    players: List[PlayerInfo] = Field(..., description="玩家列表")
    current_bet: int = Field(0, description="当前最大下注额")
    min_raise: int = Field(0, description="最小加注额")
    max_raise: Optional[int] = Field(None, description="最大加注额")

class PlayerAction(BaseModel):
    """玩家动作模型"""
    model_config = ConfigDict(from_attributes=True)
    
    player_id: str = Field(..., description="玩家ID")
    action_type: str = Field(..., description="动作类型")
    amount: int = Field(0, description="动作金额")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="动作时间戳")

class ActionResult(BaseModel):
    """动作结果模型"""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool = Field(..., description="是否成功")
    action: PlayerAction = Field(..., description="执行的动作")
    state: GameState = Field(..., description="更新后的游戏状态")
    error: Optional[str] = Field(None, description="错误信息")

class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    model_config = ConfigDict(from_attributes=True)
    
    type: str = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")

class ErrorResponse(BaseModel):
    """错误响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    detail: str = Field(..., description="错误详情")
    error_code: Optional[str] = Field(None, description="错误代码")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")

class AIPlayerConfig(BaseModel):
    """AI玩家配置模型"""
    model_config = ConfigDict(from_attributes=True)
    
    model: str = Field(..., description="使用的模型名称")
    api_key: str = Field(..., description="API密钥")
    base_url: str = Field(..., description="API基础URL")
    temperature: float = Field(0.7, ge=0, le=1, description="温度参数")
    max_tokens: int = Field(10000, ge=1000, description="最大token数")
    timeout: int = Field(30, ge=10, description="超时时间")
    description: str = Field("在激进和保守之间寻找平衡的玩家", description="AI玩家性格描述")

class AIPlayersConfig(BaseModel):
    """AI玩家配置集合模型"""
    model_config = ConfigDict(from_attributes=True)
    
    ai_1: AIPlayerConfig = Field(..., description="AI玩家1配置")
    ai_2: AIPlayerConfig = Field(..., description="AI玩家2配置") 