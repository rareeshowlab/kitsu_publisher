from typing import Dict, Any
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from dependencies import config_manager, updater, log_queue
from schemas import ConfigModel
from services.parser import parse_filename

router = APIRouter(tags=["system"])

@router.get("/system/config")
def get_config():
    return config_manager.config

@router.post("/system/config")
def update_config(config: ConfigModel):
    config_manager.save_config(config.dict())
    return {"status": "updated", "config": config_manager.config}

@router.post("/system/preview-parse")
def preview_parse(payload: Dict[str, Any]):
    filename = payload.get("filename", "")
    # 프리뷰를 위해 현재 설정을 오버라이드할 수 있음
    pattern = payload.get("filename_pattern") or config_manager.get("filename_pattern")
    seq_template = payload.get("sequence_name_template") or config_manager.get("sequence_name_template")
    shot_template = payload.get("shot_name_template") or config_manager.get("shot_name_template")
    default_task = config_manager.get("default_task_name")
    
    parsed = parse_filename(filename, pattern, seq_template, shot_template, default_task)
    if parsed:
        return {"success": True, "data": parsed}
    else:
        return {"success": False, "message": "Does not match the current pattern"}

@router.get("/system/check-update")
def check_update():
    return updater.check_for_updates()

@router.post("/system/open-url")
def open_url(payload: Dict[str, str]):
    url = payload.get("url")
    if url:
        updater.open_download_page(url)
    return {"status": "opened"}

@router.get("/logs/stream")
async def stream_logs():
    async def log_generator():
        while True:
            message = await log_queue.get()
            yield f"data: {message}\n\n"
    return StreamingResponse(log_generator(), media_type="text/event-stream")
