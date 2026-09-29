# 🤖 My AI Assistant & Agent (专属 AI 全栈超级智能体)

> 基于 **FastAPI + Docker PostgreSQL + DeepSeek + Web Speech 原生双语语音 + RAG 私有知识库 + Function Calling 智能体工具箱** 构建的企业级全栈 AI 系统。

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![DeepSeek](https://img.shields.io/badge/AI%20Engine-DeepSeek%20V3-4D6BFE?style=for-the-badge)](https://deepseek.com)
[![Docker](https://img.shields.io/badge/Container-Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Tailwind CSS](https://img.shields.io/badge/Frontend-Tailwind%20CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

---

## 🌟 核心特性一览

- 🤖 **AI Agent 智能体工具箱 (Function Calling)**：真实世界时钟感知（打破时间冻结）、全球实时天气查询、智能自主工具调用决策链路。
- 📚 **企业级 RAG 私有知识库 (开卷问答)**：支持 PDF/TXT/MD 多格式智能切片，PostgreSQL 向量级关键词精确召回，100% 杜绝幻觉。
- 🎙️ **多模态原生语音交互 (Web Speech)**：浏览器原生 STT 实时语音转写、TTS 真人流利朗读、角色中英音色自适应。
- 🧠 **ChatGPT 级逐字打字机**：基于 SSE 与 StreamingResponse 毫秒级打字机流式输出。
- 💾 **数据库级多轮历史记忆链**：PostgreSQL 容器化存储上下文对话，支持一键清空重置。
- 🎭 **4 大动态角色自由切换**：全栈导师、英语私教、大厂面试官、脱口秀大师。
- ☁️ **生产级云端 7×24h 永续部署**：成功运行于腾讯云 Linux 服务器，全网随时随地跨设备使用。

---

## 🛠️ 技术栈总览

| 模块 | 技术选型 | 说明 |
| :--- | :--- | :--- |
| **前端交互** | Tailwind CSS + Marked.js + Highlight.js | 响应式设计、Markdown 极速排版与代码高亮复制 |
| **多模态** | 原生 Web Speech API | 零依赖纯浏览器端 STT 与 TTS 引擎 |
| **后端框架** | FastAPI + Uvicorn + Pydantic | 极速异步 Python Web 框架，严格类型校验 |
| **AI 模型** | DeepSeek-V3 (OpenAI SDK 协议) | 官方 API 接入，支持 Function Calling 工具调用 |
| **私有知识库**| PyPDF + PostgreSQL 关键词检索 | 轻量高效 RAG 落地架构 |
| **数据持久化**| PostgreSQL 16 (Docker 容器化) | 历史记忆链与知识切片持久存储 |
| **生产运维** | Docker + Linux CentOS + Systemd/Nohup | 7×24 小时云端守护运行 |

---

## 🚀 极速本地运行

```bash
# 1. 启动数据库
docker run -d --name ai-postgres -p 5432:5432 -e POSTGRES_PASSWORD=mysecretpassword postgres:16

# 2. 安装依赖并启动
pip install fastapi uvicorn psycopg2-binary openai python-dotenv pypdf python-multipart
python server.py
```

---

## 👨‍💻 作者
由 **小林同学** 独立全栈架构设计与落地。欢迎 Star ⭐️ 关注项目更新！