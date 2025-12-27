import logging
import gazu
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/kitsu", tags=["kitsu"])
logger = logging.getLogger("kitsu_publisher")

@router.get("/projects")
def get_projects():
    try:
        return gazu.project.all_open_projects()
    except Exception as e:
        logger.error(f"Failed to get projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task-status-types")
def get_task_status_types():
    try:
        return gazu.task.all_task_statuses()
    except Exception as e:
        logger.error(f"Failed to get status types: {e}")
        raise HTTPException(status_code=500, detail=str(e))
