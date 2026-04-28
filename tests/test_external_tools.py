from __future__ import annotations

from bridge.external_tools import TOOL_NAMES, recommended_setup_commands, tool_catalog


def test_tool_catalog_prefers_existing_office_wheels() -> None:
    catalog = tool_catalog()

    assert TOOL_NAMES == ("feishu-cli", "lark-openapi-mcp", "presenton")
    assert catalog["feishu-cli"]["role"] == "primary Feishu/Lark office CLI and bundled AI skills"
    assert "https://feishu-cli.com/" in catalog["feishu-cli"]["sources"]
    assert "https://github.com/larksuite/lark-openapi-mcp" in catalog["lark-openapi-mcp"]["sources"]
    assert "https://docs.presenton.ai/generate-presentation-over-mcp" in catalog["presenton"]["sources"]


def test_recommended_setup_commands_are_tool_installs_not_custom_office_logic() -> None:
    commands = recommended_setup_commands()

    assert "npm install -g @larksuite/cli" in commands
    assert "npx skills add larksuite/cli -y -g" in commands
    assert "lark-cli doctor" in commands
    assert not any("OMO" in command or "OMX" in command for command in commands)
