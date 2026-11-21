import json
import time

from aisuite.provider import ProviderFactory
from aisuite.utils.tools import Tools
from pydantic import ValidationError

import email_tools
from display_functions import pretty_print_chat_completion
from prompt_builder import build_prompt

# Together AI serverless model with tool calling. GLM-5.3-Flash takes clean, minimal
# tool steps and is cheap. Also works (but makes redundant calls): "together:openai/gpt-oss-120b"
DEFAULT_MODEL = "together:zai-org/GLM-5.3-Flash"

# AISuite turns each Python function's signature + docstring into a JSON tool
# schema, and builds a Pydantic model we use to validate the model's arguments.
_TOOLS = Tools(email_tools.ALL_TOOLS)
_TOOL_SCHEMAS = _TOOLS.tools()

_providers = {}


def _provider_for(model: str):
    """Return the AISuite provider (e.g. Together) and the bare model name.

    We call the provider directly rather than `ai.Client().chat.completions.create`
    because aisuite 0.1.14 crashes (`is_mcp_config` not defined) when tool schemas
    are passed as dicts and the optional `mcp` package isn't installed.
    """
    key, name = model.split(":", 1)
    if key not in _providers:
        # Bump the timeout: Together's default 30s can be tight for multi-step tool runs.
        _providers[key] = ProviderFactory.create_provider(key, {"timeout": 120})
    return _providers[key], name


def _complete(model: str, messages: list, use_tools: bool = True, retries: int = 3):
    """One model call, retrying briefly on transient server errors (5xx / timeouts)."""
    provider, name = _provider_for(model)
    extra = {"tools": _TOOL_SCHEMAS} if use_tools else {}
    for attempt in range(retries):
        try:
            return provider.chat_completions_create(name, messages, temperature=0.1, **extra)
        except Exception as e:
            transient = any(s in str(e) for s in ("500", "502", "503", "504", "timed out", "Timeout"))
            if not transient or attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))


def _run_tool(tool_call) -> object:
    """Execute one tool call. Problems are returned to the model as an error
    result (instead of crashing) so it can correct itself on the next turn."""
    name = tool_call.function.name
    tool = _TOOLS._tools.get(name)
    if tool is None:
        return {"error": f"Unknown tool '{name}'."}
    try:
        raw = tool_call.function.arguments
        args = json.loads(raw) if isinstance(raw, str) and raw.strip() else (raw or {})
        validated = tool["param_model"](**args)
    except (ValueError, ValidationError) as e:
        return {"error": f"Invalid arguments for {name}: {e}. Call it again with the required arguments."}
    try:
        return tool["function"](**validated.model_dump())
    except Exception as e:
        return {"error": f"{name} failed: {e}"}


def ask_agent(user_request: str, model: str = DEFAULT_MODEL, max_turns: int = 10):
    """Send a natural-language request to the LLM and let it call email tools.

    Each turn: the model either asks for tool calls (we run them and send the
    results back) or gives its final answer. Returns the final AISuite response,
    with every assistant/tool message attached as `choices[0].intermediate_messages`
    so the UI can show the trace. Raises on API errors.
    """
    messages = [{"role": "user", "content": build_prompt(user_request)}]
    trace = []

    for _ in range(max_turns):
        response = _complete(model, messages)
        msg = response.choices[0].message
        trace.append(msg)

        if not msg.tool_calls:
            break

        messages.append(msg)
        seen = set()  # identical calls within one step run only once (no double-sends)
        for tc in msg.tool_calls:
            key = (tc.function.name, str(tc.function.arguments))
            if key in seen:
                result = {"note": "Duplicate of an identical call in this step; not executed again."}
            else:
                seen.add(key)
                result = _run_tool(tc)
            tool_msg = {
                "role": "tool",
                "name": tc.function.name,
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            }
            messages.append(tool_msg)
            trace.append(tool_msg)
    else:
        # Out of turns: ask once more without letting it call tools.
        messages.append({"role": "user", "content": "Stop calling tools and summarise what you did."})
        response = _complete(model, messages, use_tools=False)
        trace.append(response.choices[0].message)

    response.choices[0].intermediate_messages = trace
    return response


def run_agent(user_request: str, model: str = DEFAULT_MODEL, max_turns: int = 10):
    """Terminal version: run the agent and pretty-print the trace."""
    print(f"\n🚀 Agent starting | Model: {model}")
    print(f"📨 Request: {user_request}\n")

    try:
        response = ask_agent(user_request, model, max_turns)
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

    pretty_print_chat_completion(response)
    return response.choices[0].message.content
