#!/usr/bin/env python3
"""
JSON Configuration Merge Tool
Merges base.json with instance.json, instance values override base values.
"""

import json
import sys
from typing import Any, Dict
from pathlib import Path


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries. Override values take precedence."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def merge_json(base_path: str, override_path: str, output_path: str):
    """Merge two JSON files and write the result."""
    with open(base_path, 'r', encoding='utf-8') as f:
        base = json.load(f)
    
    override = {}
    if Path(override_path).exists():
        with open(override_path, 'r', encoding='utf-8') as f:
            override = json.load(f)
    
    result = deep_merge(base, override)
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Merged config written to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <base.json> <override.json> <output.json>")
        sys.exit(1)
    
    merge_json(sys.argv[1], sys.argv[2], sys.argv[3])
