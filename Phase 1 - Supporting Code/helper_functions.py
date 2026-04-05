
import json
from typing import Dict, List, Set, Any

def load_tips_training_mapping(path: str = "tips_training_mapping.json") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    return mapping

def infer_elements_from_tags(detected_tags: List[str], mapping: Dict[str, Any], min_tag_hits: int = 1) -> List[Dict[str, Any]]:
    detected_set: Set[str] = set(detected_tags)
    results: List[Dict[str, Any]] = []

    for element_name, info in mapping.items():
        element_tags = info.get("tags", [])
        training_items = info.get("training_items", [])
        matched_tags = [t for t in element_tags if t in detected_set]

        if len(matched_tags) >= min_tag_hits:
            results.append({
                "element_name": element_name,
                "matched_tags": matched_tags,
                "training_items": training_items,
            })

    return results
