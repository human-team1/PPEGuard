# PPE Guard Backend

PPE Guard 백엔드는 Flask API, Socket.IO, SQLite 기반 서비스 DB로 구성됩니다.  
로컬 개발과 테스트는 이 문서의 순서대로 진행하면 됩니다.

## 실행 전 준비사항

### 권장 버전

- Python `3.10.x`
- pip 최신 버전 권장

### 1. 가상환경 생성

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
.venv\Scripts\activate.bat
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. `.env` 파일 생성

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

### 4. DB 초기화

```bash
python -m app.infrastructure.service_db.init_db
```

초기화 후 `ppe_guard.db` 파일과 서비스용 테이블이 생성됩니다.

### 5. 서버 실행

```bash
python app.py
```

기본 확인 주소:

```text
http://127.0.0.1:5000/health
```

정상 응답 예시:

```json
{"status": "healthy"}
```

### 6. 테스트 실행

```bash
python -m pytest tests -v
```

`pytest`가 설치되어 있지 않으면 먼저 아래를 실행합니다.

```bash
pip install pytest
```

## 빠른 시작용 `.env` 예시

아래 값은 개발/테스트 공통 기준으로 바로 사용할 수 있는 예시입니다.

```env
FLASK_APP=app:create_app
FLASK_ENV=production
FLASK_RUN_PORT=5000
PORT=5000

SERVICE_DATABASE_URI=sqlite:///./ppe_guard.db
UPLOAD_DIR=uploads

AI_DETECTOR_PROVIDER=mock
AI_OCR_PROVIDER=mock

FRAME_INTERVAL_SEC=1
OCR_INTERVAL_SEC=1
SEGMENT_DURATION_SECONDS=10
ANALYSIS_FPS=1
MAX_CONCURRENT_SEGMENTS=2
VIDEO_PIPELINE_QUEUE_SIZE=4
YOLO_QUEUE_SIZE=4
OCR_QUEUE_SIZE=8

WEBCAM_CAPTURE_FPS=10
WEBCAM_ANALYSIS_FPS=3
WEBCAM_FRAME_QUEUE_SIZE=4
WEBCAM_EVENT_QUEUE_SIZE=8
WEBCAM_RESULT_WINDOW_SECONDS=10
WEBCAM_TRACK_EXPIRY_SECONDS=5
WEBCAM_MAX_TRACK_OCR_COUNT=6
SEGMENT_RESULT_TTL_SECONDS=10

YOLO_WORKER_COUNT=1
OCR_WORKER_COUNT=1

EMPLOYEE_NUMBER_REGEX=^[0-9]+$
EMPLOYEE_NO_REGEX=^[0-9]+$
EMPLOYEE_NO_MIN_LENGTH=3
EMPLOYEE_NO_MAX_LENGTH=10
EMPLOYEE_NUMBER_MIN_CONFIRM_COUNT=2
```

## 환경변수 설명

아래 항목은 현재 코드 기준으로 성능과 동작에 직접 영향을 줍니다.

