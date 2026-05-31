import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load your GEMINI_API_KEY from the .env file
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ---------------------------------------------------------
# Agent 1: The Supervisor (Planner & Reviewer)
# ---------------------------------------------------------
def supervisor_agent(user_request: str) -> str:
    print(f"\n[🤖 Supervisor] Analyzing request: '{user_request}'")
    
    # The Supervisor uses a fast model to break down the problem
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=f"You are the Lead Engineering Agent. Break this request into a strict 3-step technical plan for your coding agent to execute. Request: {user_request}",
        config=types.GenerateContentConfig(temperature=0.2)
    )
    
    plan = response.text
    print(f"\n[📋 Supervisor Plan]\n{plan}")
    return plan

# ---------------------------------------------------------
# Agent 2: The Coder (Execution & Sandboxing)
# ---------------------------------------------------------
def coder_agent(engineering_plan: str):
    print("\n[💻 Coder] Writing code and executing in native sandbox...")
    
    # The Coder uses native Code Execution to test its own work
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=f"You are the Execution Agent. Write a Python script to fulfill this exact plan. Once written, run it to verify it works. \n\nPlan:\n{engineering_plan}",
        config=types.GenerateContentConfig(
            tools=[{"code_execution": {}}], # <--- THE FIX: Passed as a Tool
            temperature=0.1
        )
    )
    
    print(f"\n[✅ Coder Output]\n{response.text}")

# ---------------------------------------------------------
# The Multi-Agent Orchestration Loop
# ---------------------------------------------------------
def main():
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    for m in client.models.list():
        print(m.name)

    # 1. You give the system a complex task
    task = "Write a python script that checks the available system memory (RAM) in gigabytes on this Linux machine and prints it to the console."
    
    # 2. Handoff to Supervisor to make the plan
    approved_plan = supervisor_agent(task)

    # 3. Handoff to Coder to write and test the code based on the plan
    coder_agent(approved_plan)

if __name__ == "__main__":
    main()