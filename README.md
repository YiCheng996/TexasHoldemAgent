# 德州扑克多智能体系统

基于大语言模型的多人德州扑克游戏系统，支持AI与人类玩家共同参与。

## 功能特点

- 支持5人局德州扑克游戏
- 基于LiteLLM的多模型AI玩家
- 实时游戏界面
- 完整的游戏记录和分析
- AI玩家行为分析和策略学习

## 系统要求

- Python 3.9+
- SQLite3
- 支持的操作系统：Windows/Linux/MacOS

## 安装

1. 克隆仓库：
```bash
git clone [repository-url]
cd TexasHoldemAgent
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
- 复制 `.env.example` 为 `.env`
- 填写必要的配置信息（API密钥等）

## 使用方法

1. 启动服务器：
```bash
python src/api/main.py
```

2. 访问Web界面：
```
http://localhost:8000
```

## 项目结构

```
TexasHoldemAgent/
├── src/                 # 源代码
│   ├── engine/         # 游戏引擎
│   ├── agents/         # AI智能体
│   ├── api/           # API服务
│   ├── web/           # Web界面
│   ├── db/            # 数据库
│   └── utils/         # 工具函数
├── config/            # 配置文件
├── data/             # 数据存储
├── docs/             # 项目文档
│   ├── PRD.md        # 项目需求文档
│   ├── rules.md      # 游戏规则说明
│   └── scratchpad.md # 开发记录
└── tests/            # 测试用例
```

## 开发

1. 运行测试：
```bash
pytest
```

2. 代码风格检查：
```bash
flake8
```

## 许可证

[License Type] - 查看 LICENSE 文件了解更多信息。

## 贡献

欢迎提交问题和拉取请求。
