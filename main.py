from dotenv import load_dotenv
from agent import run_agent

load_dotenv()

if __name__ == "__main__":
    print("Email Agent — type 'quit' to exit\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue
        run_agent(user_input)