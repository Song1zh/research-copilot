# Retriever 测试记录（Day 11）

## 1. 目标

验证检索函数 `retrieve_evidence(query)` 是否能够：

- 从向量库中返回 top-k 相关 chunk
- 输出 chunk 文本、score、raw_distance、metadata
- 对不同 query 表现出基本区分能力

## 2. 文件位置

```text
core/retriever.py
tests/test_retriever.py
```

## 3. 测试文档

- `data/sample.txt`
- `README.md`

## 4. 测试 query

1. `FastAPI 是什么`
2. `向量库起什么作用`
3. `什么是Cl20`
4. `氢化镁为什么适合作为推进剂`

## 5. 结果记录

### Query 1
- top-1 是否合理：是
- 是否存在明显噪声：是

### Query 2
- top-1 是否合理：否
- 是否存在明显噪声：是

### Query 3
- top-1 是否合理：是
- 是否存在明显噪声：是

### Query 4
- top-1 是否合理：是
- 是否存在明显噪声：是

## 6. 检索偏差总结

当前观察到的偏差包括：

- query 表达过泛导致结果发散
- chunk 切分边界影响检索质量
- 多主题文档造成候选 chunk 混杂
- top-k 中存在部分弱相关结果

## 7. 当前结论

已完成检索函数初版，能够返回相关 chunk 与 score，并支持多 query 的人工检索测试。