# 独立盲测协议

## 角色隔离

1. 出题人填写 `blind_questions.csv`，只写真实科研问题、类别和难度。
2. 标注人不运行当前系统，阅读原文后填写 `blind_gold.csv`。
3. 开发者仅在两份文件完成后运行冻结脚本；冻结前不得查看问题并针对性改代码。
4. 冻结后先保存代码版本和配置，再运行检索及 Groundedness；错误不能通过覆盖原报告消失。

最低30题，建议包含10条自然改写、8条跨论文比较、6条多条件问题和6条
无答案/歧义问题。`relevant_paper_ids`、`relevant_chunk_ids`和多项声明使用英文
分号分隔。拒答题的`relevant_paper_ids`必须为空。每条Gold必须由标注人将
`evidence_reviewed`设为`true`。

```powershell
.\.venv\Scripts\python.exe scripts\freeze_blind_eval.py
```

冻结结果保存到`docs/eval/frozen/`，文件名包含内容SHA-256前12位。同一内容
不能再次覆盖写入。运行评测时将冻结JSONL传给`--questions`参数。
