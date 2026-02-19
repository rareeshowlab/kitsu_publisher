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

@router.get("/system/config/projects/{project_id}")
def get_project_config(project_id: str):
    return config_manager.get_project_config(project_id)

@router.post("/system/config/projects/{project_id}")
def update_project_config(project_id: str, config: ConfigModel):
    config_manager.save_project_config(project_id, config.dict())
    return {"status": "updated", "config": config_manager.get_project_config(project_id)}

@router.post("/system/config")
def update_config(config: ConfigModel):
    # 전역 설정 저장 (project_settings 제외)
    new_data = config.dict()
    config_manager.save_config(new_data)
    return {"status": "updated", "config": config_manager.config}

@router.post("/system/preview-parse")
def preview_parse(payload: Dict[str, Any]):
    filename = payload.get("filename", "")
    project_id = payload.get("project_id")
    
    # 프로젝트 ID가 있으면 해당 프로젝트 설정을 기본으로 사용
    if project_id:
        proj_config = config_manager.get_project_config(project_id)
        default_pattern = proj_config.get("filename_pattern")
        default_seq = proj_config.get("sequence_name_template")
        default_shot = proj_config.get("shot_name_template")
        default_task = proj_config.get("default_task_name")
    else:
        default_pattern = config_manager.get("filename_pattern")
        default_seq = config_manager.get("sequence_name_template")
        default_shot = config_manager.get("shot_name_template")
        default_task = config_manager.get("default_task_name")

    # 페이로드에 명시적으로 전달된 값이 있으면 그것을 사용 (오버라이드)
    pattern = payload.get("filename_pattern") or default_pattern
    seq_template = payload.get("sequence_name_template") or default_seq
    shot_template = payload.get("shot_name_template") or default_shot
    
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
