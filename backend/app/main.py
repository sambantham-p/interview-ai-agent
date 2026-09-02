from fastapi import FastAPI

app = FastAPI(title="interview-ai-agent")


@app.get("/health")
def health():
    return {"status": "ok"}
