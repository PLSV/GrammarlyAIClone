from fastapi import FastAPI
from app.api.routes_upload import router as upload_router
from app.api.routes_analyze import router as analyze_router
from app.api.routes_revise import router as revise_router
from app.middleware.limits import BodySizeLimitMiddleware
from app.api.routes_download import router as download_router

app = FastAPI(title="GrammarlyAIClone")

app.add_middleware(BodySizeLimitMiddleware)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(upload_router)
app.include_router(analyze_router)
app.include_router(revise_router)
app.include_router(download_router)
