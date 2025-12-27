import traceback
import logging
import gazu
from fastapi import APIRouter, HTTPException
from schemas import LoginRequest, RestoreSessionRequest

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("kitsu_publisher")

@router.post("/login")
def login(request: LoginRequest):
    logger.info(f"Login attempt for host: {request.host}, email: {request.email}")
    try:
        host_url = request.host
        if not host_url.startswith("http"):
            host_url = "https://" + host_url
        if not host_url.endswith("/api"):
            host_url = host_url.rstrip("/") + "/api"
            
        logger.info(f"Setting Kitsu host to: {host_url}")
        gazu.set_host(host_url)
        tokens = gazu.log_in(request.email, request.password)
        
        user = gazu.client.get_current_user()
        return {
            "message": "Login successful",
            "user": user,
            "tokens": tokens,
            "host": host_url
        }
    except Exception as e:
        logger.error(f"Login failed error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restore-session")
def restore_session(request: RestoreSessionRequest):
    logger.info(f"Restoring session for host: {request.host}")
    try:
        gazu.set_host(request.host)
        gazu.client.set_tokens(request.tokens)
        user = gazu.client.get_current_user()
        if not user:
             raise HTTPException(status_code=401, detail="Invalid session")
        return {
            "message": "Session restored",
            "user": user
        }
    except Exception as e:
        logger.error(f"Session restore failed: {e}")
        raise HTTPException(status_code=401, detail="Session expired or invalid")
