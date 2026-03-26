# PPE Guard Frontend 개발환경

## 개요

프론트는 PySide6 기반 데스크톱 클라이언트입니다.

주요 역할:

- 서버 연결
- 입력 소스 선택
- 비디오 업로드 분석 요청
- 웹캠 실시간 분석 시작/중지
- 저장 결과 조회

## 권장 버전

- Python `3.10.x`
- 백엔드 서버 선실행 권장

## 빠른 시작

### 1. 가상환경 생성

```powershell
cd frontend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. 패키지 설치

```powershell
pip install -r requirements.txt
```

### 3. 클라이언트 실행

```powershell
python main.py
```

## 개발 시 확인 순서

1. 백엔드 실행
2. 프론트 실행
3. 서버 연결 테스트
4. 비디오 또는 웹캠 분석 확인
5. 결과 조회 확인

## 프론트 설정 방식

프론트는 별도 `.env` 파일 대신 `QSettings`를 사용합니다.

저장되는 주요 항목:

- 서버 URL
- 선택된 점검 항목
- 대시보드 표시 항목
- 결과 표 표시 컬럼

관련 파일:

- 설정 저장: [app/config/settings.py](app/config/settings.py)
- 실행 진입점: [main.py](main.py)
- 패키징 설정: [PPEGuard_Client.spec](PPEGuard_Client.spec)

## 확인 포인트

### 비디오 분석

- 업로드 요청 성공
- 진행 상태 표시
- 세그먼트 목록 조회
- 세그먼트 상세/베스트 프레임 표시

### 웹캠 분석

- 실시간 프리뷰 표시
- bbox 오버레이 표시
- KPI 갱신
- 분석 시작/중지 반복 시 UI 안정성

## 참고 문서

- 배포 문서: [DEPLOYMENT.md](DEPLOYMENT.md)
- 변경사항 요약: [../CHANGELOG_SUMMARY.md](../CHANGELOG_SUMMARY.md)
