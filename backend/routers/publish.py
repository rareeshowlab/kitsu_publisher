import logging
import gazu
from fastapi import APIRouter
from schemas import PublishRequest

router = APIRouter(prefix="/publish", tags=["publish"])
logger = logging.getLogger("kitsu_publisher")

@router.post("/execute")
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
