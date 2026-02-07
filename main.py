import os, openai

MODEL = "gpt-3.5-turbo"
USE_MOCK = os.getenv("USE_MOCK","false").lower()=="true"

def call_model(prompt, max_tokens=1200, temperature=0.2):
    if USE_MOCK:
        return "Once upon a time, a cozy mock bedtime story ended happily."
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    resp = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}],
        max_tokens=max_tokens,
        temperature=temperature
    )
    return resp.choices[0].message["content"]

def main():
    req = input("What kind of bedtime story would you like? ")
    story = call_model(f"Tell a gentle bedtime story for ages 5-10. {req}")
    print(story)

if __name__ == "__main__":
    main()
