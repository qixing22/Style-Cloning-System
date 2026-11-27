"""Validate and compile the Style System v1.0 repository format."""

import argparse
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator


SECTIONS = ("style", "character", "environment", "narrative", "mood", "technical")
SLOT = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "style-system.schema.json"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def as_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def check_shape(value, definition=None):
    schema = read_json(SCHEMA_PATH)
    if definition:
        schema = {key: schema[key] for key in ("$schema", "$defs")}
        schema["$ref"] = f"#/$defs/{definition}"
    errors = list(Draft202012Validator(schema).iter_errors(value))
    if errors:
        details = [f"{error.json_path}: {error.message}" for error in errors]
        raise ValueError("\n".join(details))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def index(items, label):
    indexed = {}
    for item in items:
        require(item["id"] not in indexed, f"{label} ID 重复：{item['id']}")
        indexed[item["id"]] = item
    return indexed


def slots_in(text):
    stripped = SLOT.sub("", text)
    require("{{" not in stripped and "}}" not in stripped, f"槽位格式无效：{text}")
    return set(SLOT.findall(text))


def validate_profile(profile):
    references = index(profile["references"], "参考")
    evidence = index(profile["evidence"], "证据")
    rules = index(profile["rules"], "规则")
    for item in evidence.values():
        require(item["reference_id"] in references, f"证据引用不存在：{item['id']}")
        if item["kind"] == "inference":
            basis = item.get("basis_ids", [])
            require(basis and all(key in evidence and evidence[key]["kind"] == "observation"
                                  for key in basis), f"推断缺少可见观察：{item['id']}")
    for rule in rules.values():
        rule_id = rule["id"]
        require(set(rule["evidence_ids"]) <= evidence.keys(), f"规则证据不存在：{rule_id}")
        observations = set()
        for key in rule["evidence_ids"]:
            item = evidence[key]
            observations.update([key] if item["kind"] == "observation" else item["basis_ids"])
        require(any(any(role["role"] == "style_reference"
                        for role in references[evidence[key]["reference_id"]]["roles"])
                    for key in observations), f"档案规则缺少风格参考观察：{rule_id}")
        for field in ("requires", "excludes"):
            related = set(rule[field])
            require(rule_id not in related and related <= rules.keys(),
                    f"规则关联无效：{rule_id}.{field}")
        for field in ("instruction", "check"):
            zh_slots = slots_in(rule[field]["zh"])
            en_slots = slots_in(rule[field]["en"])
            require(zh_slots == en_slots and zh_slots <= profile["slots"].keys(),
                    f"双语槽位不同或未声明：{rule_id}.{field}")
    return rules


def active_rules(profile, task, rules):
    require((task["profile_id"], task["profile_version"]) == (profile["id"], profile["version"]),
            "任务引用的档案 ID 或版本不匹配")
    scope = task["scope_decision"]
    require(scope["status"] == "supported", f"档案适用性未确认：{scope['reason']}")
    require(not any(item["blocking"] for item in task["conflicts"]), "存在阻断冲突")
    conditions = {key for key, rule in rules.items() if rule["variability"] == "conditional"}
    decisions = task["condition_decisions"]
    require(decisions.keys() == conditions, "请为所有条件规则提供明确的启用或排除决定")
    selected = set(task["selected_rule_ids"])
    selectable = {key for key, rule in rules.items() if rule["variability"] != "core"}
    require(selected <= selectable, "selected_rule_ids 引用了不存在的规则或核心规则")
    require(selected & conditions == {key for key, item in decisions.items() if item["enabled"]},
            "已选规则与条件判定不一致")
    active = [rule for key, rule in rules.items() if rule["variability"] == "core" or key in selected]
    active_ids = {rule["id"] for rule in active}
    for rule in active:
        key = rule["id"]
        require(profile["modules"][rule["module"]] == "active", f"规则模块未启用：{key}")
        require(set(rule["requires"]) <= active_ids, f"规则缺少启用的依赖：{key}")
        require(not set(rule["excludes"]) & active_ids, f"启用规则冲突：{key}")
    require(task["bindings"].keys() <= profile["slots"].keys(), "任务包含未声明的槽位绑定")
    if task.get("storyboard"):
        frames = [frame["frame_number"] for frame in task["storyboard"]]
        require(frames == list(range(1, 1 + task["delivery"]["count"])),
                "分镜帧号须按顺序从 1 开始，并与交付数量一致")
    requirements = index(task["requirements"], "任务要求")
    reserved = {"delivery.count", "delivery.aspect_ratio", "delivery.exact_text"}
    require(not reserved & (rules.keys() | requirements.keys()), "规则 ID 与交付检查保留 ID 冲突")
    require(not rules.keys() & requirements.keys(), "任务要求与风格规则的 ID 冲突")
    return active + list(requirements.values())


