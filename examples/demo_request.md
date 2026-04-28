# IM Context

产品：我们要做一个 Agent-Pilot 办公协同系统，重点是从飞书群聊自动沉淀项目方案、PPT 和白板流程。

工程：不要重造 IM、Doc、Slides 或白板，复用飞书、lark-cli、Presenton 和 Gateway。主编排层统一使用 Codex + superpowers。

设计：用户入口应该在飞书 IM，桌面端和移动端都能看到进度与产物。GUI 是仪表盘，不是主流程。

# User Request

根据刚才群聊内容，生成项目方案、8 页答辩 PPT 大纲、白板流程图和交付摘要。

# Acceptance Criteria

- 输出文档、PPT 大纲、白板流程和 artifacts.json。
- artifacts.json 必须包含 document、slides、whiteboard、summary、next_steps。
- 编排层只能是 Codex + superpowers。
