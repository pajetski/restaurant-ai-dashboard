"""Claude-backed ops assistant.

Actions are returned through a tool call (structured, schema-checked) rather
than parsed out of free text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .actions import ACTION_TYPES
from .analytics import build_context_summary, detect_cost_creep
from .manager import RestaurantManager
from .storage import Store

SYSTEM_PROMPT = (
    "You are an AI operations assistant for a restaurant. Give actionable guidance on "
    "inventory, ordering, staffing and pricing, grounded in the CURRENT STATE provided. "
    "Be concise. If you lack the data to answer, say so or ask ONE clarifying question; "
    "never invent numbers. When a concrete change to the dashboard data would help, call "
    "propose_actions — the owner reviews and approves every action before it is applied."
)

PROPOSE_ACTIONS_TOOL: Dict[str, Any] = {
    "name": "propose_actions",
    "description": "Propose changes to dashboard data for the owner to approve. Nothing is applied until approved.",
    "input_schema": {
        "type": "object",
        "properties": {
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ACTION_TYPES},
                        "hours": {"type": "string", "description": "set_hours, e.g. '11am–9pm'"},
                        "item": {"type": "string", "description": "update_menu_price / add_vendor_price"},
                        "vendor": {"type": "string", "description": "add_vendor_price"},
                        "price": {"type": "number", "description": "update_menu_price / add_vendor_price"},
                        "amount": {"type": "number", "description": "record_sale / record_expense"},
                    },
                    "required": ["type"],
                },
            }
        },
        "required": ["actions"],
    },
}


@dataclass
class Reply:
    text: str
    actions: List[Dict[str, Any]] = field(default_factory=list)


def build_state_block(m: RestaurantManager, store: Store) -> str:
    hist = store.load_vendor_history()
    creep = detect_cost_creep(hist).head(20)
    return (
        "CURRENT STATE\n" + build_context_summary(m)
        + "\nVENDOR PRICES\n"
        + ("\n".join(f"{v}: {p}" for v, p in m.vendor_prices.items()) or "none")
        + "\n\nRECENT VENDOR HISTORY\n"
        + (hist.tail(50).to_csv(index=False) if not hist.empty else "none")
        + "\nCOST CREEP SIGNALS\n"
        + (creep.to_csv(index=False) if not creep.empty else "none")
    )


def parse_response(content: List[Any]) -> Reply:
    text_parts, actions = [], []
    for block in content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use" and block.name == "propose_actions":
            actions.extend(block.input.get("actions", []))
    return Reply(text="\n".join(text_parts).strip(), actions=actions)


def ask(
    client: Any,
    model: str,
    question: str,
    state_block: str,
    history: List[Tuple[str, str]] | None = None,
) -> Reply:
    """history is a list of (role, text) with role in {'You', 'AI'}."""
    messages = [
        {"role": "user" if role == "You" else "assistant", "content": text}
        for role, text in (history or [])[-10:]
        if text
    ]
    messages.append({"role": "user", "content": f"{state_block}\n\nQUESTION: {question}"})
    resp = client.messages.create(
        model=model,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=messages,
        tools=[PROPOSE_ACTIONS_TOOL],
    )
    reply = parse_response(resp.content)
    if not reply.text and reply.actions:
        reply.text = "I'd suggest the following changes:"
    return reply


def make_client(api_key: str) -> Any:
    import anthropic

    return anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=60.0)
