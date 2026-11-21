import truststore
from dotenv import load_dotenv
truststore.inject_into_ssl()

# utf-8-sig strips the invisible BOM that Windows editors/PowerShell often add
# to the start of .env, which would otherwise corrupt the first variable name.
load_dotenv(encoding="utf-8-sig")

from agent import run_agent

if __name__ == "__main__":
    print("Email Agent - type 'quit' to exit\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue
        run_agent(user_input)
