from __future__ import annotations

from typing import Any

TOOL_NAMES = ("feishu-cli", "lark-openapi-mcp", "presenton")


def tool_catalog() -> dict[str, dict[str, Any]]:
    return {
        "feishu-cli": {
            "role": "primary Feishu/Lark office CLI and bundled AI skills",
            "uses": [
                "IM message send/reply/search",
                "cloud document create/read/update with Markdown",
                "Drive upload/download",
                "whiteboard-capable document operations",
            ],
            "sources": [
                "https://feishu-cli.com/",
                "https://www.npmjs.com/package/@larksuite/cli",
            ],
        },
        "lark-openapi-mcp": {
            "role": "official Feishu/Lark OpenAPI MCP server for broad API coverage",
            "uses": [
                "MCP access to Feishu/Lark Open Platform APIs",
                "document processing",
                "conversation management",
                "calendar and collaboration automation",
            ],
            "sources": ["https://github.com/larksuite/lark-openapi-mcp"],
        },
        "presenton": {
            "role": "presentation generation service through API or MCP",
            "uses": [
                "PPTX/PDF generation",
                "MCP tool generate_presentation",
                "HTTP API /api/v1/ppt/presentation/generate",
            ],
            "sources": [
                "https://docs.presenton.ai/generate-presentation-over-mcp",
                "https://github.com/presenton/presenton",
            ],
        },
    }


def recommended_setup_commands() -> list[str]:
    return [
        "npm install -g @larksuite/cli",
        "npx skills add larksuite/cli -y -g",
        "lark-cli auth login --recommend",
        "lark-cli auth status",
        "lark-cli doctor",
    ]
