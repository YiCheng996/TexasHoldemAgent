# 德州扑克多智能体系统 / Texas Holdem Multi-Agent System

基于大语言模型的多人德州扑克游戏系统，支持AI与人类玩家共同参与的学术研究项目。

A multi-player Texas Hold'em poker system based on large language models, supporting both AI and human players for academic research.

## 功能特点 / Features

- 完整的德州扑克引擎 / Complete Texas Hold'em Engine
  - 支持5人局标准德州扑克规则 / Standard 5-player poker rules
  - 完整的牌型判定系统 / Complete hand evaluation system
  - 回合控制和状态管理 / Round control and state management
  - 筹码管理和结算系统 / Chip management and settlement system

- AI智能体系统 / AI Agent System
  - 基于LiteLLM的多模型支持 (https://docs.litellm.ai/docs/) / Multi-model support via LiteLLM
  - 支持多个模型之间的对局 / Support for games between multiple models
  - 可配置的AI性格特征 / Configurable AI personalities
  - 实时决策分析 / Real-time decision analysis
  - 短期&长期记忆管理（开发中） / Short&Long-term memory management(developing)
  - 基于ChromaDB的向量存储 / Vector storage with ChromaDB

- 实时Web界面 / Real-time Web Interface
  - WebSocket实时通信 / WebSocket communication
  - 响应式设计 / Responsive design
  - 游戏状态实时更新 / Real-time game state updates
  - 玩家操作界面 / Player action interface

- 数据分析功能 / Data Analysis
  - 完整的游戏记录 / Complete game records
  - AI行为分析 / AI behavior analysis
  - 策略效果评估 / Strategy evaluation
  - 玩家数据统计 / Player statistics

## 系统要求 / Requirements

- Python 3.9+
- Node.js 14+ (前端开发 / Frontend development)
- SQLite3
- 支持的操作系统 / Supported OS: Windows/Linux/MacOS

## 安装步骤 / Installation

1. 克隆仓库 / Clone repository：
```bash
git clone https://github.com/YiCheng996/TexasHoldemAgent.git
cd TexasHoldemAgent
```

2. 安装依赖 / Install dependencies：
```bash
# 后端依赖 / Backend dependencies
pip install -r requirements.txt


3. 修改配置文件 / Edit configurations:
  - `.env`: 环境变量 / Environment variables
  - `config/game.yml`: 游戏配置 / Game settings
  - `config/llm.yml`: AI配置 / AI settings

## 配置说明 / Configuration Guide

### 游戏配置 / Game Configuration (game.yml)
```yaml
game:
  max_players: 5          # 最大玩家数 / Max players
  initial_chips: 1000     # 初始筹码 / Starting chips
  small_blind: 10         # 小盲注 / Small blind
  big_blind: 20          # 大盲注 / Big blind

server:
  host: "localhost"      # 服务器地址 / Server host
  port: 8000            # 端口 / Port
```

### AI配置 / AI Configuration (llm.yml)
```yaml
llm:
  api_key: "your-api-key"    # API密钥 / API key
  model: "gpt-3.5-turbo"     # 模型名称 / Model name
  temperature: 0.7           # 温度参数 / Temperature

memory（暂未实现应用/developing）:
  short_term:
    max_rounds: 10           # 短期记忆回合数 / Short-term memory rounds
  long_term:
    collection: "poker_memories"  # 向量存储集合名 / Vector storage collection
```

## 启动服务 / Start Services

1. 启动后端 / Start backend：
```bash
python src/web/server.py
```

2. 访问系统 / Access system：
```
http://localhost:8080
```



## 许可证 / License

MIT License - 查看 [LICENSE](LICENSE) 文件了解更多信息。
See [LICENSE](LICENSE) file for details.

## 贡献 / Contributing

欢迎提交问题和拉取请求。
Issues and pull requests are welcome.
