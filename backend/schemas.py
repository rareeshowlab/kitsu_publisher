from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

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
    sequence_folder: Optional[str] = None  # EXR/DPX sequence folder path if found

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


class FtpConfigModel(BaseModel):
    enabled: bool = False
    protocol: str = "sftp"  # "ftp" or "sftp"
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""
    passive: bool = True  # FTP only
    remote_root: str = "/"  # default upload root path for this project


class FtpBrowseRequest(BaseModel):
    config: FtpConfigModel
    path: str = "/"


class FtpMkdirRequest(BaseModel):
    config: FtpConfigModel
    path: str


class FtpEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


class FtpTransferItem(BaseModel):
    local_path: str
    is_dir: bool
    remote_name: str


class FtpTransferRequest(BaseModel):
    config: FtpConfigModel
    remote_dest: str
    items: List[FtpTransferItem]


class FtpProjectConfig(BaseModel):
    default_task_name: str
    filename_pattern: str
    sequence_name_template: str
    shot_name_template: str
    ftp_config: Optional[FtpConfigModel] = None
