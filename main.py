from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI-Powered Transaction Processing Pipeline",
    description="Upload a dirty transactions CSV, process it asynchronously, get back a structured report.",
)

@app.get("/health")
def check_health():
    return { "status": "healthy" }
