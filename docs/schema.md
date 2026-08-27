# schemas 说明文档

## 1.目标

使用pydantic定义结构化输出schema，用于约束LLM返回结果的格式，提升结果的可解析性、可验证性和可维护性。

## 2.文件位置
'''text
app/schemas.py
'''

## 3.当前定义的模型

### 3.1 'Citation'

表示单条引用信息，包含下面字段：
- 'title':
- 'source'
- 'url'

### 3.2 'StructuredAnswer'

表示结构化回答问题，包含下面字段：
- 'topic'
- 'summary'
- 'key_points'
- 'citations'
- 'uncertainty'

## 4.设计原因

该结构适合作为最小版 LLM 结构化输出格式
1. 能表达回答主题与摘要
2. 能表达多条核心要点
3. 能挂载引用信息
4. 能显式标记不确定性
5. 后续易扩展为 RAG / Agent 输出格式

## 5. 示例合法数据

```json
{
  "topic": "FastAPI",
  "summary": "FastAPI 是一个现代 Python Web 框架。",
  "key_points": [
    "高性能",
    "类型提示友好",
    "自动生成接口文档"
  ],
  "citations": [
    {
      "title": "FastAPI Official Documentation",
      "source": "FastAPI",
      "url": "https://fastapi.tiangolo.com/"
    }
  ],
  "uncertainty": null
}
```

## 6. 非法数据示例

### 6.1 `key_points` 类型错误

```json
{
  "topic": "FastAPI",
  "summary": "FastAPI 是一个现代 Python Web 框架。",
  "key_points": "高性能, 类型提示友好",
  "citations": [],
  "uncertainty": null
}
```

错误原因：
- `key_points` 应为字符串列表，而不是单个字符串。

## 7. 当前边界

当前 schema 仅定义数据结构，不负责：

- 模型调用
- prompt 设计
- 输出重试
- 自动纠错
