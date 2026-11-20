import json

def pretty_print_response(response):
    """Print the agent response in a readable format."""
    print("\n" + "="*60)
    for message in response.get("messages", []):
        role = message.get("role", "unknown").upper()
        content = message.get("content", "")
        tool_calls = message.get("tool_calls", [])

        if tool_calls:
            print(f"\n🔧 [{role}] Tool Calls:")
            for tc in tool_calls:
                fn = tc.get("function", {})
                print(f"   → {fn.get('name')}({fn.get('arguments', '{}')})")
        elif content:
            if role == "ASSISTANT":
                print(f"\n✅ [ASSISTANT]: {content}")
            elif role == "TOOL":
                print(f"\n   Result: {content}")
            else:
                print(f"\n[{role}]: {content}")
    print("="*60 + "\n")