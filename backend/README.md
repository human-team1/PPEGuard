# PPE Guard Backend 개발환경

## 개요

백엔드는 Flask API, Socket.IO, 서비스 소유 SQLite DB로 구성됩니다.

주요 역할:

- 비디오 업로드 분석
- 웹캠 실시간 분석 세션 처리
- 결과 저장/조회 API 제공
- 고객 DB 연동 포인트 제공

## 권장 버전

- Python `3.10.x`
- pip 최신 버전 권장

## 빠른 시작

### 1. 가상환경 생성

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. 패키지 설치

```powershell
pip install -r requirements.txt
```

### 3. 환경설정 파일 준비

```powershell
Copy-Item .env.example .env
```

필수 확인 항목:

- `SERVICE_DATABASE_URI`
- `UPLOAD_DIR`
- `AI_DETECTOR_PROVIDER`
- `AI_OCR_PROVIDER`
- 고객 DB 연동값

### 4. 서비스 DB 초기화

```powershell
python -m app.infrastructure.service_db.init_db
```

### 5. 서버 실행

```powershell
python app.py
```

확인:

```text
http://127.0.0.1:5000/health
```

정상 응답 예시:

```json
{"status":"healthy"}
```

## 개발 중 자주 보는 파일

- 앱 시작점: [app.py](app.py)
- 환경설정: [config/settings.py](config/settings.py)
- 배포 예시 환경변수: [.env.example](.env.example)
- Docker 배포: [docker-compose.yml](docker-compose.yml)

## 테스트

```powershell
python -m pytest tests -v
```

`pytest`가 없으면:

```powershell
pip install pytest
```

## 개발환경 핵심 설정

### 비디오 분석

- `SEGMENT_DURATION_SECONDS`
- `ANALYSIS_FPS`
- `MAX_CONCURRENT_SEGMENTS`
- `YOLO_WORKER_COUNT`
- `OCR_WORKER_COUNT`

### 웹캠 분석

- `WEBCAM_CAPTURE_FPS`
- `WEBCAM_ANALYSIS_FPS`
- `WEBCAM_FRAME_QUEUE_SIZE`
- `WEBCAM_MAX_TRACK_OCR_COUNT`

### OCR/직원번호

- `OCR_INTERVAL_SEC`
- `EMPLOYEE_NUMBER_REGEX`
- `EMPLOYEE_NO_MIN_LENGTH`
- `EMPLOYEE_NO_MAX_LENGTH`
- `EMPLOYEE_NUMBER_MIN_CONFIRM_COUNT`

## 현재 구조 요약

- `VIDEO_FILE`: 파일 기반 세그먼트 분석/저장/조회
- `WEBCAM`: session/frame/track 기반 실시간 분석 및 저장 조회

## 참고 문서

- 배포 문서: [DEPLOYMENT.md](DEPLOYMENT.md)
- 변경사항 요약: [../CHANGELOG_SUMMARY.md](../CHANGELOG_SUMMARY.md)
