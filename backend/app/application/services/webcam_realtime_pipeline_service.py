import gc
import logging
import queue
import threading
import time
from collections import deque
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


class LatestFrameQueue:
    def __init__(self, maxsize: int):
        self.maxsize = max(int(maxsize or 1), 1)
        self._queue: queue.Queue = queue.Queue(maxsize=self.maxsize)

    def put_latest(self, item) -> bool:
        dropped = False
        while True:
            try:
                self._queue.put_nowait(item)
                return dropped
            except queue.Full:
                try:
                    dropped_item = self._queue.get_nowait()
                    self._cleanup_item(dropped_item)
                    self._queue.task_done()
                    dropped = True
                except queue.Empty:
                    return dropped

    def get(self, timeout: float | None = None):
        return self._queue.get(timeout=timeout)

    def task_done(self) -> None:
        self._queue.task_done()

    def qsize(self) -> int:
        return self._queue.qsize()

    def drain(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            self._cleanup_item(item)
            self._queue.task_done()

    def _cleanup_item(self, item) -> None:
        if item is None:
            return
        if hasattr(item, "image_base64"):
            item.image_base64 = ""
        if hasattr(item, "frame"):
            item.frame = None
        if hasattr(item, "people") and item.people is not None:
            item.people.clear()


class QueueWorkerPool:
    def __init__(self, name: str, worker_count: int, handler, queue_size: int):
        self.name = name
        self.worker_count = max(int(worker_count or 0), 1)
        self.handler = handler
        self.tasks: queue.Queue = queue.Queue(maxsize=max(int(queue_size or 0), self.worker_count, 1))
        self.threads: list[threading.Thread] = []

        for index in range(self.worker_count):
            thread = threading.Thread(
                target=self._run_worker,
                name=f"{self.name}-worker-{index + 1}",
                daemon=True,
            )
            thread.start()
            self.threads.append(thread)

    def submit(self, payload) -> Future:
        future: Future = Future()
        self.tasks.put((payload, future))
        return future

    def shutdown(self) -> None:
        for _ in self.threads:
            self.tasks.put(None)
        for thread in self.threads:
            thread.join()
        self._drain_tasks()

    def _run_worker(self) -> None:
        while True:
            item = self.tasks.get()
            if item is None:
                self.tasks.task_done()
                break

            payload, future = item
            try:
                result = self.handler(payload)
            except Exception as exc:
                future.set_exception(exc)
            else:
                future.set_result(result)
            finally:
                self.tasks.task_done()

    def _drain_tasks(self) -> None:
        while True:
            try:
                item = self.tasks.get_nowait()
            except queue.Empty:
                break
            self.tasks.task_done()
            if item is None:
                continue
            payload, _future = item
            if hasattr(payload, "frame"):
                payload.frame = None


@dataclass
class RawWebcamFrame:
    frame_no: int
    received_at: float
    image_base64: str


@dataclass
class YoloTask:
    frame_no: int
    frame_time_sec: float
    received_at: float
    frame: Any


@dataclass
class YoloResult:
    frame_no: int
    frame_time_sec: float
    received_at: float
    frame: Any
    people: list


@dataclass
class TrackState:
    track_id: int
    first_seen_at: float
    last_seen_at: float
    last_bbox: list[int]
    employee_no: str | None = None
    ocr_confirmed: bool = False
    last_ocr_at_sec: float | None = None
    ocr_attempt_count: int = 0
    ocr_candidates: deque = field(default_factory=deque)
    ppe_observations: deque = field(default_factory=deque)
    last_snapshot: dict = field(default_factory=dict)
    confirmation_event_sent: bool = False
    ocr_limit_logged: bool = False


class WebcamRealtimePipelineService:
    def __init__(
        self,
        session,
        analyze_worker,
        ocr_engine,
        ocr_service,
        segment_result_service,
        realtime_event_service,
        capture_fps: float,
        analysis_fps: float,
        frame_queue_size: int,
        event_queue_size: int,
        result_window_seconds: float,
        result_ttl_seconds: float,
        track_expiry_seconds: float,
        max_track_ocr_count: int,
        yolo_worker_count: int,
        ocr_worker_count: int,
        yolo_queue_size: int,
        ocr_queue_size: int,
    ):
        self.session = session
        self.analyze_worker = analyze_worker
        self.ocr_engine = ocr_engine
        self.ocr_service = ocr_service
        self.segment_result_service = segment_result_service
        self.realtime_event_service = realtime_event_service
        self.capture_fps = max(float(capture_fps or 0.0), 0.1)
        self.analysis_fps = max(float(analysis_fps or 0.0), 0.1)
        self.result_window_seconds = max(float(result_window_seconds or 0.0), 1.0)
        self.result_ttl_seconds = max(float(result_ttl_seconds or 0.0), self.result_window_seconds)
        self.track_expiry_seconds = max(float(track_expiry_seconds or 0.0), 1.0)
        self.max_track_ocr_count = max(int(max_track_ocr_count or 0), 1)
        self.frame_queue = LatestFrameQueue(frame_queue_size)
        self.yolo_result_queue = LatestFrameQueue(frame_queue_size)
        self.event_queue = LatestFrameQueue(event_queue_size)
        self.stop_event = threading.Event()
        self.started_at = time.time()
        self.received_frame_count = 0
        self.processed_frame_count = 0
        self.last_capture_accept_at = 0.0
        self.last_analysis_at = 0.0
        self.last_summary_emit_at = 0.0
        self.last_preview_emit_at = 0.0
        self.dropped_frame_count = 0
        self.total_ocr_requests = 0
        self.total_ocr_time_sec = 0.0
        self.last_drop_warning_at = 0.0
        self.tracks: dict[int, TrackState] = {}
        self.state_lock = threading.Lock()
        self.yolo_pool = QueueWorkerPool(
            name=f"webcam-yolo-{session.session_id[:8]}",
            worker_count=yolo_worker_count,
            handler=self._run_yolo_inference,
            queue_size=yolo_queue_size,
        )
        self.ocr_pool = QueueWorkerPool(
            name=f"webcam-ocr-{session.session_id[:8]}",
            worker_count=ocr_worker_count,
            handler=self._run_ocr_inference,
            queue_size=ocr_queue_size,
        )
        self.processor_thread = threading.Thread(
            target=self._run_processor_loop,
            name=f"webcam-processor-{session.session_id[:8]}",
            daemon=True,
        )
        self.aggregator_thread = threading.Thread(
            target=self._run_aggregator_loop,
            name=f"webcam-aggregator-{session.session_id[:8]}",
            daemon=True,
        )
        self.event_thread = threading.Thread(
            target=self._run_event_loop,
            name=f"webcam-events-{session.session_id[:8]}",
            daemon=True,
        )

    def start(self) -> None:
        logger.info(
            "[AnalysisSession] started session_id=%s source=webcam capture_fps=%s analysis_fps=%s frame_queue=%s event_queue=%s track_expiry=%s max_track_ocr=%s",
            self.session.session_id,
            self.capture_fps,
            self.analysis_fps,
            self.frame_queue.maxsize,
            self.event_queue.maxsize,
            self.track_expiry_seconds,
            self.max_track_ocr_count,
        )
        self.processor_thread.start()
        self.aggregator_thread.start()
        self.event_thread.start()

    def submit_frame(self, image_base64: str) -> None:
        if not image_base64:
            return

        now = time.time()
        capture_stride = 1.0 / self.capture_fps
        if (now - self.last_capture_accept_at) < capture_stride:
            return

        self.last_capture_accept_at = now
        self.received_frame_count += 1
        dropped = self.frame_queue.put_latest(
            RawWebcamFrame(
                frame_no=self.received_frame_count,
                received_at=now,
                image_base64=image_base64,
            )
        )
        if dropped:
            self.dropped_frame_count += 1
            if (now - self.last_drop_warning_at) >= 5.0:
                self.last_drop_warning_at = now
                logger.warning(
                    "[Queue] frame dropped session_id=%s dropped_total=%s queue_size=%s",
                    self.session.session_id,
                    self.dropped_frame_count,
                    self.frame_queue.maxsize,
                )

    def stop(self, reason: str = "finalize") -> None:
        if self.stop_event.is_set():
            return

        logger.info(
            "[AnalysisSession] stopping session_id=%s reason=%s",
            self.session.session_id,
            reason,
        )
        self.stop_event.set()
        self.frame_queue.put_latest(None)
        self.yolo_result_queue.put_latest(None)
        self.event_queue.put_latest(None)

        for thread in (self.processor_thread, self.aggregator_thread, self.event_thread):
            if thread.is_alive():
                thread.join()

        self.yolo_pool.shutdown()
        self.ocr_pool.shutdown()
        self.frame_queue.drain()
        self.yolo_result_queue.drain()
        self.event_queue.drain()
        for track_state in self.tracks.values():
            self._cleanup_track_state(track_state)
        self.tracks.clear()
        elapsed_sec = time.time() - self.started_at
        self._release_runtime_memory()
        logger.info(
            "[AnalysisSession] stopped session_id=%s processed_frames=%s dropped_frames=%s ocr_requests=%s avg_ocr_ms=%.1f elapsed_sec=%.2f",
            self.session.session_id,
            self.processed_frame_count,
            self.dropped_frame_count,
            self.total_ocr_requests,
            (self.total_ocr_time_sec / self.total_ocr_requests * 1000.0) if self.total_ocr_requests else 0.0,
            elapsed_sec,
        )

    def _run_processor_loop(self) -> None:
        analysis_stride = 1.0 / self.analysis_fps

        while not self.stop_event.is_set():
            try:
                raw_frame = self.frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if raw_frame is None:
                self.frame_queue.task_done()
                break

            try:
                if (raw_frame.received_at - self.last_analysis_at) < analysis_stride:
                    raw_frame.image_base64 = ""
                    continue

                frame = self.analyze_worker.prepare_frame(raw_frame.image_base64)
                raw_frame.image_base64 = ""
                if frame is None:
                    continue

                self.last_analysis_at = raw_frame.received_at
                frame_time_sec = max(raw_frame.received_at - self.started_at, 0.0)
                task = YoloTask(
                    frame_no=raw_frame.frame_no,
                    frame_time_sec=frame_time_sec,
                    received_at=raw_frame.received_at,
                    frame=frame,
                )
                future = self.yolo_pool.submit(task)
                future.add_done_callback(
                    lambda completed_future, original_task=task: self._handle_yolo_completed(
                        completed_future,
                        original_task,
                    )
                )
            finally:
                self.frame_queue.task_done()

    def _handle_yolo_completed(self, future: Future, task: YoloTask) -> None:
        if self.stop_event.is_set():
            task.frame = None
            return

        try:
            people = future.result()
        except Exception as exc:
            self.event_queue.put_latest(
                ("error", {"message": f"웹캠 YOLO 처리 오류: {exc}"})
            )
            task.frame = None
            return

        self.yolo_result_queue.put_latest(
            YoloResult(
                frame_no=task.frame_no,
                frame_time_sec=task.frame_time_sec,
                received_at=task.received_at,
                frame=task.frame,
                people=people,
            )
        )
        task.frame = None

    def _run_aggregator_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                result = self.yolo_result_queue.get(timeout=0.5)
            except queue.Empty:
                self._cleanup_expired_tracks(time.time() - self.started_at)
                continue

            if result is None:
                self.yolo_result_queue.task_done()
                break

            try:
                self._process_yolo_result(result)
            finally:
                self.yolo_result_queue.task_done()

    def _process_yolo_result(self, result: YoloResult) -> None:
        current_time_sec = result.frame_time_sec
        preview_detections = []
        confirm_events = []

        for person in result.people:
            person.latest_ocr_candidate = None
            person.latest_ocr_regex_matched = False
            person.latest_ocr_raw_text = None

            track_state = self._get_or_create_track_state(person, current_time_sec)
            self._apply_track_snapshot(track_state, person, current_time_sec)

            if self._should_run_ocr(track_state, person, current_time_sec):
                track_state.last_ocr_at_sec = current_time_sec
                track_state.ocr_attempt_count += 1
                crop_image = person.crop_image
                ocr_data = self._wait_ocr_result(crop_image)
                self.ocr_service.apply_ocr_result_to_person(person, ocr_data)
                self._apply_ocr_to_track(track_state, person, current_time_sec)
                confirm_event = self._build_track_confirmed_event(track_state, person, current_time_sec)
                if confirm_event is not None:
                    confirm_events.append(confirm_event)

            preview_detections.append(self._build_preview_detection(person, track_state))
            self._build_track_summary(track_state, person)

        self.processed_frame_count += 1
        self.segment_result_service.ingest_frame(
            session=self.session,
            frame_no=result.frame_no,
            frame_time_sec=current_time_sec,
            frame=result.frame,
            people=result.people,
        )

        self._cleanup_expired_tracks(current_time_sec)
        summary_tracks = self._collect_active_track_summaries()
        self._enqueue_realtime_events(
            current_time_sec=current_time_sec,
            frame=result.frame,
            preview_detections=preview_detections,
            summary_tracks=summary_tracks,
            confirm_events=confirm_events,
        )

        for person in result.people:
            person.crop_image = None
        result.people.clear()
        result.frame = None
        preview_detections.clear()
        summary_tracks.clear()
        confirm_events.clear()

    def _enqueue_realtime_events(
        self,
        current_time_sec: float,
        frame,
        preview_detections: list[dict],
        summary_tracks: list[dict],
        confirm_events: list[dict],
    ) -> None:
        current_counts = {
            "detected_person_count": len(summary_tracks),
            "confirmed_ocr_person_count": sum(
                1 for item in summary_tracks if item.get("employee_id")
            ),
            "helmet_not_worn_count": sum(
                1 for item in summary_tracks if item.get("helmet_status") == "NOT_WORN"
            ),
            "vest_not_worn_count": sum(
                1 for item in summary_tracks if item.get("vest_status") == "NOT_WORN"
            ),
            "active_track_count": len(summary_tracks),
            "frame_queue_depth": self.frame_queue.qsize(),
        }

        now = time.time()
        if (now - self.last_summary_emit_at) >= self.realtime_event_service.min_emit_interval_sec:
            self.last_summary_emit_at = now
            self.event_queue.put_latest(
                (
                    "progress",
                    {
                        "session_id": self.session.session_id,
                        "source_type": "WEBCAM",
                        "current_time_sec": current_time_sec,
                        "total_time_sec": 0.0,
                        "processed_frames": self.processed_frame_count,
                        "current_counts": current_counts,
                        "track_summaries": summary_tracks,
                    },
                )
            )

        if (now - self.last_preview_emit_at) >= self.realtime_event_service.min_emit_interval_sec:
            self.last_preview_emit_at = now
            self.event_queue.put_latest(
                (
                    "frame_result",
                    {
                        "session_id": self.session.session_id,
                        "source_type": "WEBCAM",
                        "frame": frame,
                        "detections": preview_detections,
                    },
                )
            )

        for confirm_event in confirm_events:
            self.event_queue.put_latest(("track_confirmed", confirm_event))

    def _run_event_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                event = self.event_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if event is None:
                self.event_queue.task_done()
                break

            try:
                event_name, payload = event
                if event_name == "progress":
                    self.realtime_event_service.emit_progress(**payload)
                elif event_name == "frame_result":
                    self.realtime_event_service.emit_frame_result(**payload)
                elif event_name == "track_confirmed":
                    self.realtime_event_service.emit_webcam_track_confirmed(**payload)
                elif event_name == "error":
                    self.realtime_event_service.emit_error(payload.get("message", "웹캠 처리 오류"))
            finally:
                if isinstance(payload, dict):
                    payload.clear()
                self.event_queue.task_done()

    def _run_yolo_inference(self, task: YoloTask) -> list:
        results = self.analyze_worker.run_inference(task.frame)
        return list(results.values())

    def _run_ocr_inference(self, crop_image):
        if crop_image is None or getattr(crop_image, "size", 0) == 0:
            return None
        return self.ocr_engine.extract_worker_id(crop_image)

    def _wait_ocr_result(self, crop_image):
        future = self.ocr_pool.submit(crop_image)
        started_at = time.perf_counter()
        result = future.result()
        self.total_ocr_requests += 1
        self.total_ocr_time_sec += time.perf_counter() - started_at
        return result

    def _get_or_create_track_state(self, person, current_time_sec: float) -> TrackState:
        with self.state_lock:
            state = self.tracks.get(person.id)
            if state is None:
                state = TrackState(
                    track_id=person.id,
                    first_seen_at=current_time_sec,
                    last_seen_at=current_time_sec,
                    last_bbox=list(person.bbox),
                )
                self.tracks[person.id] = state
            return state

    def _apply_track_snapshot(self, track_state: TrackState, person, current_time_sec: float) -> None:
        track_state.last_seen_at = current_time_sec
        track_state.last_bbox = list(person.bbox)
        track_state.ppe_observations.append(
            {
                "time_sec": current_time_sec,
                "has_helmet": bool(person.has_helmet),
                "has_vest": bool(person.has_vest),
            }
        )
        self._prune_track_state(track_state, current_time_sec)

        if track_state.ocr_confirmed:
            person.employee_no = track_state.employee_no
            person.ocr_confirmed = True

    def _apply_ocr_to_track(self, track_state: TrackState, person, current_time_sec: float) -> None:
        candidate = getattr(person, "latest_ocr_candidate", None)
        if candidate and getattr(person, "latest_ocr_regex_matched", False):
            track_state.ocr_candidates.append(
                {
                    "time_sec": current_time_sec,
                    "candidate": candidate,
                }
            )

        self._prune_track_state(track_state, current_time_sec)

        candidate_counts: dict[str, int] = {}
        for item in track_state.ocr_candidates:
            candidate_counts[item["candidate"]] = candidate_counts.get(item["candidate"], 0) + 1

        confirmed_candidate = None
        for candidate_value, count in candidate_counts.items():
            if count >= self.ocr_service.employee_number_min_confirm_count:
                confirmed_candidate = candidate_value
                break

        if confirmed_candidate:
            track_state.employee_no = confirmed_candidate
            track_state.ocr_confirmed = True
            person.employee_no = confirmed_candidate
            person.ocr_confirmed = True
            logger.info(
                "[OCR] confirmed track_id=%s employee_no=%s session_id=%s",
                track_state.track_id,
                confirmed_candidate,
                self.session.session_id,
            )

    def _build_track_confirmed_event(
        self,
        track_state: TrackState,
        person,
        current_time_sec: float,
    ) -> dict | None:
        if not track_state.ocr_confirmed or not track_state.employee_no:
            return None
        if track_state.confirmation_event_sent:
            return None

        track_state.confirmation_event_sent = True
        return {
            "session_id": self.session.session_id,
            "source_type": "WEBCAM",
            "track_id": track_state.track_id,
            "employee_id": track_state.employee_no,
            "confirmed_at_sec": current_time_sec,
            "bbox": {
                "x1": int(person.bbox[0]),
                "y1": int(person.bbox[1]),
                "x2": int(person.bbox[2]),
                "y2": int(person.bbox[3]),
            },
        }

    def _should_run_ocr(self, track_state: TrackState, person, current_time_sec: float) -> bool:
        if track_state.ocr_confirmed or track_state.employee_no:
            return False
        if track_state.ocr_attempt_count >= self.max_track_ocr_count:
            if not track_state.ocr_limit_logged:
                track_state.ocr_limit_logged = True
                logger.warning(
                    "[OCR] max retries reached session_id=%s track_id=%s attempts=%s",
                    self.session.session_id,
                    track_state.track_id,
                    track_state.ocr_attempt_count,
                )
            return False
        if person.crop_image is None or getattr(person.crop_image, "size", 0) == 0:
            return False
        if not self.ocr_service.should_run_ocr_for_person(person, current_time_sec):
            return False
        return bool(getattr(person, "has_vest", False) or person.get_bbox_area() >= 4000)

    def _build_preview_detection(self, person, track_state: TrackState) -> dict:
        return {
            "track_id": person.id,
            "employee_id": track_state.employee_no,
            "ocr_number": track_state.employee_no,
            "ocr_confirmed": track_state.ocr_confirmed,
            "helmet_status": "WORN" if person.has_helmet else "NOT_WORN",
            "vest_status": "WORN" if person.has_vest else "NOT_WORN",
            "bbox": {
                "x1": int(person.bbox[0]),
                "y1": int(person.bbox[1]),
                "x2": int(person.bbox[2]),
                "y2": int(person.bbox[3]),
            },
        }

    def _build_track_summary(self, track_state: TrackState, person) -> dict:
        track_state.last_snapshot = {
            "track_id": track_state.track_id,
            "employee_id": track_state.employee_no,
            "ocr_confirmed": track_state.ocr_confirmed,
            "helmet_status": self._resolve_window_status(track_state, "has_helmet"),
            "vest_status": self._resolve_window_status(track_state, "has_vest"),
            "last_seen_at_sec": track_state.last_seen_at,
            "ocr_attempt_count": track_state.ocr_attempt_count,
            "bbox": {
                "x1": int(person.bbox[0]),
                "y1": int(person.bbox[1]),
                "x2": int(person.bbox[2]),
                "y2": int(person.bbox[3]),
            },
        }
        return dict(track_state.last_snapshot)

    def _resolve_window_status(self, track_state: TrackState, field_name: str) -> str:
        observations = list(track_state.ppe_observations)
        if not observations:
            return "UNKNOWN"

        true_count = sum(1 for item in observations if item.get(field_name))
        if (true_count / len(observations)) >= 0.5:
            return "WORN"
        return "NOT_WORN"

    def _collect_active_track_summaries(self) -> list[dict]:
        return sorted(
            [dict(track_state.last_snapshot) for track_state in self.tracks.values() if track_state.last_snapshot],
            key=lambda item: int(item.get("track_id", 0)),
        )

    def _prune_track_state(self, track_state: TrackState, current_time_sec: float) -> None:
        min_time_sec = current_time_sec - self.result_ttl_seconds
        while track_state.ocr_candidates and track_state.ocr_candidates[0]["time_sec"] < min_time_sec:
            track_state.ocr_candidates.popleft()
        while track_state.ppe_observations and track_state.ppe_observations[0]["time_sec"] < min_time_sec:
            track_state.ppe_observations.popleft()

    def _cleanup_expired_tracks(self, current_time_sec: float) -> None:
        expired_track_ids = []
        with self.state_lock:
            for track_id, track_state in self.tracks.items():
                self._prune_track_state(track_state, current_time_sec)
                if (current_time_sec - track_state.last_seen_at) > self.track_expiry_seconds:
                    expired_track_ids.append(track_id)

            for track_id in expired_track_ids:
                expired_state = self.tracks.pop(track_id, None)
                if expired_state is not None:
                    logger.warning(
                        "[Track] expired session_id=%s track_id=%s idle_sec=%.2f",
                        self.session.session_id,
                        track_id,
                        current_time_sec - expired_state.last_seen_at,
                    )
                    self._cleanup_track_state(expired_state)

    def _cleanup_track_state(self, track_state: TrackState) -> None:
        track_state.ocr_candidates.clear()
        track_state.ppe_observations.clear()
        track_state.last_snapshot.clear()
        track_state.last_bbox.clear()

    def _release_runtime_memory(self) -> None:
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


class WebcamPipelineManager:
    def __init__(
        self,
        analyze_worker_factory,
        ocr_engine,
        ocr_service,
        session_repo,
        segment_result_service,
        realtime_event_service,
        capture_fps: float,
        analysis_fps: float,
        frame_queue_size: int,
        event_queue_size: int,
        result_window_seconds: float,
        result_ttl_seconds: float,
        track_expiry_seconds: float,
        max_track_ocr_count: int,
        yolo_worker_count: int,
        ocr_worker_count: int,
        yolo_queue_size: int,
        ocr_queue_size: int,
    ):
        self.analyze_worker_factory = analyze_worker_factory
        self.ocr_engine = ocr_engine
        self.ocr_service = ocr_service
        self.session_repo = session_repo
        self.segment_result_service = segment_result_service
        self.realtime_event_service = realtime_event_service
        self.capture_fps = capture_fps
        self.analysis_fps = analysis_fps
        self.frame_queue_size = frame_queue_size
        self.event_queue_size = event_queue_size
        self.result_window_seconds = result_window_seconds
        self.result_ttl_seconds = result_ttl_seconds
        self.track_expiry_seconds = track_expiry_seconds
        self.max_track_ocr_count = max_track_ocr_count
        self.yolo_worker_count = yolo_worker_count
        self.ocr_worker_count = ocr_worker_count
        self.yolo_queue_size = yolo_queue_size
        self.ocr_queue_size = ocr_queue_size
        self.pipelines: dict[str, WebcamRealtimePipelineService] = {}
        self.lock = threading.Lock()

    def submit_frame(self, session_id: str, image_base64: str) -> None:
        if not session_id or not image_base64:
            return

        pipeline = self._get_or_create_pipeline(session_id)
        pipeline.submit_frame(image_base64)

    def finalize_session(self, session_id: str, reason: str = "finalize") -> None:
        with self.lock:
            pipeline = self.pipelines.pop(session_id, None)

        if pipeline is None:
            return

        pipeline.stop(reason=reason)
        session = self.session_repo.find_by_session_id(session_id)
        if session is not None:
            self.segment_result_service.finalize_session(session, reason=reason)

    def _get_or_create_pipeline(self, session_id: str) -> WebcamRealtimePipelineService:
        with self.lock:
            pipeline = self.pipelines.get(session_id)
            if pipeline is not None:
                return pipeline

            session = self.session_repo.find_by_session_id(session_id)
            if session is None:
                raise ValueError(f"웹캠 세션을 찾을 수 없습니다: {session_id}")

            pipeline = WebcamRealtimePipelineService(
                session=session,
                analyze_worker=self.analyze_worker_factory(),
                ocr_engine=self.ocr_engine,
                ocr_service=self.ocr_service,
                segment_result_service=self.segment_result_service,
                realtime_event_service=self.realtime_event_service,
                capture_fps=self.capture_fps,
                analysis_fps=self.analysis_fps,
                frame_queue_size=self.frame_queue_size,
                event_queue_size=self.event_queue_size,
                result_window_seconds=self.result_window_seconds,
                result_ttl_seconds=self.result_ttl_seconds,
                track_expiry_seconds=self.track_expiry_seconds,
                max_track_ocr_count=self.max_track_ocr_count,
                yolo_worker_count=self.yolo_worker_count,
                ocr_worker_count=self.ocr_worker_count,
                yolo_queue_size=self.yolo_queue_size,
                ocr_queue_size=self.ocr_queue_size,
            )
            pipeline.start()
            self.pipelines[session_id] = pipeline
            return pipeline
