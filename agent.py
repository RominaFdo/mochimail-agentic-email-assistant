import os
import json
import aisuite as ai
import email_tools as tools_module
from prompt_builder import build_prompt


def run_agent(
    user_request: str,
    model: str = "together:meta-llama/Llama-3.3-70B-Instruct-Turbo",
    max_turns: int = 10,
):
    client = ai.Client()

    # Map tool names to functions
    tool_map = {fn.__name__: fn for fn in tools_module.ALL_TOOLS}

    messages = [
        {"role": "user", "content": build_prompt(user_request)}
    ]

    print(f"\n🚀 Agent starting | Model: {model}")
    print(f"📨 Request: {user_request}\n")

    for turn in range(max_turns):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools_module.ALL_TOOLS,
                temperature=0.1,
            )
        except Exception as e:
            print(f"❌ API Error: {e}")
            return None

        msg = response.choices[0].message

        # Some providers return None content with tool calls
        content = msg.content or ""

        tool_calls = getattr(msg, "tool_calls", None)

        # ✅ If no tools → final answer
        if not tool_calls:
            print(f"✅ Final Answer:\n{content}")
            return content

        # Add assistant message (with tool calls)
        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls
        })

        # 🔧 Handle tool calls
        for tc in tool_calls:
            fn_name = tc.function.name

            try:
                fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                print(f"⚠️ Failed to parse args for {fn_name}")
                fn_args = {}

            print(f"🔧 Calling: {fn_name}({fn_args})")

            if fn_name not in tool_map:
                result = f"Error: Tool '{fn_name}' not found"
            else:
                try:
                    result = tool_map[fn_name](**fn_args)
                except Exception as e:
                    result = f"Error executing tool: {str(e)}"

            print(f"   ↳ Result: {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })

    print("⚠️ Max turns reached.")
    return None