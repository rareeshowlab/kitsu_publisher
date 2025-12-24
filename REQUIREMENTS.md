# Kitsu Batch Publisher

## 개요 (Overview)
CGWire의 Kitsu를 지원하는 로컬 웹 서버 애플리케이션입니다. 아티스트가 자신의 작업물(Shot) 동영상을 일괄적으로 업로드하고, 상태(Status)를 변경하며, 코멘트를 남길 수 있는 기능을 제공합니다.

## 핵심 목표 (Core Objectives)
1. **작업 효율화:** 한 번에 하나의 샷만 처리하는 기존 방식에서 벗어나, 다수의 샷을 일괄 처리(Batch Processing)하여 반복 작업을 줄입니다.
2. **자동화:** 로컬 파일 시스템을 스캔하여 샷 이름을 자동으로 파싱하고 매칭합니다.

## 주요 기능 (Key Features)

### 1. 인증 (Authentication)
- Kitsu 사용자 계정(Email/Password) 또는 API Key를 이용한 로그인.
- Kitsu 호스트 URL 설정 기능.

### 2. 파일 탐색 및 스캔 (File Discovery)
- 웹 UI를 통해 로컬 디렉토리 선택.
- 선택된 폴더 및 하위 폴더를 재귀적으로 스캔.
- 대상 포맷: `.mov`, `.mp4`.

### 3. 샷 매칭 (Shot Matching)
- 파일명에서 Shot Name을 추출하여 Kitsu DB의 샷 정보와 매칭.
- 매칭 실패 시 사용자에게 알림 또는 수동 매핑 지원(추후 고려).

### 4. 일괄 게시 (Batch Publishing)
- **Review:** 각 파일별 업로드 여부 체크박스 선택.
- **Comment:** 각 샷에 개별 코멘트 입력 가능.
- **Status:** 선택된 모든 샷의 상태(예: Retake -> Pending Review)를 일괄 변경 설정.
- **Upload:** 백그라운드에서 순차적/병렬적으로 동영상 업로드 및 정보 갱신.

## 기술 스택 제안 (Proposed Tech Stack)
- **Backend:** Python (FastAPI)
  - 이유: VFX 파이프라인 표준 언어이며, Kitsu 공식 라이브러리인 `gazu`가 Python 기반임. 로컬 파일 시스템 접근 용이.
  - **Tooling:** uv (Fast Python package installer and resolver)
- **Frontend:** Svelte (Vite/SvelteKit)
  - 이유: React보다 가볍고 문법이 직관적이며, 데이터 바인딩이 강력하여 상태 관리가 용이함.
  - **Tooling:** bun (Fast JavaScript runtime & package manager)
- **API Client:** Gazu (Python Kitsu Client)

## 워크플로우 (User Workflow)
1. 앱 실행 (Local Web Server Start).
2. 브라우저 접속 및 로그인.
3. 작업 폴더 경로 입력 또는 탐색.
4. 스캔된 파일 리스트 확인 (파일명, 예상 샷 이름 표시).
5. 업로드할 파일 선택.
6. 일괄 적용할 Status 선택 및 개별 Comment 입력.
7. "Publish" 버튼 클릭 -> 진행 상황(Progress Bar) 표시.
8. 완료 리포트 확인.
