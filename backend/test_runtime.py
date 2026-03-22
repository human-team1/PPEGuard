# yolo test


import cv2
import sys
import os

# 프로젝트 루트 경로 추가 (app 모듈 임포트 가능하도록)
sys.path.append(os.getcwd())

from app.infrastructure.ai.yolo_detector import YoloDetector
from app.application.analyze_worker import AnalyzeWorker
from app.infrastructure.ai.visualizer import RealTimeVisualizer  # 신규 시각화 모듈

from dataclasses import asdict


def test_start():
    # 1. 인프라 계층 초기화 (YOLOv11 가중치 및 트래커 설정 로드)
    model_path = os.path.join("app", "infrastructure", "ai", "models", "best.pt")
    tracker_config = os.path.join("app", "infrastructure", "ai", "configs", "bytetrack.yaml")
    
    # 설정값
    # STRIDE = 30 
    STRIDE = 90 
    
    if not os.path.exists(model_path):
        print(f"[오류] 모델 파일을 찾을 수 없습니다: {model_path}")
        return

    try:
        detector = YoloDetector(model_path=model_path, tracker_config=tracker_config)
    except Exception as e:
        print(f"[초기화 오류] {e}")
        return

    # 2. 애플리케이션 계층 초기화
    worker = AnalyzeWorker(detector=detector)
    # 3. 실시간 시각화 도구 초기화
    visualizer = RealTimeVisualizer()

    # 4. OpenCV 웹캠 연결
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[오류] 카메라를 열 수 없습니다.")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("\n" + "="*60)
    print("   PPE Guard 공식 아키텍처 실시간 모니터링 테스트 (v1.0)")
    print(f"   - Stride: {STRIDE} (성능 최적화 모드)")
    print("   - 종료하려면 'q' 키를 누르세요.")
    print("="*60 + "\n")

    frame_count = 0
    active_persons = {}

    while cap.isOpened():
        success, frame = cap.read()
        if not success: break
        
        frame_count += 1

        # 5. 인텔리전트 스트라이드 (Stride 마다 분석 수행)
        if frame_count % STRIDE == 0:
            # 탐지 -> 매핑 -> 판정의 전체 유즈케이스 실행
            active_persons = worker.run_inference(frame)
            
            # 터미널 상세 정보 출력 (사용자 요청: BBox 좌표 포함)
            if active_persons:
                print(f"\n[Frame {frame_count:5}] --- 실시간 분석 데이터 상세 ---")
                for pid, p in active_persons.items():
                    status = "SAFE" if p.is_safe() else f"V-COUNT({p.violation_count})"
                    
                    # 데이터 상태를 딕셔너리로 변환하여 전체 출력 (검증용)
                    debug_data = asdict(p)
                    # 이미지 데이터는 가독성을 위해 제외하고 출력
                    debug_data.pop('crop_image', None)
                    print(f"[DEBUG-ID:{pid}] {debug_data}")
                                    
                    
                    print(f" > [ID {pid:2}] Status: {status:12} | P-BBox: {p.bbox}")
                    
                    # 크롭 이미지 존재 여부 확인 (신규 추가 로그)
                    if p.crop_image is not None:
                        ch, cw = p.crop_image.shape[:2]
                        print(f"   ㄴ [CROP]   ROI Size: {cw}x{ch}")

                    if p.has_vest:
                        print(f"   ㄴ [VEST]   BBox: {p.vest_bbox} (Conf: {p.vest_confidence:.2f})")
                    if p.has_helmet:
                        print(f"   ㄴ [HELMET] BBox: {p.helmet_bbox} (Conf: {p.helmet_confidence:.2f})")
                print("-" * 50)

        # 6. 정교화된 시각화 (매 프레임)
        # son 프로젝트의 화려한 박스 효과를 동일하게 적용합니다.
        frame = visualizer.draw(frame, active_persons)

        cv2.imshow("PPE_Guard_RealTime_Monitor", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_start()

