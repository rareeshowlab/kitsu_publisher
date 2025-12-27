from typing import List, Optional, Dict, Any
from pydantic import BaseModel

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

class ConfigModel(BaseModel):
    default_task_name: str
    filename_pattern: str
    sequence_name_template: str
    shot_name_template: str
