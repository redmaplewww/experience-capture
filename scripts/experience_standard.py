from __future__ import annotations

import json
from typing import Any

SCHEMA_VERSION = "experience-standard/v1"
ITEM_BASIS = {"explicit", "inferred"}
PRIMARY_TYPES = {
    "principle", "decision_rule", "procedure", "diagnostic",
    "failure_pattern", "constraint", "preference", "fact", "heuristic"
}

SYSTEM_PROMPT = """你是通用经验结构化器。你的任务不是扩写知识，而是把人类自然语言中的经验拆清楚。

必须遵守：
1. 只输出一个 JSON 对象，不要输出 Markdown。
2. 原文明确表达的内容，basis=explicit；为使经验可执行而合理推导的内容，basis=inferred。
3. 不知道的内容留空并放进 knowledge_gaps，不得补造专业事实、案例或证据。
4. 每条经验都要回答：什么场景、解决什么问题、依据什么判断、应当怎么做、何时不适用、如何判断结果。
5. 标签要使用便于检索的短语；允许多个领域和跨领域标签。
6. confidence 是对“结构化结果忠于原文”的置信度，不是对经验本身绝对正确性的判断。

输出结构严格使用下面这些字段：
{
  "schema_version": "experience-standard/v1",
  "source": {"raw_text": "", "language": "zh-CN", "source_type": "human_explicit"},
  "identity": {
    "title": "",
    "summary": "",
    "primary_type": "principle|decision_rule|procedure|diagnostic|failure_pattern|constraint|preference|fact|heuristic",
    "secondary_types": []
  },
  "situation": {"goal": [], "triggers": [], "context": [], "entities": []},
  "guidance": {
    "principles": [],
    "decision_rules": [{"when": [], "then": [], "because": []}],
    "steps": [],
    "avoid": []
  },
  "applicability": {"conditions": [], "prerequisites": [], "exceptions": [], "boundaries": []},
  "outcome": {"expected": [], "success_signals": [], "failure_signals": []},
  "evidence": {"observations": [], "counterexamples": [], "validation_methods": [], "confidence": 0.0},
  "indexing": {"domains": [], "tasks": [], "tags": [], "aliases": [], "cross_domain_links": []},
  "knowledge_gaps": [{"question": "", "why_needed": ""}]
}

除 title、summary、分类、标签和 knowledge_gaps 外，数组中的每一项必须是：
{"text": "具体内容", "basis": "explicit|inferred", "confidence": 0.0}
decision_rules 中的 when、then、because 也使用这种条目。没有内容时返回空数组。"""


def item(text: str, basis: str = "explicit", confidence: float = 1.0) -> dict[str, Any]:
    return {"text": text, "basis": basis, "confidence": confidence}


def empty_record(raw_text: str = "") -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {"raw_text": raw_text, "language": "zh-CN", "source_type": "human_explicit"},
        "identity": {"title": "", "summary": "", "primary_type": "principle", "secondary_types": []},
        "situation": {"goal": [], "triggers": [], "context": [], "entities": []},
        "guidance": {"principles": [], "decision_rules": [], "steps": [], "avoid": []},
        "applicability": {"conditions": [], "prerequisites": [], "exceptions": [], "boundaries": []},
        "outcome": {"expected": [], "success_signals": [], "failure_signals": []},
        "evidence": {"observations": [], "counterexamples": [], "validation_methods": [], "confidence": 0.0},
        "indexing": {"domains": [], "tasks": [], "tags": [], "aliases": [], "cross_domain_links": []},
        "knowledge_gaps": [],
    }


def parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("model_output_must_be_object")
    return value


