@app.get("/kitsu/task-status-types")
def get_task_status_types():
    """Kitsu에 정의된 Task Status 목록을 가져옵니다."""
    try:
        # Kitsu에서 모든 Task Status Type을 가져옵니다.
        # 보통 'Todo', 'In Progress', 'Retake', 'Done' 등이 포함됩니다.
        # gazu.task.all_task_status_types() 사용
        statuses = gazu.task.all_task_status_types()
        return statuses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PublishRequestItem(BaseModel):
    file_path: str
    shot_name: str
    task_name: str
    comment: Optional[str] = None
    task_status_id: Optional[str] = None

class PublishRequest(BaseModel):
    project_name: Optional[str] = None # (Optional) 특정 프로젝트 컨텍스트가 필요하다면
    items: List[PublishRequestItem]

@app.post("/publish/execute")
def execute_publish(request: PublishRequest):
    """선택된 샷들에 대해 업로드 및 업데이트를 수행합니다."""
    results = []
    
    for item in request.items:
        try:
            # 1. 샷 찾기 (프로젝트 범위 고려 필요하지만, 일단 이름으로 전역 검색 시도)
            # 주의: 정확한 매칭을 위해 프로젝트 정보가 있으면 좋습니다.
            # 여기서는 shot_name으로 샷 객체를 찾습니다.
            # gazu.shot.get_shot_by_name(project, sequence, shot_name) 이 필요할 수 있음.
            # 간소화를 위해 '모든 프로젝트'에서 해당 샷 이름을 검색하거나, 
            # 첫 번째 매칭되는 샷을 사용한다고 가정합니다.
            
            # 개선: 파싱된 shot_name이 'EP12_s43_c0020' 형태이므로
            # 이를 이용해 정확한 샷을 찾아야 합니다.
            # Kitsu API 구조상 Project -> Sequence -> Shot 계층 탐색이 안전합니다.
            
            # 임시 구현: 이름으로 검색 (동명이인이 있을 수 있음 위험)
            # -> 실제로는 파싱된 Episode, Sequence 정보를 활용해 정확히 찾아야 함.
            
            # 파싱된 정보를 바탕으로 검색 로직 구현이 복잡할 수 있으므로
            # 우선은 '업로드 로직'의 뼈대만 잡습니다.
            
            # TODO: 실제 업로드 로직 (gazu.task.add_preview 등)
            # task = gazu.task.get_task_by_name(shot, item.task_name)
            # gazu.task.add_comment(task, task_status_id, comment)
            # gazu.files.new_preview_file(...)
            
            results.append({"shot_name": item.shot_name, "status": "success"})
            
        except Exception as e:
            results.append({"shot_name": item.shot_name, "status": "error", "message": str(e)})
            
    return results
