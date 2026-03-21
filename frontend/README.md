# PPE Guard Desktop Client

PPE Guard(사내망 헬멧/작업조끼 인식 시스템)의 PC용 GUI 프론트엔드 프로그램입니다.
고객사의 통제된 네트워크 내부 환경(On-Premise)에서 운영되는 것을 목적으로 만들어졌습니다.

## 1. 프로젝트 개요 및 구조
이 데스크톱 애플리케이션은 **객체 판별(AI) 모델 로직이나 DB 직접 조작 로직을 포함하지 않습니다**.  
사내망에 띄워진 `PPE Guard Flask Backend API` 와 통신하여 영상을 입력하고 원격 분석 결과를 시각화하여 조회하는 역할만 수행합니다.

- **프레임워크**: PySide6 기반 데스크톱 GUI
- **비동기 처리**: UI 프리징 방지를 위해 `QThread` 기반 OpenCV 및 `requests` API 통신 워커 구현
- **설정 관리**: `QSettings` 를 통한 단일 서버 URL 캐싱 기능

## 2. 개발 환경 실행 절차

팀원 혹은 인프라 담당자가 로컬 파이썬(Python 3.10+) 코드로 바로 실행할 때의 방법입니다.

1. 터미널을 열고 `frontend` 폴더로 이동합니다.
2. 가상환경 생성 및 활성화
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. 필수 모듈 설치 및 프로그램 구동
   ```bash
   pip install -r requirements.txt
   python main.py
   ```

## 3. PyInstaller 패키징 기준 (.exe 빌드)

일반 사용자 배포 시 파이썬 가상환경 세팅 없이 클릭만으로 작동하는 **폴더 단위 독립 실행본** 제작을 원칙으로 합니다. (실행 딜레이 및 리소스 로드 안정성을 위해 단일 파일(--onefile) 방식은 지양합니다.)

### 빌드 스크립트 실행
```bash
# 가상환경이 켜지고 모든 요구사항이 설치된 상태에서 실행
pip install pyinstaller

# 폴더(onedir) 기반 콘솔 창 숨김 형태 빌드 적용
pyinstaller --noconsole --name PPEGuard_Client main.py
```

*빌드가 완료되면 `dist/PPEGuard_Client/` 폴더가 생성됩니다. 배포 시 **해당 폴더 전체를 압축**하여 고객사 PC에 전달해야 합니다.*
