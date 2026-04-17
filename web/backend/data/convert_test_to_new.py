#!/usr/bin/env python3
"""
Transform queries_store_test.json to queries_store_new.json format.
Converts hierarchical structure (evidence nested in queries) to normalized structure
(evidence stored separately at top level).
"""

import json
import sys
from pathlib import Path


def transform_data(input_data):
    """Transform from test format to new format."""
    output = {
        "queries": [],
        "evidences": []
    }

    evidence_map = {}

    for query in input_data.get("queries", []):
        query_id = query["id"]
        evidence_ids = []

        for evidence in query.get("evidences", []):
            evidence_id = evidence["id"]
            evidence_ids.append(evidence_id)

            new_evidence = {
                "id": evidence["id"],
                "content": evidence["content"],
                "queries": [{"id": query_id}],
                "speaker": evidence["speaker"],
                "constraints": evidence["constraints"],
                "target_dia_id": evidence["target_dia_id"],
                "session_key": evidence["session_key"],
                "status": evidence["status"],
                "created_at": evidence["created_at"]
            }

            evidence_map[evidence_id] = new_evidence

        new_query = {
            "id": query["id"],
            "query_text": query["query_text"],
            "sample_id": query["sample_id"],
            "protagonist": query["protagonist"],
            "status": query["status"],
            "created_at": query["created_at"],
            "evidences": evidence_ids
        }

        output["queries"].append(new_query)

    polished_messages = []
    for msg in input_data.get("polished_messages", []):
        new_msg = {
            "sample_id": msg["sample_id"],
            "dia_id": msg["dia_id"],
            "session_key": msg["session_key"],
            "original_text": msg["original_text"],
            "final_polished_text": msg["final_polished_text"],
            "evidence_items": []
        }

        for item in msg.get("evidence_items", []):
            new_item = {
                "evidence": {
                    "id": item["evidence"]["id"],
                    "content": item["evidence"]["content"]
                }
            }
            new_msg["evidence_items"].append(new_item)

        new_msg["updated_at"] = msg["updated_at"]
        polished_messages.append(new_msg)

    def sort_key(dia_id):
        parts = dia_id.split(':')
        return (int(parts[0][1:]), int(parts[1]))

    evidences_list = sorted(evidence_map.values(), key=lambda e: sort_key(e['target_dia_id']))
    polished_messages_sorted = sorted(polished_messages, key=lambda m: sort_key(m['dia_id']), reverse=True)

    output["evidences"] = evidences_list
    output["polished_messages"] = polished_messages_sorted

    return output


def main():
    script_dir = Path(__file__).parent
    input_file = script_dir / "queries_store_test.json"
    output_file = script_dir / "queries_store_new.json"

    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])

    print(f"Reading from: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    output_data = transform_data(input_data)

    print(f"Writing to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Transformation complete!")
    print(f"  Queries: {len(output_data['queries'])}")
    print(f"  Evidences: {len(output_data['evidences'])}")


if __name__ == "__main__":
    main()
