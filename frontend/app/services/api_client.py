import requests
from typing import Dict, Any

class ApiClient:
    """Flask 백엔드와 통신하는 API 클라이언트"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        
    def update_base_url(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        
    def _handle_request_error(self, e: Exception, action_msg: str):
        """사용자용 안내 메시지와 원인 파악용 에러 코드를 분리하여 포맷팅하는 유틸리티"""
        if isinstance(e, requests.exceptions.Timeout):
            raise ConnectionError(f"{action_msg}\n(원인: 응답 시간 초과)")
        elif isinstance(e, requests.exceptions.ConnectionError):
            raise ConnectionError(f"{action_msg}\n(원인: 서버 연결 실패, 주소 상태 확인 필요)")
        elif isinstance(e, requests.exceptions.HTTPError):
            status = getattr(e.response, 'status_code', '알수없음')
            raise ConnectionError(f"{action_msg}\n(원인: 서버 응답 오류 HTTP {status})")
        else:
            raise ConnectionError(f"{action_msg}\n(원인: 알 수 없는 네트워크/파싱 오류)")

    def check_health(self) -> Dict[str, Any]:
        """서버 연결 상태 확인 (GET /health)"""
        url = f"{self.base_url}/health"
        try:
            response = requests.get(url, timeout=3)
            response.raise_for_status() 
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "서버 헬스체크 연결에 실패했습니다.")
            
    def start_session(self, source_type: str, source_name: str, frame_interval: int = 3) -> Dict[str, Any]:
        """분석 세션 생성 (POST /api/v1/sessions)"""
        url = f"{self.base_url}/api/v1/sessions"
        payload = {
            "source_type": source_type,
            "source_name": source_name,
            "frame_interval_sec": frame_interval,
            "requested_by": "desktop-client"
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "분석 세션 생성을 요청하지 못했습니다.")

    def get_results(self, limit: int = 50) -> list:
        """결과 목록 최신순 조회 (GET /api/v1/results)"""
        url = f"{self.base_url}/api/v1/results"
        try:
            response = requests.get(url, params={"limit": limit}, timeout=3)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "서버에서 결과 목록을 가져오지 못했습니다.")

    def get_result_detail(self, result_id: str) -> dict:
        """단건 결과 디테일 조회 (GET /api/v1/results/{id})"""
        url = f"{self.base_url}/api/v1/results/{result_id}"
        try:
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "해당 결과의 상세 데이터를 가져오지 못했습니다.")
