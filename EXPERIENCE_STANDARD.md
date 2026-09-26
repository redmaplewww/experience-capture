# 通用经验标准结构 V1

本标准只解决一件事：把人类自然语言中的经验，转换为可读、可检查、可供后续系统使用的结构化记录。它不规定数据库、向量模型或检索系统。

## 核心原则

1. 保留原文，不用结构化结果替代人的原始表达。
2. 明确区分原文明示内容与模型合理推导内容。
3. 不确定的信息进入 `knowledge_gaps`，不能由模型静默补造。
4. 经验至少要能说明场景、问题、判断、行动、边界和结果。
5. 分类和标签允许跨领域，不能强迫经验只属于一个领域。

## 顶层结构

| 字段 | 含义 |
|---|---|
| `schema_version` | 固定为 `experience-standard/v1` |
| `source` | 原始文本、语言和来源类型 |
| `identity` | 标题、摘要和经验类型 |
| `situation` | 目标、触发条件、上下文和涉及对象 |
| `guidance` | 原则、判断规则、步骤和应避免的行动 |
| `applicability` | 适用条件、前置条件、例外和边界 |
| `outcome` | 预期结果、成功信号和失败信号 |
| `evidence` | 观察、反例、验证方式和结构化置信度 |
| `indexing` | 领域、任务、标签、别名和跨领域关联 |
| `knowledge_gaps` | 当前经验仍缺失、需要向人追问的信息 |

## 内容条目

除标题、摘要、分类、标签和待确认问题外，每条内容使用统一形态：

```json
{
  "text": "具体内容",
  "basis": "explicit",
  "confidence": 0.95
}
```

- `explicit`：人类原文直接表达。
- `inferred`：为了让经验可执行而做出的合理推导。
- `confidence`：该条结构化内容忠于原文的程度，不代表经验在现实中绝对正确。

## 经验类型

- `principle`：原则
- `decision_rule`：判断或选择规则
- `procedure`：操作流程
- `diagnostic`：诊断经验
- `failure_pattern`：失败模式
- `constraint`：约束
- `preference`：个人或组织偏好
- `fact`：事实性经验
- `heuristic`：启发式规则

一个经验使用一个 `primary_type`，同时可以有多个 `secondary_types`。

## 判断规则

判断规则使用 `when / then / because`：

```json
{
  "when": [{"text": "预期发生断裂", "basis": "explicit", "confidence": 0.98}],
  "then": [{"text": "重新选择或校核本构", "basis": "inferred", "confidence": 0.85}],
  "because": [{"text": "断裂和拉伸使用的本构不同", "basis": "explicit", "confidence": 0.98}]
}
```

这使经验能进一步转换为 Agent 的决策条件，同时保留推导边界。

## 当前验收标准

一次结构化结果只有满足以下条件才算成功：

- 原始文本原样保留；
- 所有必需顶层字段存在；
- 经验类型属于标准枚举；
- 所有内容条目具有 `text`、`basis` 和 `confidence`；
- `basis` 只能是 `explicit` 或 `inferred`；
- 未知信息进入 `knowledge_gaps`；
- 同时输出标准 JSON 和人可读经验卡。
