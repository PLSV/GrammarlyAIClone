from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException
from app.core.config import MAX_UPLOAD_BYTES

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        try:
            if cl is not None and int(cl) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="File too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Bad Content-Length")
        return await call_next(request)