def render(text, language, bindings):
    def binding(match):
        key = match.group(1)
        require(key in bindings, f"提示词槽位未绑定：{key}")
        return bindings[key][language]

    slots_in(text)
    rendered = SLOT.sub(binding, text)
    require(not slots_in(rendered), f"绑定后仍有提示词槽位：{rendered}")
    return rendered


def project(bundle, language, rules):
    task = bundle["image_task"]
    prompt = {
        "schema_version": "1.0", "language": language,
        "task_id": task["id"], "task_version": task["version"],
        "profile_id": task["profile_id"], "profile_version": task["profile_version"],
        "theme": task["theme"][language], "audience": task["audience"][language],
        "intent": task["intent"][language], "delivery": task["delivery"],
        **{section: [] for section in SECTIONS},
    }
    for key in ("theme", "audience", "intent"):
        require(not slots_in(prompt[key]), f"任务 {key} 包含未绑定槽位")
    for rule in rules:
        value = render(rule["instruction"][language], language, task["bindings"])
        render(rule["check"][language], language, task["bindings"])
        prompt[rule["section"]].append({"id": rule["id"], "priority": rule["priority"], "text": value})
    if task.get("storyboard"):
        prompt["storyboard"] = [
            {key: value if key == "frame_number" else render(value[language], language, task["bindings"])
             for key, value in frame.items()}
            for frame in task["storyboard"]
        ]
    check_shape(prompt, "generation_prompt")
    return prompt


def prompt_text(prompt, compact=False):
    zh = prompt["language"] == "zh"
    delivery = prompt["delivery"]
    labels = ("主题", "受众", "叙事意图", "画幅", "交付数量", "逐字保留以下文案", "分镜") if zh else (
        "Theme", "Audience", "Narrative intent", "Aspect ratio", "Output count", "Preserve this exact text", "Storyboard")
    colon = "：" if zh else ": "
    parts = [f"{label}{colon}{prompt[key]}"
             for label, key in zip(labels[:3], ("theme", "audience", "intent"))]
    included = []
    for section in SECTIONS:
        for clause in prompt[section]:
            if compact and clause["priority"] != "must":
                continue
            parts.append(clause["text"])
            included.append(clause["id"])
    for label, key in ((labels[3], "aspect_ratio"), (labels[4], "count")):
        if delivery[key] is not None:
            parts.append(f"{label}{colon}{delivery[key]}")
    if delivery["exact_text"]:
        # JSON quoting preserves exact Unicode, punctuation and line breaks without translating them.
        parts.append(labels[5] + colon + json.dumps(delivery["exact_text"], ensure_ascii=False))
    for frame in prompt.get("storyboard", []):
        values = (frame[key] for key in ("narrative_function", "relation_to_previous", "shot_type", "angle", "focus"))
        parts.append(f"{labels[6]} {frame['frame_number']}{colon}" + " / ".join(values))
    return ("\n" if compact else "\n\n").join(parts) + "\n", included


