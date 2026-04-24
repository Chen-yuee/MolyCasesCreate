"""
将 back4.21.json 中 polished_messages 的 final_polished_text 按
(sample_id, session_key, dia_id) 回灌到 locomo10_CN_remapped.json
对应 sample 的 conversation 中,并为每个 target sample 单独产出一个 JSON 文件。
"""
import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def build_session_index(conversation):
    index = {}
    for key, val in conversation.items():
        if not key.startswith("session_") or key.endswith("_date_time"):
            continue
        if not isinstance(val, list):
            continue
        for item in val:
            dia_id = item.get("dia_id")
            if dia_id is None:
                continue
            index[(key, dia_id)] = item
    return index


def prune_orphan_date_times(conversation):
    """删除没有对应 session_X 内容列表的 session_X_date_time 键。"""
    content_sessions = {
        k for k, v in conversation.items()
        if k.startswith("session_") and not k.endswith("_date_time") and isinstance(v, list)
    }
    for key in list(conversation.keys()):
        if key.endswith("_date_time") and key.replace("_date_time", "") not in content_sessions:
            del conversation[key]


def apply_for_sample(sid, sample, messages):
    sample = copy.deepcopy(sample)
    prune_orphan_date_times(sample["conversation"])
    index = build_session_index(sample["conversation"])

    total = len(messages)
    replaced = skipped = mismatched = missing = 0

    for msg in messages:
        key = (msg["session_key"], msg["dia_id"])
        item = index.get(key)
        if item is None:
            missing += 1
            print(f"  [missing] sid={sid} {key}")
            continue

        current = item.get("text", "")
        original = msg["original_text"]
        polished = msg["final_polished_text"]

        if current == original:
            item["text"] = polished
            replaced += 1
        elif current == polished:
            skipped += 1
        else:
            mismatched += 1
            print(
                f"  [mismatch] sid={sid} {key}\n"
                f"    current : {current[:60]}\n"
                f"    original: {original[:60]}"
            )

    return sample, {
        "total": total,
        "replaced": replaced,
        "skipped": skipped,
        "mismatched": mismatched,
        "missing": missing,
    }


def parse_targets(s):
    return [int(x) for x in s.split(",") if x.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--back", type=Path, default=REPO_ROOT / "data/4.22/back4.21.json")
    parser.add_argument("--remapped", type=Path, default=REPO_ROOT / "data/4.22/locomo10_CN_remapped.json")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "data/4.22")
    parser.add_argument("--targets", type=parse_targets, default=[0, 3, 6])
    args = parser.parse_args()

    with open(args.back, "r", encoding="utf-8") as f:
        back = json.load(f)
    with open(args.remapped, "r", encoding="utf-8") as f:
        remapped = json.load(f)

    groups = defaultdict(list)
    for m in back.get("polished_messages", []):
        groups[m["sample_id"]].append(m)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    overall = {"total": 0, "replaced": 0, "skipped": 0, "mismatched": 0, "missing": 0}

    for sid in args.targets:
        if not (0 <= sid < len(remapped)):
            print(f"[skip] sample_id={sid} 越界 (remapped 长度 {len(remapped)})")
            continue

        messages = groups.get(sid, [])
        sample, stats = apply_for_sample(sid, remapped[sid], messages)

        out_path = args.out_dir / f"locomo10_CN_remapped_polished_sample{sid}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)

        rel = out_path.relative_to(REPO_ROOT)
        print(
            f"sample_id={sid} "
            f"total={stats['total']} replaced={stats['replaced']} "
            f"skipped={stats['skipped']} mismatched={stats['mismatched']} "
            f"missing={stats['missing']} -> {rel}"
        )
        for k in overall:
            overall[k] += stats[k]

    print(
        f"overall: total={overall['total']} replaced={overall['replaced']} "
        f"skipped={overall['skipped']} mismatched={overall['mismatched']} "
        f"missing={overall['missing']}"
    )


if __name__ == "__main__":
    main()
