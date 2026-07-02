# 🤖 AI Agent 智能对话系统

基于 [LangGraph](https://langchain.com/langgraph) 和 [Ollama](https://ollama.com) 的本地 AI Agent，支持上下文记忆、多工具调用和流式对话。

## 功能特点

- **上下文记忆** — 自动记住对话历史，支持多轮对话
- **指代消解** — 理解"那里"、"上次那个"等指代词
- **工具集成** — 内置天气查询（高德地图 API），可扩展更多工具
- **本地运行** — 通过 Ollama 本地推理，无需联网 LLM API

## 技术栈

| 组件 | 技术 |
|------|------|
| 工作流引擎 | LangGraph |
| 本地模型 | Ollama + DeepSeek-R1-1.5B |
| 记忆系统 | SQLite + 自定义 HybridMemory |
| 工具调用 | LangChain Tools |

## 快速开始

### 1. 安装依赖

```bash
pip install langgraph langchain langchain-core pydantic requests python-dotenv
```

### 2. 安装 Ollama 并拉取模型

```bash
# 安装 Ollama: https://ollama.com
ollama pull deepseek-r1:1.5b
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_NAME=deepseek-r1:1.5b
AMAP_API_KEY=你的高德地图API密钥  # 可选，用于天气查询
```

### 4. 运行

```bash
python xcmain.py
```

## 项目结构

```
├── xcmain.py           # 主入口，交互式对话界面
├── xcagent.py          # Agent 核心，LangGraph 工作流定义
├── xcmemory.py         # 混合记忆系统（短时+长时记忆）
├── xcollama_client.py  # Ollama API 客户端
├── xctools.py          # 工具函数（天气查询等）
├── xcconfig.py         # 配置中心
└── xcapi.py            # 接口定义
```

## 使用说明

```
👤 用户: 北京今天天气怎么样？
🤖 助手: 北京今天晴天，温度 25°C ...

👤 用户: 那上海呢？
🤖 助手: [自动理解"那"指代天气查询] 上海今天多云 ...
```

- 输入 `clear` 清除对话记忆
- 输入 `quit` 退出
