import os
import json
import requests
import argparse
import pandas as pd
from tqdm import tqdm


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, default="source.csv")
    return parser.parse_args()


def prefetch(concept, field, level):
    level_list = [
        "Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"
    ]
    with open("heuristics.txt", "r+") as f:
        heuristic_list = f.readlines()

    # step 1: prefetch knowledge component
    knowledge_result = requests.post(
        url="http://18.206.229.27:8000/tree/create_knowledge_component",
        data=json.dumps({
            "concept": concept,
            "field": field,
            "level": level,
            "cache": "true"
        }),
        timeout=60)
    knowledge_text = json.loads(knowledge_result.text)["data"]["knowledge"]
    print("[Knowledge]")
    # step 2: prefetch knowledge graph
    graph_result = requests.post(
        url="http://18.206.229.27:8000/tree/create_knowledge_graph",
        data=json.dumps({
            "concepts": [concept],
            "field": field,
            "knowledge": knowledge_text,
            "cache": "true"
        }),
        timeout=60)
    graph_text = json.loads(graph_result.text)["data"]["graph"]
    print("[Graph]")
    # step 3: prefetch key statement
    key_candidates = []
    for relation in tqdm(graph_text, desc="[Key]"):
        key_result = requests.post(
            url="http://18.206.229.27:8000/tree/create_key_statement",
            data=json.dumps({
                "source": relation["source"],
                "target": relation["target"],
                "label": relation["relation"],
                "cache": "true"
            }),
            timeout=60)
        try:
            key_text = json.loads(key_result.text)["data"]["key"]
            key_candidates.append(key_text)
        except ValueError:
            continue
    # step 4: prefetch distractor statement
    distractor_candidates = []
    for relation in tqdm(graph_text, desc="[Distractor]"):
        for template in tqdm(heuristic_list, desc="[Heuristics]"):
            distractor_result = requests.post(
                url=
                "http://18.206.229.27:8000/tree/create_distractor_statement",
                data=json.dumps({
                    "source": relation["source"],
                    "target": relation["target"],
                    "label": relation["relation"],
                    "template": template,
                    "cache": "true"
                }),
                timeout=60)
            try:
                distractor_list = json.loads(
                    distractor_result.text)["data"]["distractors"]
                for distractor in distractor_list:
                    distractor_candidates.append(distractor)
            except ValueError:
                continue
    # step 5: prefetch question
    question_list = []
    for question_level in tqdm(level_list, desc="[Question]"):
        question_result = requests.post(
            url="http://18.206.229.27:8000/tree/create_question",
            data=json.dumps({
                "concept": concept,
                "field": field,
                "level": question_level,
                "type": "Multi-Choice",
                "keys": [],
                "distractors": [],
                "cache": "true"
            }),
            timeout=60)
        try:
            question_text = json.loads(question_result.text)["data"]
            question_list.append(question_text)
        except ValueError:
            continue


def main():
    args = parse_args()
    source = pd.read_csv(args.path)
    for _, row in source.iterrows():
        concept = row["concept"]
        field = row["field"]
        level = row["level"]
        print(f"prefetch: {concept} {field} {level}")
        prefetch(row["concept"], row["field"], row["level"])


if __name__ == '__main__':
    main()