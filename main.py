from fastapi import FastAPI

app = FastAPI(
    title="AI-Powered Transaction Processing Pipeline",
    description="Upload a dirty transactions CSV, process it asynchronously, get back a structured report.",
)

@app.get("/health")
def check_health():
    return { "status": "healthy" }
