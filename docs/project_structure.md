# 项目结构说明（Day 6）

## 1. 目标

本次重构的目标是将前几天的原型代码进行模块化拆分，使项目结构更清晰、更易维护，并为后续继续扩展 API、RAG、Agent 功能打基础。

## 2. 当前目录结构

```text
ai-app-engineer-roadmap/
├─ app/
│  ├─ __init__.py
│  └─ main.py
├─ core/
│  ├─ __init__.py
│  ├─ config.py
│  └─ llm_client.py
├─ schemas/
│  ├─ __init__.py
│  └─ structured_output.py
├─ workflows/
│  ├─ __init__.py
│  └─ toy_workflow.py
├─ tests/
│  ├─ __init__.py
│  └─ test_schemas.py
├─ docs/
│  └─ ...
├─ .env.example
├─ .gitignore
├─ README.md
└─ requirements.txt
```

## 3. 各目录职责

### `app/`
项目入口层，当前主要包含 FastAPI 服务入口。

### `core/`
项目核心能力层，包含配置读取与 LLM 调用客户端。

### `schemas/`
数据结构定义层，使用 Pydantic 描述结构化输出 schema。

### `workflows/`
工作流层，包含基于 LangGraph 的 toy workflow 原型。

### `tests/`
测试层，存放 schema 等模块的验证脚本。

### `docs/`
文档层，存放环境说明、API 测试、LLM 测试、workflow 测试、项目结构说明等文档。

## 4. 设计原则

1. 入口与核心能力分离
2. schema 与业务逻辑分离
3. workflow 单独归类
4. 测试代码独立管理
5. 尽量保持最小、清晰、可扩展

## 5. 当前边界

当前工程化重构仍属于初版，尚未引入：

- 更完整的配置管理
- 单元测试框架（如 pytest）
- 更细粒度的 routers/services 分层
- 日志系统
- CI/CD 配置
