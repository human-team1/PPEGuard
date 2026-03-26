# PPE Guard Backend 배포 가이드

## 배포 방식

기본 배포 대상은 사내망 서버이며, Docker 기준으로 운영합니다.

## 배포 설정 파일

- Docker 이미지 정의: [Dockerfile](Dockerfile)
- 컨테이너 실행 설정: [docker-compose.yml](docker-compose.yml)
- 환경변수 예시: [.env.example](.env.example)

## 배포 전 확인

### 1. 환경변수 준비

```powershell
cd backend
Copy-Item .env.example .env
```

운영 시 필수 점검:

- `PORT`
- `SERVICE_DATABASE_URI`
- `UPLOAD_DIR`
- `AI_DETECTOR_PROVIDER`
- `AI_OCR_PROVIDER`
- 고객 DB 연결값

## Docker 배포

```powershell
cd backend
docker-compose up -d --build
```

로그 확인:

```powershell
docker-compose logs -f
```

중지:

```powershell
docker-compose down
```

## 볼륨/저장 위치

현재 compose 기준:

- DB 파일: `./ppe_guard.db -> /app/ppe_guard.db`
- 업로드/결과 파일: `./uploads -> /app/uploads`

운영 환경에서는 이 경로의 백업/보존 정책을 별도로 가져가는 것이 안전합니다.

## 운영 체크리스트

- `/health` 응답 확인
- 업로드 디렉터리 쓰기 권한 확인
- 서비스 DB 생성 여부 확인
- 고객 DB 연동값 분리 관리 확인
- 방화벽에서 `5000` 포트 접근 정책 확인

## 주의사항

- 프론트가 고객 DB에 직접 접근하면 안 됩니다.
- 고객 환경마다 DB 스키마가 다를 수 있으므로, 고객 DB 연결값은 반드시 `.env`로 분리합니다.
- `AI_DETECTOR_PROVIDER`, `AI_OCR_PROVIDER`가 운영 모델 설정과 맞는지 확인해야 합니다.
