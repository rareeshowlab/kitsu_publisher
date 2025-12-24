import os
import re
import traceback
import logging
import asyncio
import gazu
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from updater import Updater

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kitsu_publisher")

# 로그 큐 (메모리에 로그 저장)
log_queue = asyncio.Queue()

class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(log_queue.put(msg))
            except RuntimeError:
                pass
        except Exception:
            self.handleError(record)

# 커스텀 핸들러 추가
queue_handler = QueueHandler()
queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(queue_handler)
logging.getLogger().addHandler(queue_handler)

app = FastAPI()
updater = Updater()

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

# Pydantic 모델
class LoginRequest(BaseModel):
    host: str
    email: str
    password: str

class RestoreSessionRequest(BaseModel):
    host: str
    tokens: Dict[str, Any]

class ScanRequest(BaseModel):
    directory: str
    project_id: str

class PublishRequestItem(BaseModel):
    file_path: str
    shot_id: str
    task_id: str
    comment: Optional[str] = None
    task_status_id: str

class PublishRequest(BaseModel):
    items: List[PublishRequestItem]

class TaskOption(BaseModel):
    id: str
    name: str

class ScanResponseItem(BaseModel):
    file_path: str
    filename: str
    episode_name: Optional[str]
    sequence_name: Optional[str]
    shot_name: Optional[str]
    task_name: Optional[str]
    version: Optional[int]

class MatchRequest(BaseModel):
    project_id: str
    episode_name: Optional[str] = None
    sequence_name: str
    shot_name: str
    task_name: str

class MatchResponse(BaseModel):
    shot_id: Optional[str] = None
    task_id: Optional[str] = None
    available_tasks: List[TaskOption] = []
    match_status: str = "none"
    last_version: Optional[int] = None

FILENAME_PATTERN = re.compile(r"^(?:(?P<episode>[^_]+)_)?(?P<sequence>[^_]+)_(?P<shot_num>[^_]+)_(?P<task>[^_]+)_v(?P<version>\d+)")

@app.get("/system/check-update")
def check_update():
    return updater.check_for_updates()

@app.post("/system/open-url")
def open_url(payload: Dict[str, str]):
    url = payload.get("url")
    if url:
        updater.open_download_page(url)
    return {"status": "opened"}

@app.get("/logs/stream")
async def stream_logs():
    async def log_generator():
        while True:
            message = await log_queue.get()
            yield f"data: {message}\n\n"
    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.get("/")
def read_root():
    return {"message": "Kitsu Publisher API is running"}

@app.post("/auth/login")
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

@app.post("/auth/restore-session")
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

@app.get("/kitsu/projects")
def get_projects():
    try:
        return gazu.project.all_open_projects()
    except Exception as e:
        logger.error(f"Failed to get projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/kitsu/task-status-types")
def get_task_status_types():
    try:
        return gazu.task.all_task_statuses()
    except Exception as e:
        logger.error(f"Failed to get status types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def parse_filename(filename: str) -> Optional[dict]:
    match = FILENAME_PATTERN.search(filename)
    if not match:
        return None
    data = match.groupdict()
    task_map = {"comp": "Compositing", "ani": "Animation", "lit": "Lighting", "fx": "FX"}
    task_raw = data["task"].lower()
    task_name = task_map.get(task_raw, task_raw.capitalize())
    
    if data["episode"]:
        seq_name = f"{data['episode']}_{data['sequence']}"
        shot_name = f"{seq_name}_{data['shot_num']}"
    else:
        seq_name = data["sequence"]
        shot_name = f"{seq_name}_{data['shot_num']}"

    return {
        "episode_name": data["episode"],
        "sequence_name": seq_name,
        "shot_name": shot_name,
        "task_name": task_name,
        "version": int(data["version"])
    }

@app.post("/files/scan", response_model=List[ScanResponseItem])
def scan_directory(request: ScanRequest):
    logger.info(f"Scanning directory: {request.directory}")
    if not os.path.isdir(request.directory):
        raise HTTPException(status_code=400, detail="Invalid directory path")

    results = []
    video_extensions = {".mov", ".mp4"}
    
    for root, _, files in os.walk(request.directory):
        for file in files:
            if file.startswith('.'):
                continue
            ext = os.path.splitext(file)[1].lower()
            if ext in video_extensions:
                file_path = os.path.join(root, file)
                parsed = parse_filename(file)
                if parsed:
                    results.append(ScanResponseItem(
                        file_path=file_path,
                        filename=file,
                        **parsed
                    ))
                else:
                    results.append(ScanResponseItem(
                        file_path=file_path,
                        filename=file,
                        episode_name=None, sequence_name="", shot_name="", task_name="", version=None
                    ))
    return results

@app.post("/files/match-single", response_model=MatchResponse)
def match_single_shot(request: MatchRequest):
    try:
        project = gazu.project.get_project(request.project_id)
        if not project:
            return MatchResponse()

        shot_id, task_id = None, None
        available_tasks = []
        match_status = "none"
        last_version = None

        all_sequences = gazu.shot.all_sequences_for_project(project)
        sequence = next((s for s in all_sequences if s["name"].lower() == request.sequence_name.lower()), None)
        
        if sequence:
            logger.debug(f"Sequence matched: {sequence['name']}")
            all_shots = gazu.shot.all_shots_for_sequence(sequence)
            
            shot = next((s for s in all_shots if s["name"].lower() == request.shot_name.lower()), None)
            if not shot:
                short_name = request.shot_name.split('_')[-1]
                shot = next((s for s in all_shots if s["name"].lower() == short_name.lower()), None)

            if shot:
                logger.debug(f"Shot matched: {shot['name']}")
                shot_id = shot["id"]
                match_status = "shot_only"
                
                all_tasks = gazu.task.all_tasks_for_shot(shot)
                available_tasks = [TaskOption(id=t["id"], name=t["task_type_name"]) for t in all_tasks]
                
                matched_task = next((t for t in all_tasks if t["task_type_name"].lower() == request.task_name.lower()), None)
                if matched_task:
                    task_id = matched_task["id"]
                    match_status = "full"
                    
                    try:
                        previews = gazu.files.get_all_preview_files_for_task(matched_task)
                        if previews and len(previews) > 0:
                            last_version = max([int(p.get("revision", 0)) for p in previews])
                            logger.debug(f"Task {request.task_name} has last version v{last_version}")
                        else:
                            last_version = 0
                    except Exception as e:
                        logger.warning(f"Failed to get previews: {e}")
                        last_version = 0
        
        return MatchResponse(
            shot_id=shot_id,
            task_id=task_id,
            available_tasks=available_tasks,
            match_status=match_status,
            last_version=last_version
        )
    except Exception as e:
        logger.error(f"Match failed: {e}")
        traceback.print_exc()
        return MatchResponse()

@app.post("/publish/execute")
def execute_publish(request: PublishRequest):
    logger.info(f"Executing publish for {len(request.items)} items")
    results = []
    for item in request.items:
        try:
            task = gazu.task.get_task(item.task_id)
            task_status = gazu.task.get_task_status(item.task_status_id)
            comment = gazu.task.add_comment(task, task_status, item.comment or "Published via Batch Publisher")
            gazu.task.add_preview(task, comment, item.file_path)
            results.append({"file_path": item.file_path, "status": "success"})
        except Exception as e:
            logger.error(f"Publish failed for {item.file_path}: {e}")
            results.append({"file_path": item.file_path, "status": "error", "message": str(e)})
    return results
