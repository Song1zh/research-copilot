# Text Splitter 测试记录（Day 9）

## 1. 目标

验证文本切分器是否能够：

- 支持 `chunk_size`
- 支持 `chunk_overlap`
- 对不同风格文档进行切分
- 尽量在较自然的位置切分文本

## 2. 文件位置

```text
core/text_splitter.py
tests/test_text_splitter.py
```

## 3. 测试文档

### 文档 A
- 路径：`data/sample.txt`
- 类型：txt
- 特点：连续中文长文本

### 文档 B
- 路径：`README.md`
- 类型：md
- 特点：标题、列表、代码块混合文本

## 4. 测试参数

### 参数组 1
- `chunk_size=300`
- `chunk_overlap=50`

### 参数组 2
- `chunk_size=500`
- `chunk_overlap=80`

### 参数组 3
- `chunk_size=800`
- `chunk_overlap=100`

## 5. 当前边界

当前 splitter 仍有以下局限：

1. 仍以字符长度为主，不是 token 级切分
2. markdown 未做结构感知切分
3. 只做了较简单的自然边界优先策略
4. 尚未针对检索效果做定量评估

