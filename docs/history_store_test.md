# Request History 测试记录（Day 20）

## 1. 目标

验证 SQLite 持久化模块是否能够正确记录请求历史。

## 2. 当前表结构

表名：`request_history`

字段：
- `id`：自增主键
- `query`：用户问题
- `answer_summary`：回答摘要
- `timestamp`：请求时间
- `latency_ms`：请求耗时（毫秒）

## 3. 测试项

### 3.1 基本写入
- 插入 1 条记录
- 检查字段是否正确保存

### 3.2 时间倒序读取
- 插入 2 条不同时间记录
- 检查 `list_recent()` 是否按 `timestamp DESC` 返回

### 3.3 非法 limit
- `limit=0`
- 预期抛出 `ValueError`

## 4. 当前结果

- 数据库文件可自动创建
- 表结构可自动初始化
- 请求记录可成功写入
- 最近记录可正确读取
- 时间倒序排序正常
- 非法参数校验正常

## 5. 当前结论

Day 20 已完成最小持久化能力初版。系统已能够将请求的 query、answer 摘要、timestamp 与 latency 写入 SQLite，并支持读取最近请求历史。