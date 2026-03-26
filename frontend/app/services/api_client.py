import json
import os
from typing import Any, Dict

import requests


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def update_base_url(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _handle_request_error(self, e: Exception, action_msg: str):
        if isinstance(e, requests.exceptions.Timeout):
            raise ConnectionError(f"{action_msg}\n(원인: 응답 시간 초과)")
        if isinstance(e, requests.exceptions.ConnectionError):
            raise ConnectionError(f"{action_msg}\n(원인: 서버 연결 실패)")
        if isinstance(e, requests.exceptions.HTTPError):
            status = getattr(e.response, "status_code", "알수없음")
            details = ""
            try:
                resp_json = e.response.json()
                if "details" in resp_json:
                    details = f"\n상세: {resp_json['details']}"
            except Exception:
                pass
            raise ConnectionError(f"{action_msg}\n(HTTP {status}){details}")
        raise ConnectionError(f"{action_msg}\n(원인: 알 수 없는 오류)")

    def check_health(self) -> Dict[str, Any]:
        url = f"{self.base_url}/health"
        try:
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "서버 상태 확인에 실패했습니다.")

    def start_session(
        self,
        source_type: str,
        source_name: str,
        frame_interval: int = 3,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/sessions"
        payload = {
            "source_type": source_type,
            "source_name": source_name,
            "frame_interval_sec": frame_interval,
            "requested_by": "desktop-client",
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "분석 세션 생성 요청에 실패했습니다.")

    def stop_session(self, session_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/sessions/{session_id}/stop"
        try:
            response = requests.post(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "분석 종료 요청에 실패했습니다.")

    def stop_video_analysis(self, session_id: str | None = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/video/stop"
        try:
            payload = {"session_id": session_id} if session_id else {}
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "동영상 분석 중단 요청에 실패했습니다.")

    def upload_video(
        self,
        video_path: str,
        video_started_at: str = None,
        inspection_item_keys: list[str] | None = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/video"
        if not os.path.exists(video_path):
            raise ConnectionError("선택한 동영상 파일을 찾을 수 없습니다.")

        try:
            with open(video_path, "rb") as video_file:
                files = {
                    "file": (os.path.basename(video_path), video_file, "video/mp4")
                }
                data = {}
                if video_started_at:
                    data["video_started_at"] = video_started_at
                if inspection_item_keys is not None:
                    data["inspection_item_keys"] = json.dumps(inspection_item_keys)

                response = requests.post(url, files=files, data=data, timeout=300)
                response.raise_for_status()
                return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "동영상 업로드 요청에 실패했습니다.")

    def get_results(self, limit: int = 50) -> list:
        url = f"{self.base_url}/api/v1/results"
        try:
            response = requests.get(url, params={"limit": limit}, timeout=3)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "결과 목록을 불러오지 못했습니다.")

    def get_result_detail(self, result_id: str) -> dict:
        url = f"{self.base_url}/api/v1/results/{result_id}"
        try:
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "결과 상세를 불러오지 못했습니다.")

    def get_session_results(self, session_id: str) -> list:
        url = f"{self.base_url}/api/v1/sessions/{session_id}/results"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "세션 결과 목록을 불러오지 못했습니다.")

    def get_session_segments(self, session_id: str, timeout_sec: int = 5) -> dict:
        url = f"{self.base_url}/api/v1/sessions/{session_id}/segments"
        try:
            response = requests.get(url, timeout=timeout_sec)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "세션 세그먼트 결과를 불러오지 못했습니다.")

    def get_session_tracks(self, session_id: str, timeout_sec: int = 5) -> dict:
        url = f"{self.base_url}/api/v1/sessions/{session_id}/tracks"
        try:
            response = requests.get(url, timeout=timeout_sec)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "?몄뀡 異붿쟻 寃곌낵瑜?遺덈윭?ㅼ? 紐삵뻽?듬땲??")

    def get_session_track_detail(self, session_id: str, track_id: int, timeout_sec: int = 5) -> dict:
        url = f"{self.base_url}/api/v1/sessions/{session_id}/tracks/{track_id}"
        try:
            response = requests.get(url, timeout=timeout_sec)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "?붿쟻 寃곌낵 ?곸꽭瑜?遺덈윭?ㅼ? 紐삵뻽?듬땲??")

    def get_sessions(self, limit: int = 20) -> dict:
        url = f"{self.base_url}/api/v1/sessions"
        try:
            response = requests.get(url, params={"limit": limit}, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "세션 목록을 불러오지 못했습니다.")
