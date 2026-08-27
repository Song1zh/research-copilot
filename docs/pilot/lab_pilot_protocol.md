# Research Copilot 实验室试用协议

## 最小试用规模

- 建议3名真实实验室用户，每人提交5个日常科研问题；
- 若只有项目作者，`role`写`author`，结果只能称为作者试用；
- 使用匿名参与者编号，不填写姓名、学号或其他个人信息；
- 提交前确认`consent=yes`，文献片段可能发送到百炼模型。

## 操作步骤

1. 启动Neo4j、FastAPI和Streamlit。
2. 参与者提出自己真实需要解决的问题，不使用开发者给出的演示问题。
3. 记录从提问到找到可用证据的总时间，而不是仅记录接口延迟。
4. 对回答有用性、证据有用性分别按1–5分评分。
5. `solved`只在回答和原文证据足以支持当前研究任务时填`yes`。
6. 失败类型从`retrieval`、`graph`、`generation`、`citation`、`latency`、
   `usability`、`none`中选择，并在`notes`记录具体表现。

数据写入`lab_pilot_sessions.csv`后运行：

```powershell
.\.venv\Scripts\python.exe scripts\summarize_lab_pilot.py
```

空表只会生成“没有真实参与者数据”的报告，不会产生成功率。简历只有在完成
真实试用后才能写参与人数、问题数、任务解决率或满意度。
