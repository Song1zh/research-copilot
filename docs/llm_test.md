# LLM 调用测试

## 1.测试目标

验证最小 LLM 调用脚本是否能够：
- 正常读取'.env'配置
- 完成一次模型调用
- 支持‘system prompt’
- 支持'user prompt'
- 对常见异常给出可理解的报错

## 2.运行方式
python app/lim_client.py

## 3.测试用例

### 3.1 普通问答测试

**system prompt**
```text
你是一名简洁、准确的ai助手
```
**user prompt**
```text
请用一句话解释什么是FastAPI
```

**结果**
- 是否成功：成功
- 模型输出：FastAPI 是一个基于 Python 类型提示的现代高性能 Web 框架，用于快速构建 API 并自动生成文档。

---

### 3.2 格式约束测试

**system prompt**
```text
你是一名简洁助手，回答必须控制在20个字以内。
```

**user prompt**
```text
请解释什么是 FastAPI
```

**结果**
- 是否成功：成功
- 模型输出：现代高性能 Python 接口框架。
- 是否基本遵循格式要求：是

---

### 3.3 角色约束测试

**system prompt**
```text
你是一名面向初学者的 Python 助教，请用通俗中文回答。
```

**user prompt**
```text
什么是列表推导式？
```

**结果**
- 是否成功：成功
- 模型输出：你好呀！👋 我是你的 Python 助教....
- 角色风格是否基本符合预期：是

## 4. 异常与错误处理记录

### 4.1 缺少 API Key

**现象**
- 程序启动失败
**预期处理**
- 抛出清晰错误：‘API key not found.’

### 4.2 user_prompt 为空

**现象**
- 调用前参数校验失败

**预期处理**
- 抛出清晰错误：`user_prompt not found.`

## 5.结论
已完成最小LLM调用脚本，能够读取配置、发送‘system/user prompt’并返回模型输出