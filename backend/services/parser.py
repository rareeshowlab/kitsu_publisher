import os
import re
import logging
from typing import Optional

logger = logging.getLogger("kitsu_publisher")

def parse_filename(
    filename: str, 
    pattern_str: str, 
    seq_template: str, 
    shot_template: str, 
    default_task_name: str
) -> Optional[dict]:
    """
    파일명과 설정된 패턴들을 기반으로 메타데이터를 추출합니다.
    모든 패턴 인자는 필수입니다. 호출하는 측에서 Config를 조회하여 전달해야 합니다.
    """
    
    if not pattern_str:
        return None
    
    # 2. 패턴을 정규식으로 변환
    # 지원 문법:
    # {key} -> (?P<key>.+?)
    # [ ... ] -> (?: ... )?  (Optional)
    
    regex_parts = []
    i = 0
    length = len(pattern_str)
    
    while i < length:
        char = pattern_str[i]
        
        if char == '[':
            # 옵셔널 시작
            regex_parts.append("(?:")
            i += 1
        elif char == ']':
            # 옵셔널 끝
            regex_parts.append(")?")
            i += 1
        elif char == '{':
            # 변수 시작, '}' 찾기
            end_brace = pattern_str.find('}', i)
            if end_brace != -1:
                key = pattern_str[i+1:end_brace]
                if key == "version":
                    regex_parts.append(f"(?P<{key}>\\d+)")
                else:
                    regex_parts.append(f"(?P<{key}>.+?)")
                i = end_brace + 1
            else:
                # 닫는 괄호 없으면 그냥 문자로 취급
                regex_parts.append(re.escape(char))
                i += 1
        elif char == '*':
            # 와일드카드 -> 모든 문자 매칭 (Non-greedy)
            regex_parts.append(".*?")
            i += 1
        else:
            # 일반 문자 -> 이스케이프
            regex_parts.append(re.escape(char))
            i += 1
            
    regex_pattern = "^" + "".join(regex_parts) + "$"
    
    logger.debug(f"Generated Regex: {regex_pattern}") # Info -> Debug로 변경 (로그 과다 방지)

    # 확장자 제거 후 매칭
    name_without_ext = os.path.splitext(filename)[0]
    
    try:
        match = re.match(regex_pattern, name_without_ext)
    except re.error as e:
        logger.error(f"Invalid regex generated: {regex_pattern} - {e}")
        return None

    if not match:
        # 매칭 실패 로그는 디버그 레벨로 낮춤 (스캔 시 너무 많이 뜰 수 있음)
        logger.debug(f"No match for '{name_without_ext}' against pattern '{pattern_str}'")
        return None
    
    data = match.groupdict()
    
    # 3. 데이터 정제
    # 태스크 이름 매핑
    task_map = {"comp": "Compositing", "ani": "Animation", "lit": "Lighting", "fx": "FX"}
    task_raw = data.get("task", "").lower()
    task_name = task_map.get(task_raw, task_raw.capitalize())
    if not task_name:
        task_name = default_task_name

    # 템플릿 포맷팅을 위한 안전한 데이터 준비
    # None 값을 빈 문자열로 변환하여 포맷팅 에러 방지
    format_data = {k: (v if v is not None else "") for k, v in data.items()}
    
    # 4. 시퀀스 이름 조합
    try:
        # 템플릿에 사용된 키가 데이터에 없으면 KeyError 발생
        full_seq_name = seq_template.format(**format_data)
        # 만약 에피소드가 없는데 {episode}_ 부분이 앞에 붙어서 "_Seq01" 처럼 되면 앞의 _ 제거
        full_seq_name = full_seq_name.lstrip("_").rstrip("_")
    except KeyError as e:
        logger.warning(f"Missing key for sequence template: {e}")
        full_seq_name = data.get("sequence", "")

    # 5. 샷 이름 조합
    try:
        full_shot_name = shot_template.format(**format_data)
        full_shot_name = full_shot_name.lstrip("_").rstrip("_")
    except KeyError as e:
        logger.warning(f"Missing key for shot template: {e}")
        full_shot_name = data.get("shot", name_without_ext)

    return {
        "episode_name": data.get("episode"),
        "sequence_name": full_seq_name,
        "shot_name": full_shot_name,
        "task_name": task_name,
        "version": int(data.get("version", 0))
    }
