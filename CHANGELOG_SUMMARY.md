# 변경사항 요약

최근 반영된 주요 변경은 아래와 같습니다.

## 1. 결과 조회 구조 분리

- `VIDEO_FILE`은 세그먼트 기반 조회 유지
- `WEBCAM`은 track 기반 저장/조회 구조 추가
- 세션 목록에서 `VIDEO_FILE`, `WEBCAM` 모두 조회 가능
- 조회 화면에서 세션 타입에 따라 세그먼트 목록 또는 추적 결과 목록으로 분기

## 2. 웹캠 실시간 분석 구조 정리

- 오른쪽 큰 실시간 화면 하나로 프리뷰/오버레이 통합
- 로컬 프리뷰와 서버 분석 결과를 분리
- 서버는 웹캠 실시간에서 이미지 재전송 대신 metadata 중심으로 응답
- 실시간 KPI는 런타임 세션 상태 기준으로 갱신

## 3. 웹캠 저장/조회 데이터 라인 추가

- `analysis_track_summary` 추가
- `analysis_frame`, `detection_result(track_id)` 보강
- 웹캠 결과는 세그먼트가 아니라 `session/frame/track` 기준으로 저장

## 4. 비디오 OCR 수행 조건 보정

- 프론트 점검 항목 선택값을 비디오 분석 요청에 포함
- 선택된 점검 항목 위반 프레임에서만 OCR 수행
- regex 미일치 시 같은 객체의 다음 위반 프레임에서 재시도
- 확정된 객체는 OCR 중단

## 5. 세그먼트 상세 표시 보정

- 세그먼트 상세/위반 유형은 세션 최종 상태가 아니라 세그먼트 상태 기준으로 표시
- 점검 항목이 여러 개일 때도 세그먼트 기준 위반 유형을 그대로 표시

## 6. 베스트 프레임 선정 로직 정리

- 세그먼트 종료 시점에 최종 대표 프레임 확정
- 현재 selector 우선순위:
  1. `violation_person_count`
  2. `confirmed_violation_person_count`
  3. 동률이면 더 이른 `frame_no`
- 세그먼트 종료 시 베스트 프레임 후보/선택 로그 추가

## 7. 프론트 UI 안정화

- 세션 클릭 시 첫 세그먼트/track 상세가 즉시 갱신되도록 수정
- 웹캠 미리보기 라벨 크기 고정으로 프리뷰 영역 비정상 확대 현상 완화

## 8. 서비스 DB 구조

- 공통 루트: `analysis_session`
- 비디오: `analysis_segment_summary`, `analysis_segment_person_result`
- 웹캠: `analysis_frame`, `detection_result`, `analysis_track_summary`
