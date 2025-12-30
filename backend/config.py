import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("kitsu_publisher")

class ConfigManager:
    def __init__(self):
        # 설정 파일 경로: ~/.kitsu_publisher_data/config.json
        self.config_dir = os.path.join(os.path.expanduser('~'), '.kitsu_publisher_data')
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.config = {}
        self.config = self.load_config()

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "default_task_name": "Compositing",
            # 기본 패턴: 시퀀스_샷_태스크_v버전
            # 예: SQ01_SH010_Comp_v001.mov
            "filename_pattern": "[{episode}_]{sequence}_{shot}_{task}_v{version}*",
            # 시퀀스 이름 구성 방식 (예: {episode}_{sequence})
            "sequence_name_template": "{episode}_{sequence}",
            # Kitsu에서의 샷 이름 구성 방식 (파일명의 토큰을 조합)
            # 예: 파일명이 SQ01_SH010 이면, 샷 이름도 SQ01_SH010
            "shot_name_template": "{episode}_{sequence}_{shot}",
            "session": None,
            "last_directory": ""
        }

    def load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        if not os.path.exists(self.config_file):
            default_config = self.get_default_config()
            self.save_config(default_config)
            return default_config

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # 누락된 키가 있으면 기본값으로 채움
                default = self.get_default_config()
                for key, value in default.items():
                    if key not in user_config:
                        user_config[key] = value
                return user_config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self.get_default_config()

    def save_config(self, new_config: Dict[str, Any]):
        try:
            # self.config를 먼저 업데이트
            self.config.update(new_config)
            
            # 파일에는 전체 config를 씀
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Configuration saved.")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key: str):
        # self.config에서 먼저 찾고, 없으면 기본값에서 찾음
        return self.config.get(key, self.get_default_config().get(key))

    def set(self, key: str, value: Any):
        self.save_config({key: value})
