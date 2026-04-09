"""Tests for skill registry and discovery."""

from pathlib import Path

from leeway.skills.registry import SkillRegistry, _parse_skill_file, load_skill_registry
from leeway.skills.types import SkillDefinition


def test_parse_skill_with_frontmatter(tmp_path: Path):
    md = tmp_path / "review.md"
    md.write_text(
        "---\nname: code-review\ndescription: Review code changes\n---\n"
        "Review the code for correctness and style."
    )
    skill = _parse_skill_file(md, "user")
    assert skill is not None
    assert skill.name == "code-review"
    assert skill.description == "Review code changes"
    assert "Review the code" in skill.content
    assert skill.source == "user"


def test_parse_skill_without_frontmatter(tmp_path: Path):
    md = tmp_path / "simple.md"
    md.write_text("Just some instructions for the agent.")
    skill = _parse_skill_file(md, "project")
    assert skill is not None
    assert skill.name == "simple"
    assert skill.description == ""
    assert "Just some instructions" in skill.content


def test_parse_empty_skill(tmp_path: Path):
    md = tmp_path / "empty.md"
    md.write_text("---\nname: empty\n---\n")
    skill = _parse_skill_file(md, "user")
    assert skill is None


def test_registry_operations():
    registry = SkillRegistry()
    skill = SkillDefinition(name="test", content="Test content")
    registry.register(skill)
    assert registry.get("test") is not None
    assert registry.get("missing") is None
    assert len(registry.list_skills()) == 1


def test_project_overrides_user(tmp_path: Path):
    user_dir = tmp_path / "user" / "skills"
    user_dir.mkdir(parents=True)
    (user_dir / "fix.md").write_text("---\nname: fix\n---\nUser fix instructions")

    project_dir = tmp_path / "project" / ".leeway" / "skills"
    project_dir.mkdir(parents=True)
    (project_dir / "fix.md").write_text("---\nname: fix\n---\nProject fix instructions")

    registry = SkillRegistry()
    from leeway.skills.registry import _scan_directory

    _scan_directory(user_dir, "user", registry)
    _scan_directory(project_dir, "project", registry)

    skill = registry.get("fix")
    assert skill is not None
    assert "Project fix" in skill.content
    assert skill.source == "project"


def test_load_skill_registry(tmp_path: Path):
    skills_dir = tmp_path / ".leeway" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "debug.md").write_text("---\nname: debug\ndescription: Debug help\n---\nDebug steps.")

    registry = load_skill_registry(tmp_path)
    assert registry.get("debug") is not None


def test_frontmatter_extra_metadata(tmp_path: Path):
    md = tmp_path / "tagged.md"
    md.write_text("---\nname: tagged\ntags: [python, testing]\n---\nContent here.")
    skill = _parse_skill_file(md, "user")
    assert skill is not None
    assert skill.metadata.get("tags") == ["python", "testing"]


# ── Folder-per-skill tests ──────────────────────────────────────────────────


def test_folder_skill_discovered(tmp_path: Path):
    """Folder with SKILL.md is discovered as a skill."""
    skill_dir = tmp_path / "code-review"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: code-review\ndescription: Review code\n---\nReview steps."
    )

    registry = SkillRegistry()
    from leeway.skills.registry import _scan_directory

    _scan_directory(tmp_path, "project", registry)
    skill = registry.get("code-review")
    assert skill is not None
    assert skill.name == "code-review"
    assert skill.dir_path == skill_dir
    assert "Review steps" in skill.content


def test_folder_skill_name_from_dir(tmp_path: Path):
    """Skill name defaults to folder name when not in frontmatter."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("Just instructions, no frontmatter.")

    skill = _parse_skill_file(skill_dir / "SKILL.md", "project", dir_path=skill_dir)
    assert skill is not None
    assert skill.name == "my-skill"


def test_folder_skill_supporting_files(tmp_path: Path):
    """Supporting files in the skill folder are accessible."""
    skill_dir = tmp_path / "security"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: security\n---\nMain content.")
    (skill_dir / "owasp.md").write_text("OWASP checklist here.")
    (skill_dir / "examples.md").write_text("Example findings.")
    (skill_dir / "_private.md").write_text("Should be hidden.")

    skill = _parse_skill_file(skill_dir / "SKILL.md", "project", dir_path=skill_dir)
    assert skill is not None

    files = skill.list_files()
    assert "owasp.md" in files
    assert "examples.md" in files
    assert "_private.md" not in files  # hidden files excluded
    assert "SKILL.md" not in files  # SKILL.md excluded

    content = skill.read_file("owasp.md")
    assert content == "OWASP checklist here."


def test_folder_skill_path_traversal_blocked(tmp_path: Path):
    """Path traversal in read_file is prevented."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: test\n---\nContent.")

    # Create a file outside the skill dir
    (tmp_path / "secret.txt").write_text("should not be readable")

    skill = _parse_skill_file(skill_dir / "SKILL.md", "project", dir_path=skill_dir)
    assert skill.read_file("../secret.txt") is None


def test_folder_skill_overrides_flat(tmp_path: Path):
    """Folder skill takes precedence over flat .md file with same name."""
    # Create both a folder and flat file
    skill_dir = tmp_path / "review"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: review\n---\nFolder version.")
    (tmp_path / "review.md").write_text("---\nname: review\n---\nFlat version.")

    registry = SkillRegistry()
    from leeway.skills.registry import _scan_directory

    _scan_directory(tmp_path, "project", registry)
    skill = registry.get("review")
    assert skill is not None
    assert "Folder version" in skill.content
    assert skill.dir_path is not None


def test_legacy_flat_still_works(tmp_path: Path):
    """Flat .md files still load when no folder exists."""
    (tmp_path / "simple.md").write_text("---\nname: simple\n---\nFlat skill.")

    registry = SkillRegistry()
    from leeway.skills.registry import _scan_directory

    _scan_directory(tmp_path, "project", registry)
    skill = registry.get("simple")
    assert skill is not None
    assert "Flat skill" in skill.content
    assert skill.dir_path is None


def test_case_insensitive_lookup():
    """Registry supports case-insensitive and hyphen/underscore lookup."""
    registry = SkillRegistry()
    registry.register(SkillDefinition(name="code-review", content="test"))
    assert registry.get("code-review") is not None
    assert registry.get("code_review") is not None  # underscore → hyphen fallback