def validate_record(record: dict[str, Any], raw_text: str) -> list[str]:
    errors: list[str] = []
    required = ["schema_version", "source", "identity", "situation", "guidance", "applicability", "outcome", "evidence", "indexing", "knowledge_gaps"]
    for key in required:
        if key not in record:
            errors.append(f"missing:{key}")
    if errors:
        return errors
    if record["schema_version"] != SCHEMA_VERSION:
        errors.append("invalid:schema_version")
    if not isinstance(record["source"], dict) or record["source"].get("raw_text") != raw_text:
        errors.append("invalid:source.raw_text")
    if not isinstance(record["identity"], dict) or record["identity"].get("primary_type") not in PRIMARY_TYPES:
        errors.append("invalid:identity.primary_type")
    for field in ("title", "summary"):
        if not isinstance(record.get("identity", {}).get(field), str) or not record["identity"][field].strip():
            errors.append(f"invalid:identity.{field}")
    confidence = record["evidence"].get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append("invalid:evidence.confidence")

    item_paths = {
        "situation": ["goal", "triggers", "context", "entities"],
        "guidance": ["principles", "steps", "avoid"],
        "applicability": ["conditions", "prerequisites", "exceptions", "boundaries"],
        "outcome": ["expected", "success_signals", "failure_signals"],
        "evidence": ["observations", "counterexamples", "validation_methods"],
    }
    required_fields = {
        **item_paths,
        "guidance": ["principles", "decision_rules", "steps", "avoid"],
        "indexing": ["domains", "tasks", "tags", "aliases", "cross_domain_links"],
    }
    for section, fields in required_fields.items():
        value = record.get(section)
        if not isinstance(value, dict):
            errors.append(f"invalid:{section}")
            continue
        for field in fields:
            if field not in value:
                errors.append(f"missing:{section}.{field}")

    def check_item(value: Any, path: str) -> None:
        if not isinstance(value, dict) or not isinstance(value.get("text"), str) or not value["text"].strip():
            errors.append(f"invalid:{path}.text")
            return
        if value.get("basis") not in ITEM_BASIS:
            errors.append(f"invalid:{path}.basis")
        score = value.get("confidence")
        if not isinstance(score, (int, float)) or not 0 <= score <= 1:
            errors.append(f"invalid:{path}.confidence")

    for section, fields in item_paths.items():
        for field in fields:
            values = record.get(section, {}).get(field, [])
            if not isinstance(values, list):
                errors.append(f"invalid:{section}.{field}")
                continue
            for index, value in enumerate(values):
                check_item(value, f"{section}.{field}[{index}]")

    rules = record.get("guidance", {}).get("decision_rules", [])
    if not isinstance(rules, list):
        errors.append("invalid:guidance.decision_rules")
    else:
        for rule_index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                errors.append(f"invalid:guidance.decision_rules[{rule_index}]")
                continue
            for field in ("when", "then", "because"):
                values = rule.get(field)
                if not isinstance(values, list):
                    errors.append(f"invalid:guidance.decision_rules[{rule_index}].{field}")
                    continue
                for item_index, value in enumerate(values):
                    check_item(value, f"guidance.decision_rules[{rule_index}].{field}[{item_index}]")

    for field in ("domains", "tasks", "tags", "aliases", "cross_domain_links"):
        values = record.get("indexing", {}).get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"invalid:indexing.{field}")

    gaps = record.get("knowledge_gaps")
    if not isinstance(gaps, list):
        errors.append("invalid:knowledge_gaps")
    else:
        for index, gap in enumerate(gaps):
            if not isinstance(gap, dict) or not isinstance(gap.get("question"), str) or not gap["question"].strip() or not isinstance(gap.get("why_needed"), str):
                errors.append(f"invalid:knowledge_gaps[{index}]")
    return errors


def render_markdown(record: dict[str, Any]) -> str:
    def texts(section: str, field: str) -> list[str]:
        return [x.get("text", "") for x in record.get(section, {}).get(field, []) if isinstance(x, dict) and x.get("text")]

    def block(title: str, values: list[str]) -> list[str]:
        return [f"## {title}", *(f"- {value}" for value in values), ""] if values else []

    identity = record.get("identity", {})
    lines = [f"# {identity.get('title', '未命名经验')}", "", identity.get("summary", ""), ""]
    lines += block("适用场景", texts("situation", "context") + texts("situation", "triggers"))
    lines += block("核心原则", texts("guidance", "principles"))
    rules = []
    for rule in record.get("guidance", {}).get("decision_rules", []):
        when = "；".join(x.get("text", "") for x in rule.get("when", []))
        then = "；".join(x.get("text", "") for x in rule.get("then", []))
        because = "；".join(x.get("text", "") for x in rule.get("because", []))
        rules.append(f"当 {when or '条件满足'} 时，{then or '采取相应行动'}" + (f"。依据：{because}" if because else ""))
    lines += block("判断规则", rules)
    lines += block("建议步骤", texts("guidance", "steps"))
    lines += block("适用条件", texts("applicability", "conditions") + texts("applicability", "prerequisites"))
    lines += block("边界与例外", texts("applicability", "exceptions") + texts("applicability", "boundaries"))
    lines += block("预期结果", texts("outcome", "expected") + texts("outcome", "success_signals"))
    gaps = [x.get("question", "") for x in record.get("knowledge_gaps", []) if isinstance(x, dict) and x.get("question")]
    lines += block("仍需确认", gaps)
    tags = record.get("indexing", {}).get("tags", [])
    if tags:
        lines += ["## 检索标签", "", "、".join(tags), ""]
    return "\n".join(lines).strip() + "\n"
