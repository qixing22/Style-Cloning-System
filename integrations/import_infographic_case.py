"""Read a pinned Infographic-Design case and build a compilable style task."""

import argparse
import csv
import io
import json
from pathlib import Path
import subprocess
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_at_commit(repo, commit, path):
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        capture_output=True, encoding="utf-8", check=False,
    )
    if result.returncode:
        raise ValueError(f"无法读取来源快照 {commit}:{path}。请确认检出含该提交。\n{result.stderr.strip()}")
    return result.stdout


def bilingual(zh, en):
    return {"zh": zh, "en": en}


def requirement(key, category, section, instruction, check):
    return {"id": key, "category": category, "priority": "must",
            "section": section, "instruction": instruction, "check": check}


def import_case(repo, case_id):
    integration = read_json(ROOT / "integrations" / "infographic-design.json")
    case = integration["cases"].get(case_id)
    if case is None:
        raise ValueError(f"没有登记的案例：{case_id}")
    commit = integration["source_commit"]
    analysis_path = f"{case['directory']}/{case['analysis']}"
    data_path = f"{case['directory']}/{case['data']}"
    directory_url = f"https://github.com/{integration['source_repo']}/blob/{commit}/{quote(case['directory'])}"

    analysis = read_at_commit(repo, commit, analysis_path)
    data = read_at_commit(repo, commit, data_path)
    reader = csv.DictReader(io.StringIO(data.lstrip("\ufeff")))
    required = {"record_id", "item_name", "value", "unit", "evidence_status"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("案例数据缺少必需列")
    rows = {}
    for row in reader:
        key = row["record_id"]
        if not key or key in rows:
            raise ValueError("案例记录 ID 缺失或重复")
        rows[key] = row
    for skipped in case["omissions"]:
        if skipped not in rows:
            raise ValueError(f"排除记录不存在：{skipped}")
    titles = []
    for key in case["records"]:
        row = rows.get(key)
        if row is None or not (row["item_name"] or "").strip():
            raise ValueError(f"记录不存在或无有效标签：{key}")
        if row["evidence_status"] != "visible_label_or_structure" or row["value"] or row["unit"]:
            raise ValueError(f"顺序型案例含不同证据或度量，须重新核对：{key}")
        titles.append(row["item_name"])
    if not titles or len(set(titles)) != len(titles):
        raise ValueError("案例必须提供互不重复的有效标签")

    title = case["topic"]["en"]
    labels = " → ".join(titles)
    count = len(titles)
    bundle = read_json(ROOT / "library" / "profiles" / "voxel-editorial.v1.json")
    profile = bundle["style_profile"]
    analysis_url = f"{directory_url}/{quote(case['analysis'])}"
    bundle["image_task"] = {
        "id": f"{case_id.lower()}-voxel",
        "version": 1,
        "profile_id": profile["id"],
        "profile_version": profile["version"],
        "mode": "change",
        "scope_decision": {"status":"supported","reason":"案例可按顺序编码为等体量的三维层。"},
        "theme": case["topic"],
        "audience": bilingual("希望读懂产业过程的普通读者。", "General readers learning about the production process."),
        "intent": bilingual("从上到下读懂环节顺序。", "Read the supply-chain sequence from top to bottom."),
        "bindings": {"layer_subjects":bilingual("相应设施或环节的标志性物件", "icons of the facilities or activities at each stage")},
        "selected_rule_ids": [],
        "condition_decisions": {"R06":{"enabled":False,"reason":"案例有顺序与标签，未提供可比较的数值或单位。"}},
        "requirements": [
            requirement("T-01","content","character",
                bilingual(f"按源记录的顺序展示 {count} 层：{labels}。", f"Use {count} modules in the source order: {labels}."),
                bilingual("逐层核对标注与阶段顺序。","Check each stage label and its order.")),
            requirement("T-02","presentation","technical",
                bilingual("所有层采用相当的体量，以顺序表达流程。把数值徽章改为两侧的阶段标签，保留清楚的连线。",
                          "Use modules of comparable volume to encode the sequence. Connect stage labels in each gutter with clear leaders."),
                bilingual("检查各层均不暗示定量大小，也没有未经证实的数值或图例。","Verify that the modules do not imply quantities and that no unsupported values or legends appear.")),
        ],
        "delivery": {"aspect_ratio":"1:2","count":1,"exact_text":[title,*titles]},
        "conflicts": [],
    }
    sources = {
        "case_id": case_id, "repository": integration["source_repo"], "commit": commit,
        "analysis_url": analysis_url, "data_url": f"{directory_url}/{quote(case['data'])}",
        "reference_image_url": f"{directory_url}/{quote(case['image'])}",
        "analysis_title": analysis.splitlines()[0].lstrip("# "),
        "records": case["records"], "omissions": case["omissions"],
        "encoding": "ordered_stages", "role": "content_reference",
    }
    return bundle, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="信息图形知识库的本地检出")
    parser.add_argument("--case", required=True, help="案例 ID，例如 CASE-17")
    parser.add_argument("--out", type=Path, required=True, help="尚不存在的输出目录")
    args = parser.parse_args()
    try:
        bundle, sources = import_case(args.repo, args.case)
        args.out.mkdir(parents=True, exist_ok=False)
        for name, data in (("task.json",bundle),("sources.json",sources)):
            (args.out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(args.out)


if __name__ == "__main__":
    main()
