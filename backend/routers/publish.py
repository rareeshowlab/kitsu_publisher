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
        filename = item.file_path.split("/")[-1] if "/" in item.file_path else item.file_path
        logger.info(f"Starting publish for: {filename}")
        try:
            logger.info(f"  - Getting task and status for {filename}")
            task = gazu.task.get_task(item.task_id)
            task_status = gazu.task.get_task_status(item.task_status_id)
            
            logger.info(f"  - Adding comment for {filename}")
            comment = gazu.task.add_comment(task, task_status, item.comment or "Published via Batch Publisher")
            
            logger.info(f"  - Uploading preview file for {filename} (This may take a while...)")
            gazu.task.add_preview(task, comment, item.file_path)
            
            logger.info(f"Successfully published: {filename}")
            results.append({"file_path": item.file_path, "status": "success"})
        except Exception as e:
            logger.error(f"Publish failed for {item.file_path}: {e}")
            results.append({"file_path": item.file_path, "status": "error", "message": str(e)})
    return results
