# PPE Guard Frontend 배포 가이드

## 배포 방식

프론트는 Windows 데스크톱 클라이언트 기준으로 패키징합니다.

## 배포 설정 파일

- 패키징 설정: [PPEGuard_Client.spec](PPEGuard_Client.spec)
- 런타임 설정 저장 코드: [app/config/settings.py](app/config/settings.py)

## 패키징

PyInstaller가 설치되어 있지 않으면 먼저 설치합니다.

```powershell
cd frontend
.venv\Scripts\Activate.ps1
pip install pyinstaller
```

빌드:

```powershell
pyinstaller PPEGuard_Client.spec
```

출력 경로:

- 실행 파일 묶음: `frontend/dist/PPEGuard_Client`

## 배포 전 확인

- 대상 PC에서 백엔드 서버 URL 접근 가능 여부
- 카메라 장치 권한
- 사내망 방화벽 정책
- 백엔드와 버전 호환 여부

## 운영 설정

프론트는 최초 실행 후 GUI에서 서버 URL을 저장합니다.

기본 URL:

```text
http://127.0.0.1:5000
```

사내 배포 시에는 사용자 매뉴얼에 아래를 포함하는 것이 좋습니다.

- 서버 주소 입력 방법
- 연결 테스트 방법
- 비디오 분석 절차
- 웹캠 분석 절차
- 결과 조회 절차

## 주의사항

- 프론트는 고객 DB에 직접 접근하지 않습니다.
- 서버 URL은 환경마다 다를 수 있으므로 코드 하드코딩보다 GUI 저장 방식을 유지합니다.
- 웹캠 실시간 분석은 백엔드 소켓 연결이 살아 있어야 합니다.