| 변수 | 기본값 | 의미 | 값을 줄이면 | 값을 키우면 | 성능 관련 주의사항 |
|---|---:|---|---|---|---|
| `FRAME_INTERVAL_SEC` | `1` | 세션 메타데이터용 프레임 간격 값 | 메타데이터 숫자만 작아짐 | 메타데이터 숫자만 커짐 | 비디오 실제 샘플링 기준은 아님 |
| `OCR_INTERVAL_SEC` | `1` | 동일 인물 OCR 재시도 최소 간격(초) | OCR 재시도 빈도 증가 | OCR 재시도 빈도 감소 | 너무 작으면 OCR CPU 사용률 급증 |
| `SEGMENT_DURATION_SECONDS` | `10` | 비디오/웹캠 결과 저장 구간 길이 | 저장 이벤트 빈도 증가 | 저장 이벤트 빈도 감소 | 너무 짧으면 DB/IO 부하 증가 |
| `ANALYSIS_FPS` | `1` | 비디오 분석 샘플링 FPS | 분석 프레임 수 감소 | 분석 프레임 수 증가 | 값이 커질수록 YOLO/OCR 둘 다 부하 증가 |
| `MAX_CONCURRENT_SEGMENTS` | `2` | 비디오 세그먼트 병렬 처리 상한 | 동시 처리량 감소 | 동시 처리량 증가 | CPU/RAM 여유 없으면 오히려 느려질 수 있음 |
| `VIDEO_PIPELINE_QUEUE_SIZE` | `4` | 비디오 세그먼트 task/result 큐 상한 | backlog가 더 빨리 버려짐/막힘 | backlog 허용량 증가 | 무한 누적 방지용, 너무 크게 잡지 않는 편이 안전 |
| `YOLO_QUEUE_SIZE` | `4` | YOLO 작업 큐 상한 | YOLO 대기열 축소 | YOLO 대기열 증가 | 너무 크게 잡으면 메모리 사용량 증가 |
| `OCR_QUEUE_SIZE` | `8` | OCR 작업 큐 상한 | OCR backlog 축소 | OCR backlog 증가 | OCR 병목이 큰 환경에서는 크게 잡지 않는 편이 좋음 |
| `WEBCAM_CAPTURE_FPS` | `10` | 프론트에서 서버로 보내는 웹캠 프레임 목표 FPS | 전송량 감소 | 전송량 증가 | 네트워크/인코딩 부하에 직접 영향 |
| `WEBCAM_ANALYSIS_FPS` | `3` | 웹캠 분석용 실제 샘플링 FPS | 실시간성은 다소 낮아짐 | 분석 반응성 증가 | OCR 수행 기회도 함께 늘어 CPU 사용량 상승 가능 |
| `WEBCAM_FRAME_QUEUE_SIZE` | `4` | 웹캠 프레임 큐 상한 | 오래된 프레임이 더 자주 버려짐 | backlog 허용량 증가 | 실시간 우선이면 크게 키우지 않는 편이 적절 |
| `WEBCAM_EVENT_QUEUE_SIZE` | `8` | 웹캠 이벤트 큐 상한 | 이벤트 드롭 가능성 증가 | 이벤트 backlog 증가 | 너무 크면 미리보기/요약 이벤트가 밀릴 수 있음 |
| `WEBCAM_RESULT_WINDOW_SECONDS` | `10` | 웹캠 PPE/OCR 집계 윈도우 길이 | 최근 변화에 민감 | 더 안정적인 집계 | 길수록 track state 메모리 유지 시간이 길어짐 |
| `WEBCAM_TRACK_EXPIRY_SECONDS` | `5` | 일정 시간 미감지 track 정리 기준 | track state가 빨리 제거됨 | track state가 오래 남음 | 크게 잡으면 장시간 메모리 유지 가능 |
| `WEBCAM_MAX_TRACK_OCR_COUNT` | `6` | 동일 track OCR 최대 시도 횟수 | OCR 부하 감소 | OCR 확정 기회 증가 | OCR 병목 완화에 가장 직접적 |
| `SEGMENT_RESULT_TTL_SECONDS` | `10` | OCR/PPE 캐시 TTL | 캐시가 빨리 사라짐 | 캐시가 오래 유지됨 | 크게 잡으면 track/segment 메모리 유지량 증가 |
| `YOLO_WORKER_COUNT` | `1` | YOLO 워커 수 | 추론 병렬성 감소 | 추론 병렬성 증가 | CPU/GPU 자원과 모델 특성에 맞춰 조정 필요 |
| `OCR_WORKER_COUNT` | `1` | OCR 워커 수 | OCR 동시 실행 수 감소 | OCR 동시 실행 수 증가 | 현재 가장 민감한 CPU 병목 포인트 |
| `EMPLOYEE_NUMBER_REGEX` | `^[0-9]+$` | 직원번호 유효성 정규식 | 허용 범위가 좁아짐 | 허용 범위가 넓어짐 | 너무 느슨하면 오인식 확정 가능성 증가 |
| `EMPLOYEE_NO_REGEX` | `^[0-9]+$` | 레거시 호환용 직원번호 정규식 | 동일 | 동일 | 현재는 `EMPLOYEE_NUMBER_REGEX`와 같은 의미로 사용 |
| `EMPLOYEE_NO_MIN_LENGTH` | `3` | OCR 후보 최소 길이 | 짧은 번호 배제 | 짧은 번호 허용 | 잘못 낮추면 오인식 증가 |
| `EMPLOYEE_NO_MAX_LENGTH` | `10` | OCR 후보 최대 길이 | 긴 번호 배제 | 긴 번호 허용 | 잘못 높이면 노이즈 허용 가능 |
| `EMPLOYEE_NUMBER_MIN_CONFIRM_COUNT` | `2` | 동일 값 반복 등장 시 확정 횟수 | 더 빨리 확정 | 더 늦게 확정 | 정확도와 응답 속도 사이의 핵심 값 |

## 성능 튜닝 가이드

### 핵심 포인트

- 현재 병목은 대체로 OCR 구간에서 가장 크게 발생합니다.
- OCR 수행 시점에는 CPU 사용률이 순간적으로 높아질 수 있습니다.
- 기본값은 안정성 우선 기준입니다. 고성능 장비 기준 최대 처리량을 노린 값이 아닙니다.

### 저사양 PC에서 먼저 조정할 값

