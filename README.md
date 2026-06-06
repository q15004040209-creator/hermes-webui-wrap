# hermes-webui-wrap

> **Hermes Agent Web UI 封装** — 零框架、轻量级 Web界面 + API 服务，一键部署

[English](#english) | [中文](#中文)

---

## 中文

### 什么是 hermes-webui-wrap？

**hermes-webui-wrap** 是 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 官方 Web UI 的轻量级 Python 封装，提供开箱即用的 Web 界面和 REST API 服务。

Hermes Agent 是一个自托管 AI 助手，运行在您的服务器上，支持多消息平台访问、跨会话记忆、自动化任务调度。本项目将其 Web UI 封装为 Python 标准库 HTTP 服务器 + Vanilla JS 前端，无需 Node.js、无需复杂构建。

### 核心特性

- **零依赖部署**：仅需 Python 3.11+，无需 Node.js，无需 webpack
- **自托管**：数据存储在本地，支持可选密码认证
- **多模型支持**：OpenAI、Anthropic、Google、DeepSeek、OpenRouter、MiniMax 等
- **三栏布局**：左侧边栏（会话管理）+ 中间聊天 +右侧工作区文件浏览
- **实时流式响应**：通过 SSE 推送 Token，支持取消
- **工作区管理**：内置文件浏览器、Git 状态、代码高亮
- **多主题**：System / Dark / Light +多种皮肤主题
- **移动端适配**：响应式布局，移动端可用

### 与原项目的关系

本项目是 [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui)（星标 13,588）的官方封装版本，保留所有原生功能，提供更简单的 Python 接入方式。

### 快速开始

```bash
# 克隆本封装项目
git clone https://github.com/q15004040209-creator/hermes-webui-wrap.git
cd hermes-webui-wrap

# 安装依赖
pip install -r requirements.txt

# 一键启动（自动检测 Hermes Agent）
python start.py

# 或手动指定路径
HERMES_WEBUI_HOST=0.0.0.0 HERMES_WEBUI_PORT=9000 python start.py
```

启动后访问 [http://localhost:8787](http://localhost:8787)

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HERMES_WEBUI_AGENT_DIR` | 自动检测 | Hermes Agent 目录 |
| `HERMES_WEBUI_HOST` | `127.0.0.1` | 绑定地址 |
| `HERMES_WEBUI_PORT` | `8787` | 端口 |
| `HERMES_WEBUI_STATE_DIR` | `~/.hermes/webui` | 状态存储目录 |
| `HERMES_WEBUI_DEFAULT_WORKSPACE` | `./workspace` | 默认工作区 |
| `HERMES_WEBUI_PASSWORD` | 无 | 开启密码认证 |

### API 接口

```python
import requests

# 发送消息
resp = requests.post("http://localhost:8787/api/chat", json={
    "message": "你好",
    "session_id": "default"
})
print(resp.json())

# 获取会话历史
resp = requests.get("http://localhost:8787/api/sessions")
print(resp.json())

# 创建新会话
resp = requests.post("http://localhost:8787/api/sessions", json={
    "title": "新对话"
})
print(resp.json())
```

### 项目结构

```
hermes-webui-wrap/
├── api/ # 后端 Python API
│   ├── server.py         # HTTP 服务器入口
│   ├── config.py         # 配置与发现逻辑
│   ├── models.py         # 会话模型 + CRUD
│   └── streaming.py     # SSE 流式响应
├── static/              # 前端静态资源
│   ├── index.html       # HTML 模板
│   ├── style.css        # 所有样式（含主题）
│   └── ui.js            # DOM 操作与渲染
├── start.py             # 启动脚本
├── requirements.txt    # Python 依赖
└── README.md
```

### 系统要求

- Python 3.11+
- Hermes Agent 已安装（自动检测或手动指定 `HERMES_WEBUI_AGENT_DIR`）
- 支持 Linux / macOS / Windows (WSL2)

---

## English

### What is hermes-webui-wrap?

**hermes-webui-wrap** is a lightweight Python wrapper for the official [Hermes Agent](https://github.com/NousResearch/hermes-agent) Web UI, providing an out-of-the-box Web interface and REST API service.

Hermes Agent is a self-hosted autonomous agent that lives on your server, accessible via terminal or messaging apps, that remembers what it learns and gets more capable the longer it runs. Hermes WebUI is a lightweight, dark-themed web app in your browser for interacting with Hermes Agent.

### Key Features

- **Zero-config deployment**: Python 3.11+ only, no Node.js, no bundler
- **Self-hosted**: Local data storage, optional password auth
- **Multi-model**: OpenAI, Anthropic, Google, DeepSeek, OpenRouter, MiniMax, and more
- **Three-panel layout**: Sessions (left) + Chat (center) + File browser (right)
- **Real-time streaming**: SSE token streaming with cancel support
- **Workspace management**: Built-in file browser, Git status, syntax highlighting
- **Theming**: System / Dark / Light + multiple skin themes
- **Mobile responsive**: Works on phones and tablets

### Relationship to upstream

This project is an official Python wrapper for [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui) (13,588 stars), preserving all native features while providing a simpler Python integration path.

### Quick Start

```bash
git clone https://github.com/q15004040209-creator/hermes-webui-wrap.git
cd hermes-webui-wrap
pip install -r requirements.txt
python start.py
```

Visit [http://localhost:8787](http://localhost:8787)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_WEBUI_AGENT_DIR` | auto-detect | Hermes Agent directory |
| `HERMES_WEBUI_HOST` | `127.0.0.1` | Bind address |
| `HERMES_WEBUI_PORT` | `8787` | Port |
| `HERMES_WEBUI_STATE_DIR` | `~/.hermes/webui` | State storage directory |
| `HERMES_WEBUI_DEFAULT_WORKSPACE` | `./workspace` | Default workspace |
| `HERMES_WEBUI_PASSWORD` | none | Enable password auth |

### REST API

```python
import requests

# Send a message
resp = requests.post("http://localhost:8787/api/chat", json={
    "message": "Hello",
    "session_id": "default"
})
print(resp.json())

# List sessions
resp = requests.get("http://localhost:8787/api/sessions")
print(resp.json())

# Create new session
resp = requests.post("http://localhost:8787/api/sessions", json={
    "title": "New Chat"
})
print(resp.json())
```

### Project Structure

```
hermes-webui-wrap/
├── api/                  # Backend Python API
│   ├── server.py         # HTTP server entry
│   ├── config.py         # Config & auto-discovery
│   ├── models.py         # Session model + CRUD
│   └── streaming.py     # SSE streaming
├── static/              # Frontend static assets
│   ├── index.html       # HTML template
│   ├── style.css        # All styles (themes included)
│   └── ui.js            # DOM helpers & rendering
├── start.py             # Launcher
├── requirements.txt    # Python dependencies
└── README.md
```

### Requirements

- Python 3.11+
- Hermes Agent installed (auto-detected or set `HERMES_WEBUI_AGENT_DIR`)
- Linux / macOS / Windows (WSL2)

---

## License

MIT License - see [upstream license](https://github.com/nesquena/hermes-webui/blob/master/LICENSE)