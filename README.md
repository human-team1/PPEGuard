# 🦺 PPE Guard

> 산업 안전 현장의 **PPE 착용 여부를 영상 분석과 OCR로 판별**하고,  
> **결과 저장 · 조회 · 이력 관리**까지 지원하는 **온프레미스 지향 PPE 점검 시스템**입니다.

---

## 📌 프로젝트 소개

**PPE Guard**는 산업 현장에서 작업자의 **개인 보호 장비(PPE) 착용 여부를 자동 점검**하기 위해 만든 영상 기반 분석 시스템입니다.

- 🎥 **동영상 파일 업로드 분석**
- 📷 **실시간 웹캠 입력 분석**
- 🔍 **PPE 탐지 + 작업자 번호 OCR 결합**
- 🗂️ **결과 조회 및 이력 관리**
- 🏢 **고객사 환경을 고려한 온프레미스 지향 구조**

---

## 🎯 문제 정의 / 해결 목표

산업 현장에서는 PPE 착용 여부를 사람이 직접 확인하는 경우가 많아  
**누락**, **지연**, **추적 한계**가 발생할 수 있습니다.

PPE Guard는 아래 문제 해결을 목표로 설계했습니다.

- PPE 착용 여부 점검의 **자동화**
- 실시간 분석과 사후 분석을 모두 지원하는 **유연한 입력 방식**
- PPE 탐지와 OCR을 결합한 **위반 이력 추적성 강화**
- 사내망에서도 운영 가능한 **온프레미스 배포 구조 확보**

---

## 🛠 기술 스택

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Backend-000000?logo=flask&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-Desktop_UI-41CD52?logo=qt&logoColor=white)
![YOLOv11](https://img.shields.io/badge/YOLOv11-Vision-FF6F00)
![EasyOCR](https://img.shields.io/badge/EasyOCR-OCR-7B1FA2)
![Socket.IO](https://img.shields.io/badge/Socket.IO-Realtime-010101?logo=socketdotio&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Service_DB-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-On--Prem_Deploy-2496ED?logo=docker&logoColor=white)

---

## 🏗 시스템 아키텍처

PPE Guard는 **프론트엔드 / 백엔드 / 서비스 DB / 고객사 DB**를 역할별로 분리한 구조입니다.

- **프론트엔드**
  - 영상 업로드
  - 웹캠 입력
  - 결과 조회

- **백엔드**
  - 분석 요청 처리
  - PPE 탐지 및 OCR 결합
  - 결과 저장 및 조회 API 제공

- **서비스 DB**
  - 세션, 프레임, 분석 결과, 이력 관리

이 구조를 통해 **보안성**, **운영 통제성**, **유지보수성**을 높이고자 했습니다.

---

## 🧩 백엔드 아키텍처

백엔드는 **Hexagonal Architecture** 기반으로 구성했습니다.

| 계층 | 설명 |
|------|------|
| **Presentation** | Flask API, Socket.IO 엔드포인트, 요청/응답 처리 |
| **Application** | 유스케이스 조합, 세션 처리, 분석 파이프라인 orchestration |
| **Domain** | PPE 판정 규칙, 엔티티, 포트 인터페이스 |
| **Infrastructure** | YOLO/EasyOCR 연동, 서비스 DB/고객사 DB 구현, 파일 저장 |

---

## 📸 대표 이미지

<img width="850" height="500" alt="화면 캡처 2026-03-27 190616" src="https://github.com/user-attachments/assets/76f24e29-2807-46ef-b764-6b3f24d6bde2" />
<img width="850" height="500" alt="화면 캡처 2026-03-27 190644" src="https://github.com/user-attachments/assets/eb82f985-ea8a-4736-8723-650167815539" />

---

## 🔄 주요 동작 흐름
``` text
입력(동영상 / 웹캠)
    ↓
백엔드 분석 요청
    ↓
YOLO 기반 PPE 탐지
    ↓
EasyOCR 기반 작업자 번호 인식
    ↓
결과 저장 (서비스 DB / 고객사 DB)
    ↓
프론트엔드 결과 조회 및 이력 확인
```


