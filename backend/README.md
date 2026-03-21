# PPE Guard Backend

본 프로젝트는 온프레미스(사내망) 환경에 구축되는 **기업용 PPE(개인보호구) 착용 상태 검사 솔루션**입니다.

## 1. 프로젝트 개요
- **핵심 역할**: 영상(또는 웹캠) 프레임 기반 객체 탐지 로그를 생성하고 세션별 검출 상태(안전모, 작업조끼 등)를 관리합니다.
- **아키텍처**: 유지보수와 확장을 고려한 클린 아키텍처 기반 분리 구조 (Domain - Application - Infrastructure - Presentation).
- **데이터베이스 (MVP 기준)**: 앱 내장 SQLite (`ppe_guard.db`) 파일 기반 동작. 향후 고객사 마스터 DB 연동 확장 대응.

---

## 2. 환경 설정 가이드

### 2.1 가상환경 구성 (개발 및 테스트용)
```bash
python -m venv .venv

# Windows 시스템
.venv\Scripts\activate

# Linux / Mac 시스템
source .venv/bin/activate

# 의존성 패키지 설치
pip install -r requirements.txt
```

### 2.2 `.env` 설정
프로젝트 최상단 폴더에 `.env.example` 파일을 복사하여 `.env` 를 생성합니다.
```bash
cp .env.example .env
```
_(기본적으로 `sqlite:///./ppe_guard.db` 환경 및 포트 5000으로 설정됩니다.)_

---

## 3. 실행 방법 (Local)

### 3.1 DB 초기화 
먼저 관리용 서비스 DB 파일과 내부 테이블을 최초 1회 생성해야 합니다.
```bash
python -m app.infrastructure.db.init_db
```
*(성공 시 `ppe_guard.db` 파일이 생성됩니다.)*

### 3.2 서버 실행
DB 준비가 완료된 후 Flask API 서버를 구동합니다.
```bash
python app.py
```
*(기본 실행 확인 주소: `http://localhost:5000/health`)*

### 3.3 자동 테스트 (pytest) 적용
사전에 구성된 API 검증 및 레포지토리 저장/조회 테스트 스냅샷을 통과하는지 검증합니다. 
(독립 단위 테스트용 `test_ppe_guard.db` 파일이 사용 중 생성 및 삭제되어 운영 DB를 오염시키지 않습니다.)
```bash
python -m pytest tests -v
```

---

## 4. Docker 배포 방법 (Production / On-Premise)

고객사 내부망(On-Premise) 도커 배포를 기준으로 구성되어 있습니다.

```bash
# 백그라운드 서버 구동 및 컨테이너 빌드
docker-compose up -d --build

# 실행 로그 모니터링
docker-compose logs -f
```

- 실행 시 호스트의 `.env` 환경 변수가 컨테이너로 매핑됩니다.
- 내부 `ppe_guard.db` 파일과 `uploads/` 스토리지 디렉토리는 도커 컴포즈 상에서 볼륨(`volumes`)으로 영속 마운트 처리되어 컨테이너 재가동 혹은 내부망 재투입 시에도 데이터가 유지됩니다. (`Dockerfile` 환경은 Python 3.10.6 버전을 기준으로 이미지를 설계했습니다.)

---

## 5. 주요 API 목록

| Method | Endpoint | 설명 |
|---|---|---|
| `GET` | `/health` | 서버 동작 상태 (헬스 체크) |
| `POST` | `/api/v1/sessions` | 신규 분석 세션 생성 (JSON Body: `source_type`, `frame_interval_sec` 등) |
| `GET` | `/api/v1/sessions/{id}` | 생성된 분석 세션 메타정보 리턴 |
| `POST` | `/api/v1/sessions/{id}/stop` | 진행 중인 분석 세션 상태 `STOPPED` 처리 |
| `GET` | `/api/v1/results` | 전체 탐지 결과 목록 (최신순 정렬, `?limit=N` 쿼리 가능) |
| `GET` | `/api/v1/results/{id}` | 특정 탐지 결과 단건 응답 반환 |
| `GET` | `/api/v1/sessions/{id}/results` | 특정 분석 세션에 참조된 내부 Detection Result 전량 묶음 조회 |
