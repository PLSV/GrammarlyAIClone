from fastapi import FastAPI
from app.api.routes_upload import router as upload_router
from app.api.routes_analyze import router as analyze_router
from app.middleware.limits import BodySizeLimitMiddleware

app = FastAPI(title="GrammarlyAIClone")

app.add_middleware(BodySizeLimitMiddleware)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(upload_router)
app.include_router(analyze_router)
