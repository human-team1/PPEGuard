# PPE Guard Desktop Client

PPE Guard(사내망 헬멧/작업조끼 인식 시스템)의 PC용 GUI 프론트엔드 프로그램입니다.
객체 판별(AI) 모델 로직 없이 사내망의 `Flask Backend API` 와 통신하여 원격으로 영상을 입력하고 분석 결과를 시각화합니다.

---

## 💻 1. [개발자용] 개발 인프라 기반 실행 절차

소스 코드를 수정하거나, 개발자가 직접 소스 단에서 점검을 위해 실행할 때의 방식입니다. **Python 및 가상환경(venv) 구성이 필수적입니다.**

1. 터미널을 열고 `frontend` 폴더로 이동합니다.
2. 파이썬 가상환경 생성 및 활성화
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows PowerShell 기준
   ```
3. 필수 개발 모듈 설치 및 프로그램 구동
   ```bash
   pip install -r requirements.txt
   python main.py
   ```

---

## 📦 2. [프로덕션 빌드/배포자용] PyInstaller 독립 패키징 절차 및 체크리스트

최종 사용자에게 파이썬 설치 없이, 클릭만으로 동작하는 배포본(`.exe`)을 만들기 위한 빌드 기준입니다. 
**반드시 아래 절차를 준수하여 묶여야 `No module named PySide6` 같은 의존성 유출 배포 사고가 발생하지 않습니다.**

### 2.1 빌드 전 필수 체크 사항 (가상환경 격리)
1. 🚨 **반드시 가상환경(`.venv`)이 활성화된 상태**여야 합니다. 전역(Global) 환경에서 빌드를 시도하면 모듈 색인이 엇갈려 빈 껍데기만 빌드됩니다.
2. 해당 셸 환경에서 `pip list`를 쳐서 `PySide6`, `opencv-python`, `requests` 및 `pyinstaller`가 모두 리스트에 들어 있는지 육안으로 확인하세요.

### 2.2 빌드 스크립트 실행
```bash
# 콘솔 창 은닉 및 폴더(onedir) 기반 응축 형태로 빌드 지시
pyinstaller --noconsole --name PPEGuard_Client main.py
```
*빌드가 완료되면 `dist/PPEGuard_Client/` 묶음 폴더가 생성됩니다.*

### 2.3 배포 전 1회 검증 필수 (QA)
- 만들어진 `dist/PPEGuard_Client/PPEGuard_Client.exe`를 파이썬이나 개발 관련 환경 변수가 **아예 없는 완전히 독립된 테스트 PC 혹은 윈도우 샌드박스**에서 1회 실행(더블클릭)해 보십시오.
- **실패 판정**: 만약 실행 시 `No module named PySide6` 등의 에러가 발생하면 빌드가 엇갈린 불량 배포본입니다. 기존 `build`, `dist` 폴더를 삭제하고 `2.1`의 가상환경 점검부터 다시 진행해야 합니다.
- **최종 배포 방식**: 클リーン PC 실행 검증이 통과된 정상 동작본에 한해, `dist/PPEGuard_Client/` 폴더 **전체를 하나의 묶음**(`.zip`)으로 사용자에게 공유합니다.

---

## 3. 프론트엔드 구동을 위한 백엔드 응답 규약 (기대 스펙)
이 프로그램이 멈춤이나 오류 없이 동작하기 위해 **프론트는 내부적으로 백엔드가 아래와 같은 JSON 응답을 돌려줄 것을 기대**하고 파싱하도록 작성되었습니다. (향후 백엔드 개발 시 참고)

*   `GET /health`: JSON `{"status": "healthy"}`를 즉각 반환할 것.
*   `POST /api/v1/sessions`: body 데이터 수신 후, 화면 록(Lock) 해제를 위해 즉각 `session_id`와 초기화 `status`를 반환할 것.
*   `GET /api/v1/results`: 프론트에서 재정렬 하지 않으므로 서버 DB에서 사전 최신순 정렬(Order by desc)된 배열을 제공할 것.
*   `GET /api/v1/results/{id}`: 상세 조회 폼 규격에 맞는 필드와, 로컬 렌더링에 필요한 `image_path` 데이터 문자열을 제공할 것.

## 4. MVP 버전의 알려진 제한사항 (Known Limitations)
1. 🚨 **[위험] 단순 경로명 기반 비디오 전송 (임시)**: 현재 분석 API 호출 시 대용량 파일 바이너리 스트림(Multipart) 송신 구조가 아닙니다. `source_name` 필드에 시스템 상의 **로컬 파일 경로 문자열**만 보냅니다. 이는 MVP용 임시 우회 구조이며, 추후 정식 업그레이드 때 실질적인 파일 스트림 업로드 아키텍처로 개편해야 합니다. (이 경로 전송 방식을 확정 스펙으로 삼지 마십시오.)
2. **보안 체계 부재**: 사내망 통제 환경(On-premise)이 전제이므로 HTTPS 보안 프로토콜 및 토큰 로그인(Auth) 계층이 프론트에 설계되어 있지 않습니다.