def compile_bundle(bundle):
    check_shape(bundle)
    require("image_task" in bundle, "编译需要图像任务")
    profile = bundle["style_profile"]
    task = bundle["image_task"]
    rules = active_rules(profile, task, validate_profile(profile))
    zh, en = (project(bundle, language, rules) for language in ("zh", "en"))
    brief, brief_ids = prompt_text(zh, compact=True)
    english, english_ids = prompt_text(en)
    all_ids = [rule["id"] for rule in rules]
    manifest = {
        "profile_id": profile["id"], "profile_version": profile["version"],
        "task_id": task["id"], "task_version": task["version"],
        "mandatory_ids": [rule["id"] for rule in rules if rule["priority"] == "must"],
        "rule_coverage": {"prompt.zh.json": all_ids, "prompt.en.json": all_ids,
                          "prompt.zh.short.txt": brief_ids, "prompt.en.txt": english_ids},
        "delivery": task["delivery"],
    }
    files = {"prompt.zh.json": as_json(zh), "prompt.en.json": as_json(en),
             "prompt.zh.short.txt": brief, "prompt.en.txt": english,
             "coverage.json": as_json(manifest)}
    return files, rules


def audit_bundle(bundle, rules):
    task, review = bundle["image_task"], bundle["image_review"]
    require((review["task_id"], review["task_version"]) == (task["id"], task["version"]),
            "验收引用的任务 ID 或版本不匹配")
    expected = {rule["id"]: rule["check"]["zh"] for rule in rules if rule["priority"] == "must"}
    expected["delivery.count"] = "核对实际交付数量。"
    if task["delivery"]["aspect_ratio"]:
        expected["delivery.aspect_ratio"] = "核对实际文件宽高比。"
    if task["delivery"]["exact_text"]:
        expected["delivery.exact_text"] = "逐字核对成品文案。"
    checks = index(review["checks"], "验收项")
    known = {rule["id"] for rule in rules} | expected.keys()
    require(checks.keys() <= known, "验收引用未知的规则或交付项")
    phase = review["phase"]
    output_exists = review["output_id"] is not None and review["output_version"] is not None
    if phase == "not_generated":
        absent = review["output_id"] is None and review["output_version"] is None
        require(absent and not checks, "未生成状态应没有产物版本或成图验收项")
    else:
        require(output_exists, "成图验收需要具体产物 ID 和版本")
    if phase == "unreviewed":
        require(not checks, "未审状态应没有成图验收项")
    statuses = {}
    for key, item in checks.items():
        result = item["result"]
        if result != "unknown":
            require(item.get("evidence", "").strip(), f"验收结论缺少证据：{key}")
        require(key not in expected or result != "not_applicable", f"启用的必须项须核验：{key}")
        statuses[key] = result
    result = phase
    if phase == "reviewed":
        mandatory = [statuses.get(key, "unknown") for key in expected]
        result = "fail" if "fail" in mandatory else "pass" if all(x == "pass" for x in mandatory) else "indeterminate"
    return {"status": result, "task_id": task["id"], "output_id": review["output_id"],
            "mandatory": [{"id": key, "check": render(check, "zh", task["bindings"]),
                           "result": statuses.get(key, "unknown")} for key, check in expected.items()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("validate", "compile", "audit"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, help="compile 的新输出目录")
    args = parser.parse_args()
    try:
        bundle = read_json(args.input)
        check_shape(bundle)
        validate_profile(bundle["style_profile"])
        if args.mode == "compile":
            require(args.out is not None, "compile 需要 --out")
            files, _ = compile_bundle(bundle)
            args.out.mkdir(parents=True, exist_ok=False)
            for name, content in files.items():
                (args.out / name).write_text(content, encoding="utf-8")
            print(args.out)
        elif args.mode == "audit":
            require("image_review" in bundle, "audit 需要图像验收记录")
            _, rules = compile_bundle(bundle)
            print(as_json(audit_bundle(bundle, rules)), end="")
        else:
            if "image_task" in bundle:
                _, rules = compile_bundle(bundle)
                if "image_review" in bundle:
                    audit_bundle(bundle, rules)
            else:
                require("image_review" not in bundle, "验收记录缺少对应任务")
            print("结构与规则引用通过")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
