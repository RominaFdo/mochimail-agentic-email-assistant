import json


def _get(obj, key, default=None):
    """Read a field from either a dict or an object (AISuite mixes both)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _parse(value):
    """Turn a JSON string into Python data; leave anything else untouched."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def extract_steps(response) -> list[dict]:
    """Pair each tool call the model made with the result it got back.

    Returns a list like [{"name": "search_emails", "args": {...}, "result": [...]}]
    in the order the model called the tools.
    """
    steps, by_id = [], {}
    for msg in getattr(response.choices[0], "intermediate_messages", None) or []:
        role = _get(msg, "role")
        if role == "assistant":
            for tc in _get(msg, "tool_calls") or []:
                fn = _get(tc, "function")
                step = {"name": _get(fn, "name"), "args": _parse(_get(fn, "arguments")) or {}, "result": None}
                steps.append(step)
                by_id[_get(tc, "id")] = step
        elif role == "tool":
            step = by_id.get(_get(msg, "tool_call_id"))
            if step is not None:
                step["result"] = _parse(_get(msg, "content"))
    return steps


def pretty_print_chat_completion(response):
    """Print the tool-call trace and final answer from an AISuite response."""
    steps = extract_steps(response)

    print("=" * 60)
    for step in steps:
        print(f"\n🧠 LLM Action: {step['name']}")
        print(json.dumps(step["args"], indent=2))
        print(f"🔧 Tool Response: {step['name']}")
        print(json.dumps(step["result"], indent=2))

    print(f"\n✅ Final Assistant Message:\n{response.choices[0].message.content}")
    if steps:
        print(f"\n🧭 Tool Sequence: {' → '.join(s['name'] for s in steps)}")
    print("=" * 60 + "\n")
