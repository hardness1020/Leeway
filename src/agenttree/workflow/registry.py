"""Workflow discovery and registry."""

from __future__ import annotations

import logging
from pathlib import Path

from agenttree.config.paths import get_config_dir
from agenttree.workflow.parser import parse_workflow
from agenttree.workflow.types import WorkflowDefinition

logger = logging.getLogger(__name__)


class WorkflowRegistry:
    """Store discovered workflow definitions by name."""

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        self._workflows[workflow.name] = workflow

    def get(self, name: str) -> WorkflowDefinition | None:
        return self._workflows.get(name)

    def list_workflows(self) -> list[WorkflowDefinition]:
        return sorted(self._workflows.values(), key=lambda w: w.name)


def get_user_workflows_dir() -> Path:
    """Return ``~/.agenttree/workflows/``, creating it if needed."""
    path = get_config_dir() / "workflows"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_workflow_registry(cwd: str | Path | None = None) -> WorkflowRegistry:
    """Discover workflow YAML/JSON files from user and project directories."""
    registry = WorkflowRegistry()

    # User-level: ~/.agenttree/workflows/*.yaml
    _scan_dir(get_user_workflows_dir(), registry)

    # Project-level: <cwd>/.agenttree/workflows/*.yaml
    if cwd is not None:
        project_dir = Path(cwd).resolve() / ".agenttree" / "workflows"
        if project_dir.is_dir():
            _scan_dir(project_dir, registry)

    return registry


def _scan_dir(directory: Path, registry: WorkflowRegistry) -> None:
    """Load all workflow files from *directory* into *registry*."""
    for pattern in ("*.yaml", "*.yml", "*.json"):
        for path in sorted(directory.glob(pattern)):
            try:
                workflow = parse_workflow(path)
                registry.register(workflow)
            except Exception as exc:
                logger.warning("Skipping invalid workflow %s: %s", path, exc)
