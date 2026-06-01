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


# 글로벌 FTP 접속 설정 (Kitsu 로그인 단위로 하나)
class FtpGlobalConfig(BaseModel):
    enabled: bool = False
    protocol: str = "sftp"  # "ftp" or "sftp"
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""
    passive: bool = True  # FTP only


# 라우터 내부에서 접속 정보로 사용하는 모델 (FtpGlobalConfig와 동일 구조)
class FtpConfigModel(BaseModel):
    enabled: bool = False
    protocol: str = "sftp"
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""
    passive: bool = True


# 프로젝트별 FTP 루트 경로
class FtpProjectRoot(BaseModel):
    remote_root: str = "/"


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
    group_key: Optional[str] = None  # 프론트엔드에서 그룹 식별용


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
