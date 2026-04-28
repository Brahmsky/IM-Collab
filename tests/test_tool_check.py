from __future__ import annotations

from bridge.tool_check import check_tools


def test_check_tools_reports_missing_and_present_binaries() -> None:
    result = check_tools(
        binaries=("definitely-missing-im-collab-binary", "python"),
        skill_names=("definitely-missing-skill",),
    )

    assert result["binaries"]["definitely-missing-im-collab-binary"]["available"] is False
    assert result["binaries"]["python"]["available"] is True
    assert result["skills"]["definitely-missing-skill"]["available"] is False


def test_check_tools_can_see_installed_lark_skill_directory() -> None:
    result = check_tools(binaries=(), skill_names=("lark-doc",))

    assert "path" in result["skills"]["lark-doc"]
