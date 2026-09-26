import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from experience_standard import SCHEMA_VERSION, empty_record, item, render_markdown, validate_record


raw = "仿真中本构的选择要根据材料、损伤预期来决定，断裂和拉伸用的本构是不一样的。"
record = empty_record(raw)
record["identity"] = {
    "title": "依据材料与损伤预期选择本构",
    "summary": "仿真本构应匹配材料及预期损伤模式，拉伸与断裂场景不能默认共用同一套本构描述。",
    "primary_type": "decision_rule",
    "secondary_types": ["principle"],
}
record["situation"]["context"] = [item("进行材料仿真并选择本构模型")]
record["guidance"]["principles"] = [item("本构选择需要同时考虑材料和预期损伤模式")]
record["guidance"]["decision_rules"] = [{
    "when": [item("预期响应从拉伸变化为断裂")],
    "then": [item("重新选择或校核所用本构", "inferred", 0.85)],
    "because": [item("拉伸和断裂使用的本构并不相同")],
}]
record["evidence"]["confidence"] = 0.96
record["indexing"] = {
    "domains": ["工程仿真", "材料力学"],
    "tasks": ["本构选择"],
    "tags": ["本构模型", "材料", "损伤", "断裂", "拉伸"],
    "aliases": [],
    "cross_domain_links": [],
}
record["knowledge_gaps"] = [{"question": "具体材料、载荷和损伤模型是什么？", "why_needed": "决定可选本构及标定方法"}]

assert record["schema_version"] == SCHEMA_VERSION
assert validate_record(record, raw) == []
markdown = render_markdown(record)
assert "核心原则" in markdown and "仍需确认" in markdown

example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples", "constitutive-model-selection.v1.json")
with open(example_path, encoding="utf-8") as example_file:
    example = json.load(example_file)
assert validate_record(example, example["source"]["raw_text"]) == []
print("experience standard: PASS")
