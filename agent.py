import os
from llm import get_llm


MAX_STEPS = 5

def calculator(expr):
    try:
        return str(eval(expr.replace("^", "**")))
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"

def run(question):
    SYSTEM = (
        "You are a simple calculator agent. Tool: calculator(expr).\n"
        "Each step, respond with exactly one of:\n"
        "TOOL: calculator\n"
        "ARGS: <math expression>\n"
        "or:\n"
        "FINAL: <answer>\n"
        "or:\n"
        "If the tool can't help, do not guess. Respond exactly: FINAL: None\n"
    )


    messages = [{
        "role": "user",
        "content": question
    }]
    llm = get_llm()
    step = 0
    final_answer = None
    while step< MAX_STEPS:
        response = llm.complete(SYSTEM, messages)

        if response.startswith("FINAL"):
            final_answer = response.split("FINAL:", 1)[1].strip().splitlines()[0].strip()
            if final_answer=='None':
                final_answer=None
            break

        if response.startswith("TOOL"):
            expr = response.split("ARGS:", 1)[1].strip().splitlines()[0].strip()

            result = calculator(expr)

            messages.append({
                "role":"assistant",
                "content": response
            })

            messages.append({
                "role":"user",
                "content":f"Tool result {result}"
            })

        step += 1

    return final_answer, step


if __name__=="__main__":
    ans, steps = run("What is 8% of today's USD to INR exchange rate?")
    print(ans, steps)