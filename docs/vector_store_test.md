# Vector Store 测试

## 1.目标

验证最小向量检索模块是否能够完成：

- 文档加载
- 文本切分
- 建立chroma collection
- 将chunk写入向量库
- 使用query进行top-k查询

## 2.技术路径

本阶段使用chroma作为最小向量数据库后端，使用本地持久化客户端完成原型验证

## 3.文件位置
'''text
core/vector_store.py
tests/test_vector_store.py
'''

## 4.测试命令

### 文档 A：sample.txt
```bash
python -m tests.test_vector_store --path data/sample.txt --query "CL-20 热解研究" --top-k 3
```

### 文档 B：README.md
```bash
python -m tests.test_vector_store --path README.md --query "workflow 是什么" --top-k 3
```

## 5. 当前边界

当前版本仍存在以下局限：

1. 仅完成最小 Chroma 检索主线
2. 未实现 FAISS 后端
3. 未对 embedding 模型做显式配置
4. 检索质量仅做人工观察，未做定量评估

## 6. 结论

Day 10 已完成最小向量检索模块，能够完成 query → top-k 的基本检索闭环，并可用于后续 RAG 原型扩展。