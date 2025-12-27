import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from dependencies import setup_logging
from routers import auth, system, kitsu, files, publish

# Logging 설정
setup_logging()
logger = logging.getLogger("kitsu_publisher")

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 정적 파일이나 로그 스트림 요청은 로깅 제외 (너무 빈번함)
    if request.url.path in ["/logs/stream", "/"]:
        return await call_next(request)
        
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Request failed: {e}")
        traceback.print_exc()
        raise

# 라우터 등록
app.include_router(auth.router)
app.include_router(system.router)
app.include_router(kitsu.router)
app.include_router(files.router)
app.include_router(publish.router)

@app.get("/")
def read_root():
    return {"message": "Kitsu Publisher API is running"}
