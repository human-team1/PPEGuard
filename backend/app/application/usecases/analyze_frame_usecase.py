import time
from typing import Dict, Any

from ..dtos import AnalyzeFrameCommand
from ..services.analyze_worker_service import AnalyzeWorker
from ...domain.entities.person import Person


class AnalyzeFrameUseCase:
    def __init__(
        self,
        analyze_worker: AnalyzeWorker,
        session_repo=None,
        ocr_service=None,
        ocr_engine=None,
        segment_result_service=None,
        realtime_event_service=None,
    ):
        self.analyze_worker = analyze_worker
        self.session_repo = session_repo
        self.ocr_service = ocr_service
        self.ocr_engine = ocr_engine
        self.segment_result_service = segment_result_service
        self.realtime_event_service = realtime_event_service
        self.webcam_state: Dict[str, Any] = {}

    def execute(self, command: AnalyzeFrameCommand) -> Dict[int, Person]:
        normalized_frame = self.analyze_worker.prepare_frame(command.image_base64)
        if normalized_frame is None:
            return {}

        print(
            f"[Webcam] frame received - session_id={command.session_id}",
            flush=True,
        )
        results = self.analyze_worker.run_inference(normalized_frame)

        for p_id, person in results.items():
            print(
                f"      - [WebcamFrameLog] Person {p_id}: "
                f"Helmet={person.helmet_confidence:.2f}, "
                f"Vest={person.vest_confidence:.2f}"
            )

        if command.session_id and self.segment_result_service and self.session_repo:
            self._handle_webcam_segment(command.session_id, normalized_frame, results)
        elif not command.session_id:
            print("[Webcam] frame skipped - session_id missing", flush=True)

        return results

    def finalize_session(self, session_id: str, reason: str = "finalize") -> None:
        if not self.session_repo or not self.segment_result_service:
            return

        session = self.session_repo.find_by_session_id(session_id)
        if session is None:
            return

        if self.realtime_event_service:
            self.realtime_event_service.emit_session_status(
                session_id=session_id,
                source_type="WEBCAM",
                status="stopping",
            )

        print(
            f"[Webcam] {reason} flush triggered - session_id={session_id}",
            flush=True,
        )
        self.segment_result_service.finalize_session(session, reason=reason)
        self.webcam_state.pop(session_id, None)

    def _handle_webcam_segment(
        self,
        session_id: str,
        frame,
        results: Dict[int, Person],
    ) -> None:
        now = time.time()
        state = self.webcam_state.setdefault(
            session_id,
            {
                "started_at": now,
                "frame_no": 0,
            },
        )
        state["frame_no"] += 1

        session = self.session_repo.find_by_session_id(session_id)
        if session is None:
            print(
                f"[Webcam] session lookup failed - session_id={session_id}",
                flush=True,
            )
            return

        elapsed_sec = now - state["started_at"]
        people = list(results.values())

        for person in people:
            person.latest_ocr_candidate = None
            person.latest_ocr_regex_matched = False
            person.latest_ocr_raw_text = None

            if self.ocr_service is None or self.ocr_engine is None:
                continue

            if self.ocr_service.should_run_ocr_for_person(person, elapsed_sec):
                ocr_data = self.ocr_engine.extract_worker_id(person.crop_image)
                person.last_ocr_at_sec = elapsed_sec
                self.ocr_service.apply_ocr_result_to_person(person, ocr_data)

        self.segment_result_service.ingest_frame(
            session=session,
            frame_no=state["frame_no"],
            frame_time_sec=elapsed_sec,
            frame=frame,
            people=people,
        )
        if self.realtime_event_service:
            detections = []
            for person in people:
                detections.append(
                    {
                        "track_id": person.id,
                        "employee_id": getattr(person, "employee_no", None),
                        "ocr_number": getattr(person, "employee_no", None),
                        "helmet_status": "WORN" if person.has_helmet else "NOT_WORN",
                        "vest_status": "WORN" if person.has_vest else "NOT_WORN",
                        "bbox": {
                            "x1": int(person.bbox[0]),
                            "y1": int(person.bbox[1]),
                            "x2": int(person.bbox[2]),
                            "y2": int(person.bbox[3]),
                        },
                    }
                )
            current_counts = {
                "detected_person_count": len(detections),
                "confirmed_ocr_person_count": sum(
                    1 for item in detections if item.get("ocr_number")
                ),
                "helmet_not_worn_count": sum(
                    1 for item in detections if item.get("helmet_status") != "WORN"
                ),
                "vest_not_worn_count": sum(
                    1 for item in detections if item.get("vest_status") != "WORN"
                ),
            }
            self.realtime_event_service.emit_progress(
                session_id=session_id,
                source_type="WEBCAM",
                current_time_sec=elapsed_sec,
                total_time_sec=0.0,
                processed_frames=state["frame_no"],
                current_counts=current_counts,
            )
            self.realtime_event_service.emit_frame_result(
                session_id=session_id,
                source_type="WEBCAM",
                frame=frame,
                detections=detections,
            )
        print(
            f"[Webcam] segment window updated - session_id={session_id}, "
            f"frame_no={state['frame_no']}, elapsed_sec={elapsed_sec:.2f}, "
            f"person_count={len(people)}",
            flush=True,
        )
