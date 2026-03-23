import cv2
from typing import Dict, Any
from app.domain.entities.person import Person

class RealTimeVisualizer:
    """
    실시간 분석 결과 시각화를 담당하는 클래스 (Infrastructure 계층)
    프로젝트의 시각화 효과.
    """
    
    # 색상 정의 (BGR 형식)
    COLOR_SAFE = (0, 255, 0)      # 초록색
    COLOR_WARNING = (0, 255, 255)  # 노란색
    COLOR_DANGER = (0, 0, 255)     # 빨간색
    COLOR_VEST = (0, 255, 255)    # 노란색 (조끼 세부박스)
    COLOR_HELMET = (255, 255, 0)  # 하늘색 (헬멧 세부박스)

    def draw(self, frame, active_persons: Dict[int, Person]):
        """
        프레임 위에 사람 및 장구류 박스를 그리고 상태를 표시합니다.
        """
        for pid, p in active_persons.items():
            # 1. 상태에 따른 메인 박스 색상 결정 (son의 3단계 색상 로직)
            if p.is_safe():
                color = self.COLOR_SAFE
            elif p.violation_count < 5:
                color = self.COLOR_WARNING
            else:
                color = self.COLOR_DANGER

            x1, y1, x2, y2 = p.bbox
            
            # 2. 메인 사람 박스 그리기 (두께 4)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 4)

            # 3. 상세 정보 텍스트 (상단)
            status_txt = f"ID:{pid} | V:{'O' if p.has_vest else 'X'} H:{'O' if p.has_helmet else 'X'}"
            cv2.putText(frame, status_txt, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # 4. 위반 카운트가 있는 경우 하단에 표시 (DANGER 상태 강조)
            if p.violation_count > 0:
                cv2.putText(frame, f"V-Count: {p.violation_count}", (x1, y2 + 25), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_DANGER, 1)

            # 5. 매핑된 조끼 박스 표시 (얇게)
            if p.has_vest and p.vest_bbox:
                vx1, vy1, vx2, vy2 = p.vest_bbox
                cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), self.COLOR_VEST, 1)

            # 6. 매핑된 헬멧 박스 표시 (얇게)
            if p.has_helmet and p.helmet_bbox:
                hx1, hy1, hx2, hy2 = p.helmet_bbox
                cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), self.COLOR_HELMET, 1)

        return frame
