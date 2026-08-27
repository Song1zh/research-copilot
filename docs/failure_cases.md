# Failure Case Analysis（Day 25）

## 1. 文档目标

本文档用于记录 Project A / Research Copilot 在当前阶段的典型失败模式，帮助后续优化检索、回答生成、引用校验与接口表现。

## 2. 失败模式总览

当前整理的失败模式包括：

1. retrieval drift
2. unsupported evidence
3. format instability
4. noisy pdf
5. refusal needed

---

## 3. Case 1：retrieval drift

### 3.1 失败定义

检索漂移指的是检索模块虽然返回了top-k证据，但这些证据与用户问题只存在表面相关性，无法支撑其真正回答核心

### 3.2 真实例子
- 问题："文中提到了哪些研究不足或空白？"
- 文档："sample.txt"
- 现象："文中指出了 CL-20 材料因高感度导致的应用局限，作为研究背景中的不足，未明确提及本研究的具体局限"

### 3.3 现象

- tok-k返回非空
- retrieval_hit = 0
- 回答出现泛化总结/limitations不贴问题

### 3.4 根因分析

- chunk粒度偏大，局限性信息被藏在大段背景中
- 检索只做向量召回，缺少额外的rerank
- “研究不足/空白”类问题本身表达更抽象，容易与“研究意义”“现状综述”混淆

### 3.5 当前系统表现

系统可以稳定返回结构化结果，但在该类问题上 evidence 召回质量不足，导致最终回答可用性有限

### 3.6 后续优化方向

- 调整chunk策略，提高局限类信息密度
- 补充rerank
- 对“limitations”类问题单独设计prompt

---

## 4. Case 2：unsupported evidence

### 4.1 失败定义
unsupported evidence 指的是：回答中给出了 claim 与 citation，但被引用的 evidence 实际上不足以支撑该 claim，存在弱支持、错配或过度概括问题。

### 4.2 真实例子
- 问题："文中研究目标是什么？"
- 现象：文中研究目标是为了有效调节 CL-20 的能量释放速率、降低感度并提升整体的作功能力，并准确描述 Mg 纳米颗粒与 CL-20 在高温下的氧化还原反应过程 [E1,E3]。

### 4.3 现象
- "citation_grounded = 0"
- claim 比 evidence 表述更强
- evidence 更像背景信息，而不是直接结论支撑

### 4.4 根因分析
- 模型倾向于把 evidence 做概括后写成更完整结论
- 当前 verifier 仍以轻量规则为主，不能完全阻止弱支持 claim
- evidence 本身可能只支持“相关”，不支持“结论已成立”

### 4.5 当前系统表现
系统已具备 citation / evidence 输出能力，但在少数情况下仍会出现“有引用但支撑不足”的问题。

### 4.6 后续优化方向
- 收紧 findings / summary 的 prompt 约束
- 在 verifier 中区分“strong support / weak support”
- 对 unsupported claim 做自动降级或改写

---

## 5. Case 3：format instability

### 5.1 失败定义
format instability 指的是：模型输出在格式层面不稳定，例如非法 JSON、字段缺失、字段类型错误，导致下游解析失败或 schema 校验失败。

### 5.2 真实例子
- 开发阶段曾真实出现：
  - 非法 JSON
  - JSON 合法但字段类型不符合 schema
- 例如：
  - methods 被输出为字符串而非列表
  - JSON 缺少闭合括号导致解析失败

### 5.3 现象
- "json.loads()" 失败
- 进而触发："MODEL_JSON_INVALID"

### 5.4 根因分析
- LLM 在自由生成时格式不稳定
- 结构化约束不足时容易混入自然语言解释
- schema 边界不明确时，列表字段容易被输出成单个字符串

### 5.5 当前系统表现
该失败模式在开发阶段真实出现过。当前版本通过固定 schema、parser 与异常兜底，已将 JSON 合法率与 schema 合法率稳定到 100%。

### 5.6 后续优化方向
- 继续保持严格 JSON-only prompt
- 对关键字段做更细粒度 schema 检查
- 保留并完善 format 层异常兜底
- 
## 6. Case 4：refusal needed

### 6.1 失败定义
refusal needed 指的是：用户问题超出当前文档证据范围，此时系统应避免编造答案，而应给出基于证据边界的明确拒答。

### 6.2 真实例子
- 问题："法国大革命什么时候发生？"
- 文档："sample.txt"
- 当前评测结果：
  - retrieval_hit = 0
  - usable_answer = 1 （多数情况下）

### 6.3 现象
- evidence 与问题无关
- 系统若直接拒答，用户仍可接受
- 若强行回答，则会立即构成幻觉

### 6.4 根因分析
- 当前系统的知识边界应严格限定在用户上传文档
- 对无关问题，最优策略不是“猜测”，而是“基于当前证据无法回答”
- refusal 是 evidence-based answering 的一部分，而不是系统失败

### 6.5 当前系统表现
在无关问题场景下，系统大多能够避免错误召回，并通过说明“当前文档不包含相关信息”来完成可用拒答。

### 6.6 后续优化方向
- 进一步统一 refusal 模板
- 在无关 query 场景下减少无意义 citation
- 将 refusal 明确纳入 API / 前端展示语义中

## 8. 当前结论

从当前失败案例来看，项目已经完成“结构稳定、链路闭环”的第一阶段，但在检索质量、证据支持强度、PDF 文本质量与无关问题处理口径上仍有明显优化空间。