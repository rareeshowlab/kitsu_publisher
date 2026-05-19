import os
import logging
import gazu
import traceback
from typing import List
from fastapi import APIRouter, HTTPException

from schemas import ScanRequest, ScanResponseItem, MatchRequest, MatchResponse, TaskOption
from dependencies import config_manager
from services.parser import parse_filename

router = APIRouter(prefix="/files", tags=["files"])
logger = logging.getLogger("kitsu_publisher")

SEQUENCE_EXTENSIONS = {".exr", ".dpx", ".tif", ".tiff", ".png"}


def _find_sequence_folders(root_dir: str) -> dict:
    """
    디렉토리 트리에서 EXR/DPX 시퀀스 파일이 들어있는 폴더를 찾아
    {폴더명.lower(): 폴더경로} 딕셔너리로 반환합니다.
    """
    seq_folders = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fname in filenames:
            if os.path.splitext(fname)[1].lower() in SEQUENCE_EXTENSIONS:
                folder_name = os.path.basename(dirpath)
                seq_folders[folder_name.lower()] = dirpath
                break
    return seq_folders


def _find_matching_sequence_folder(shot_name: str, seq_folders: dict) -> str | None:
    """shot_name을 포함하는 시퀀스 폴더를 찾아 경로를 반환합니다."""
    if not shot_name:
        return None
    shot_lower = shot_name.lower()
    for folder_name, folder_path in seq_folders.items():
        if shot_lower in folder_name or folder_name in shot_lower:
            return folder_path
    return None


@router.post("/scan", response_model=List[ScanResponseItem])
def scan_directory(request: ScanRequest):
    logger.info(f"Scanning directory: {request.directory}")
    if not os.path.isdir(request.directory):
        raise HTTPException(status_code=400, detail="Invalid directory path")

    results = []
    video_extensions = {".mov", ".mp4"}

    project_config = config_manager.get_project_config(request.project_id)
    pattern = project_config.get("filename_pattern")
    seq_template = project_config.get("sequence_name_template")
    shot_template = project_config.get("shot_name_template")
    default_task = project_config.get("default_task_name")

    # EXR/DPX 시퀀스 폴더 미리 수집
    seq_folders = _find_sequence_folders(request.directory)

    for root, _, files in os.walk(request.directory):
        for file in files:
            if file.startswith('.'):
                continue
            ext = os.path.splitext(file)[1].lower()
            if ext in video_extensions:
                file_path = os.path.join(root, file)
                parsed = parse_filename(file, pattern, seq_template, shot_template, default_task)
                shot_name = parsed.get("shot_name") if parsed else None
                sequence_folder = _find_matching_sequence_folder(shot_name, seq_folders)
                if parsed:
                    results.append(ScanResponseItem(
                        file_path=file_path,
                        filename=file,
                        sequence_folder=sequence_folder,
                        **parsed
                    ))
                else:
                    results.append(ScanResponseItem(
                        file_path=file_path,
                        filename=file,
                        episode_name=None, sequence_name="", shot_name="", task_name="", version=None,
                        sequence_folder=sequence_folder
                    ))
    return results

@router.post("/match-single", response_model=MatchResponse)
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
