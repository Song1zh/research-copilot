# 求职准备代码基线（2026-07-31）

## 基线说明

- 使用当前工作区版本，不回退到已提交master。
- 修改前测试：38 passed。
- Embedding升级后测试：44 passed。
- 工作区在任务开始前已有大量 staged、unstaged 和 untracked 文件。
- 本次没有执行 `git reset`、`git clean`、文件删除或覆盖式恢复。

## 本次新增/修改边界

- 新增显式embedding provider及collection隔离。
- 新增DashScope OpenAI兼容向量调用。
- 新增paper-level Hit@5、Recall@5、MRR@5和耗时评测。
- 新增评测相关人工标注、测试和文档。
- 不修改Neo4j抽取逻辑、不新增reranker、不升级引用语义校验。

## 运行结果

- 本地hash评测完成并保留原始JSON。
- 云端真实调用因账户状态异常未完成，未生成虚假对照数字。
