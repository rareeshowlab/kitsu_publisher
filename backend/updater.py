import requests
import logging
import webbrowser
from packaging import version
from version import VERSION, REPO_OWNER, REPO_NAME

logger = logging.getLogger("kitsu_publisher")

class Updater:
    def __init__(self):
        self.current_version = VERSION
        self.github_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

    def check_for_updates(self):
        try:
            logger.info(f"Checking for updates... (Current: {self.current_version})")
            # 타임아웃 3초 설정 (앱 실행 속도 저하 방지)
            response = requests.get(self.github_url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "").lstrip("v")
                html_url = data.get("html_url", "")
                
                if not latest_tag:
                    return {"update_available": False}

                # 버전 비교 (packaging 라이브러리 사용 권장하나, 없으면 문자열 비교)
                if version.parse(latest_tag) > version.parse(self.current_version):
                    logger.info(f"New version found: {latest_tag}")
                    return {
                        "update_available": True,
                        "current_version": self.current_version,
                        "latest_version": latest_tag,
                        "download_url": html_url
                    }
            
            return {"update_available": False, "current_version": self.current_version}
            
        except Exception as e:
            logger.warning(f"Failed to check updates: {e}")
            return {"update_available": False, "error": str(e), "current_version": self.current_version}

    def open_download_page(self, url):
        webbrowser.open(url)
