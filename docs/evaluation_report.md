# 评测报告

## 文档目的

本文档记录 Research Copilot 当前阶段可度量的系统表现。目标不是宣称系统已经达到生产级质量，而是让项目具备可审阅性：测试了什么、记录了哪些指标、系统在哪些问题上表现较好、又在哪些场景下失败。

## 评测数据集

当前评测基于 `sample.txt` 人工设计 20 条问题，分为四类：

| 问题类别 | 数量 | 评测目标 |
| --- | ---: | --- |
| `fact` | 5 | 检查系统对文档直接事实的抽取能力。 |
| `methods_findings` | 5 | 检查系统对研究方法和主要发现的总结能力。 |
| `limitations` | 5 | 检查系统对研究局限、研究空白等抽象问题的回答能力。 |
| `irrelevant` | 5 | 检查系统能否拒答文档证据范围之外的问题。 |

评测脚本为 `scripts/run_manual_eval.py`。脚本会生成带自动字段的 CSV，并保留 `retrieval_hit`、`citation_grounded`、`usable_answer` 三列供人工标注。

## 评测指标

| 指标 | 定义 | 结果 |
| --- | --- | ---: |
| JSON 合法率 | LLM 输出可以被 JSON parser 解析，不包含预期的前置失败场景。 | 100% |
| Schema 通过率 | 解析后的 JSON 可以通过 `ResearchCopilotAnswer` Pydantic schema 校验。 | 100% |
| 检索命中率 | 检索到的 evidence 包含足以回答问题的相关信息。 | 50% |
| 引用支撑率 | 回答中的 claim 能被对应 evidence snippet 支撑。 | 80% |
| 回答可用率 | 最终回答在当前项目边界下对用户问题有实际帮助。 | 60% |

原始汇总文件：`app_data/eval/manual_eval_sample_20260422_092923_manual_summary.json`。

## 分类结果

| 问题类别 | 检索命中率 | 回答可用率 | 说明 |
| --- | ---: | ---: | --- |
| `fact` | 60% | 20% | 直接事实有时不在 top-k chunk 中，导致回答可用率较低。 |
| `methods_findings` | 100% | 100% | 表现最好，因为方法和发现类信息语义密度更高。 |
| `limitations` | 40% | 40% | 抽象问题容易检索到背景信息，而不是明确的局限或空白。 |
| `irrelevant` | 0% | 80% | 检索命中率低是预期现象，关键是系统能否拒绝无证据问题。 |

## 典型失败模式

- Retrieval drift：top-k evidence 非空，但只和问题表面相关，无法支撑核心回答。
- Unsupported evidence：回答带有引用，但被引用片段对 claim 只有弱支撑或无支撑。
- Format instability：模型返回非法 JSON 或字段类型错误；当前 parser 和 fallback 逻辑会处理该路径。
- Noisy PDF extraction：源 PDF 抽取文本质量差，进而影响检索质量。
- Refusal needed：无关问题应基于证据边界拒答，而不是调用外部常识回答。

更具体的失败案例见 `docs/failure_cases.md`。

## 后续优化方向

下一阶段优先级较高的技术改进包括：

1. 为抽象问题补充 hybrid retrieval 或 rerank。
2. 为局限性、研究空白类问题增加 query rewrite。
3. 将 citation verification 从关键词重合升级为 claim-level support scoring。
4. 增加不依赖外部 LLM API 的评测 fixture。
5. 在依赖和测试稳定后补充 CI。