1. `OCR_WORKER_COUNT`
2. `WEBCAM_ANALYSIS_FPS`
3. `WEBCAM_MAX_TRACK_OCR_COUNT`
4. `WEBCAM_FRAME_QUEUE_SIZE`
5. `OCR_INTERVAL_SEC`

권장 방향:

- CPU가 과하게 튀면 `OCR_WORKER_COUNT`를 유지하거나 낮춥니다.
- 웹캠이 버벅이면 `WEBCAM_ANALYSIS_FPS`를 낮춥니다.
- OCR이 너무 자주 돌면 `WEBCAM_MAX_TRACK_OCR_COUNT`를 낮추고 `OCR_INTERVAL_SEC`를 높입니다.
- backlog를 쌓기보다 오래된 프레임을 제한적으로 버리는 편이 실시간성 유지에 더 적절합니다.

### 상황별 권장 예시

실시간성 우선:

```env
WEBCAM_ANALYSIS_FPS=2
WEBCAM_FRAME_QUEUE_SIZE=2
WEBCAM_MAX_TRACK_OCR_COUNT=3
OCR_WORKER_COUNT=1
OCR_INTERVAL_SEC=2
```

정확도 우선:

```env
WEBCAM_ANALYSIS_FPS=4
WEBCAM_FRAME_QUEUE_SIZE=4
WEBCAM_MAX_TRACK_OCR_COUNT=6
OCR_WORKER_COUNT=1
OCR_INTERVAL_SEC=1
```

비디오 처리량 우선:

```env
ANALYSIS_FPS=1
MAX_CONCURRENT_SEGMENTS=2
VIDEO_PIPELINE_QUEUE_SIZE=4
YOLO_WORKER_COUNT=1
OCR_WORKER_COUNT=1
```

## 자주 발생하는 설정 실수

- `.env`를 만들지 않고 실행하는 경우
- DB 초기화 전에 서버를 먼저 실행하는 경우
- `OCR_WORKER_COUNT`만 올리고 `OCR_INTERVAL_SEC`는 그대로 둬 CPU가 급격히 치솟는 경우
- `WEBCAM_FRAME_QUEUE_SIZE`를 너무 크게 잡아 실시간성이 떨어지는 경우
- `ANALYSIS_FPS`와 `WEBCAM_ANALYSIS_FPS`를 같은 의미로 착각하는 경우
  - `ANALYSIS_FPS`: 비디오 경로
  - `WEBCAM_ANALYSIS_FPS`: 웹캠 경로
- `FRAME_INTERVAL_SEC`를 실제 샘플링 기준으로 오해하는 경우
  - 현재는 세션 메타데이터 성격이 더 강합니다

## 운영 메모

- 디버그 프레임 저장은 기본 운영 구조가 아닙니다.
- 웹캠 경로는 backlog 무한 누적보다 bounded queue와 제한적 드롭을 우선합니다.
- OCR 병목이 발생하면 우선 OCR 관련 값부터 조정하고, 그 다음 FPS/큐 크기를 조정하는 순서를 권장합니다.

## 주요 API

| Method | Endpoint | 설명 |
|---|---|---|
| `GET` | `/health` | 서버 상태 확인 |
| `POST` | `/api/v1/sessions` | 분석 세션 생성 |
| `POST` | `/api/v1/video` | 비디오 업로드 및 분석 시작 |
| `GET` | `/api/v1/sessions/{id}` | 세션 조회 |
| `GET` | `/api/v1/sessions/{id}/segments` | 세그먼트 결과 조회 |
| `GET` | `/api/v1/sessions/{id}/results` | 결과 조회 |
| `POST` | `/api/v1/sessions/{id}/stop` | 세션 중지 |

## Docker 실행

```bash
docker-compose up -d --build
docker-compose logs -f
```

운영 시에도 `.env` 값이 실제 처리량과 CPU 사용률에 직접 영향을 줍니다.  
특히 OCR 관련 값은 개발 환경과 운영 환경을 분리해서 관리하는 편이 안전합니다.
## 로그 정책

- 기본 로그 레벨은 `.env`의 `LOG_LEVEL=INFO` 입니다.
- 운영 기본값 `INFO`에서는 서버 시작/종료, 세션 시작/종료, 세그먼트 저장, DB 저장, OCR 최종 확정, 큐 드롭 경고, 예외만 남깁니다.
- `DEBUG`로 올리면 실시간 이벤트 수신, KPI 갱신, best frame 갱신 같은 상세 추적 로그를 추가로 볼 수 있습니다.
- 프레임마다 반복되는 진행 로그, OCR 1회당 상세 로그, payload 전체 dump는 운영 기본값에서 남기지 않습니다.

```env
LOG_LEVEL=INFO
```
