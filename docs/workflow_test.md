# Toy Workflow 测试记录（Day 5）

## 1. 目标

验证一个固定路径 toy workflow 是否能够完成以下三步：

- `understand_query`
- `generate_answer`
- `format_output`

并记录每个 node 的输入输出与 state 变化。

## 2. 技术说明

本原型基于 LangGraph 的 Graph API 实现，采用固定顺序的 workflow，而不是动态 agent。

## 3. 运行方式

```bash
python -m app.toy_workflow
```

## 4. 测试问题

1. `请用一句话解释什么是 FastAPI`
2. `LangGraph 和普通函数串联有什么区别？`
3. `列表推导式是什么？`

## 5. 观察点

### 5.1 `understand_query`
- 输入：`query`
- 输出：`topic`、`intent`

### 5.2 `generate_answer`
- 输入：`query`、`topic`、`intent`
- 输出：`answer`
- 若 LLM 调用失败，应记录 `error` 并 fallback

### 5.3 `format_output`
- 输入：前两步结果
- 输出：`structured_output`

## 6. 结果记录模板

### 测试 1
- query：
- understand_query 输出：
- generate_answer 输出：
- format_output 输出：
- 是否记录 trace：是 / 否

### 测试 2
- query：
- understand_query 输出：
- generate_answer 输出：
- format_output 输出：
- 是否记录 trace：是 / 否

### 测试 3
- query：
- understand_query 输出：
- generate_answer 输出：
- format_output 输出：
- 是否记录 trace：是 / 否

## 7. 结论

Day 5 已完成 toy workflow 原型，能够按固定路径执行三个 node，并打印每一步 state，同时保留 node 输入输出记录。