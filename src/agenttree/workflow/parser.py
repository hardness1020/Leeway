"""Parse workflow definitions from YAML or JSON files."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from agenttree.workflow.types import WorkflowDefinition


def parse_workflow(path: Path) -> WorkflowDefinition:
    """Load and validate a workflow definition from a YAML or JSON file."""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        raw = yaml.safe_load(text)
    elif suffix == ".json":
        raw = json.loads(text)
    else:
        raise ValueError(f"Unsupported workflow file format: {suffix} (expected .yaml/.yml/.json)")

    if not isinstance(raw, dict):
        raise ValueError(f"Workflow file must be a mapping, got {type(raw).__name__}")

    return WorkflowDefinition.model_validate(raw)
