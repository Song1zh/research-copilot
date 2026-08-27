# Research Copilot Prompt 测试记录（Day 12）

## 1. 目标

验证 Research Copilot prompt 是否能够稳定输出固定结构的 JSON 回答，字段包括：

- summary
- methods
- findings
- limitations
- evidence

## 2. 文件位置

```text
schemas/research_answer.py
tests/test_research_prompt.py
```

## 3. 测试设置

- 固定 query：
- 固定 evidence 来源：
- 测试次数：2 次
- 期望结果：
  1. 输出为合法 JSON
  2. 字段齐全且无额外字段
  3. 字段类型稳定
  4. 不编造 evidence 之外的信息

## 4. 测试记录

### 第 1 次
- JSON 是否可解析：是
- Schema 是否校验通过：是
- 是否出现额外字段：否
- 是否出现格式错误：否
- 备注：内容不够收敛

### 第 2 次
- JSON 是否可解析：是
- Schema 是否校验通过：是
- 是否出现额外字段：否
- 是否出现格式错误：否
- 备注：内容不够收敛


## 5. 当前结论

Day 12 已完成 Research Copilot prompt 初版，并完成结构化输出稳定性测试，但“只回答当前问题、不过度扩展”的能力还需要再用 prompt 收紧。