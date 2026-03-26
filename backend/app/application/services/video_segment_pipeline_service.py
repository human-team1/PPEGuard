import gc
import logging
import math
import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass, field

import cv2

from config.settings import Config
from app.application.services.best_frame_selector import BestFrameSelector
from app.application.services.segment_aggregation_service import SegmentAggregationService


logger = logging.getLogger(__name__)


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
            if hasattr(payload, "clear"):
                try:
                    payload.clear()
                except Exception:
                    pass


@dataclass
class VideoSegmentTask:
    segment_index: int
    segment_start_sec: float
    segment_end_sec: float
    start_frame_index: int
    end_frame_index: int


@dataclass
class VideoSegmentResult:
    segment_index: int
    segment_start_sec: float
    segment_end_sec: float
    processed_frames: int
    people_results: list[dict]
    representative_frame_path: str | None
    representative_frame_info: dict | None
    current_counts: dict


@dataclass
class SegmentPersonState:
    track_id: int
    bbox: list[int]
    last_seen_frame_no: int
    employee_no: str | None = None
    ocr_confirmed: bool = False
    last_ocr_at_sec: float | None = None
    ocr_candidate_counts: dict[str, int] = field(default_factory=dict)
    ocr_attempt_count: int = 0
    last_regex_matched: bool = False
    current_violation_flags: dict[str, bool] = field(default_factory=dict)
    has_selected_item_violation: bool = False


class VideoSegmentPipelineService:
    def __init__(
        self,
        analyze_worker,
        ocr_engine,
        ocr_service,
        file_service,
        persistence_service,
        realtime_event_service,
        segment_window_service,
        analysis_fps: float,
        max_concurrent_segments: int,
        yolo_worker_count: int,
        ocr_worker_count: int,
        max_track_ocr_count: int,
    ):
        self.analyze_worker = analyze_worker
        self.ocr_engine = ocr_engine
        self.ocr_service = ocr_service
        self.file_service = file_service
        self.persistence_service = persistence_service
        self.realtime_event_service = realtime_event_service
        self.segment_window_service = segment_window_service
        self.analysis_fps = 1.0
        self.max_concurrent_segments = max(int(max_concurrent_segments or 0), 1)
        self.max_track_ocr_count = max(int(max_track_ocr_count or 0), 1)
        self.yolo_pool = QueueWorkerPool(
            name="yolo",
            worker_count=yolo_worker_count,
            handler=self._run_yolo_prediction,
            queue_size=Config.YOLO_QUEUE_SIZE,
        )
        self.ocr_pool = QueueWorkerPool(
            name="ocr",
            worker_count=ocr_worker_count,
            handler=self._run_ocr_prediction,
            queue_size=Config.OCR_QUEUE_SIZE,
        )
        queue_size = max(Config.VIDEO_PIPELINE_QUEUE_SIZE, self.max_concurrent_segments)
        self.segment_tasks: queue.Queue = queue.Queue(maxsize=queue_size)
        self.segment_results: queue.Queue = queue.Queue(maxsize=queue_size)
        self.stop_event = threading.Event()

    def close(self) -> None:
        logger.info("[VideoPipeline] cleanup started")
        self.yolo_pool.shutdown()
        self.ocr_pool.shutdown()
        self._drain_queue(self.segment_tasks)
        self._drain_queue(self.segment_results)
        self._release_runtime_memory()
        logger.info("[VideoPipeline] cleanup completed")

    def process_video(
        self,
        session,
        video_path: str,
        fps: float,
        total_frames: int,
        total_time_sec: float,
        source_type: str,
        inspection_item_keys: list[str] | None = None,
        stop_signal = None,
    ) -> int | None:
        tasks = self._build_segment_tasks(total_frames=total_frames, total_time_sec=total_time_sec, fps=fps)
        if not tasks:
            return 0

        logger.info(
            "[VideoPipeline] started session_id=%s segments=%s analysis_fps=%s max_segments=%s",
            session.session_id,
            len(tasks),
            self.analysis_fps,
            self.max_concurrent_segments,
        )

        workers = []
        for index in range(self.max_concurrent_segments):
            worker = threading.Thread(
                target=self._run_segment_worker,
                kwargs={
                    "session_id": session.session_id,
                    "video_path": video_path,
                    "fps": fps,
                    "inspection_item_keys": inspection_item_keys,
                },
                name=f"segment-worker-{index + 1}",
                daemon=True,
            )
            worker.start()
            workers.append(worker)

        for task in tasks:
            self.segment_tasks.put(task)
        for _ in workers:
            self.segment_tasks.put(None)

        processed_frames = 0
        completed_segments = 0
        next_segment_index = 0
        pending_results: dict[int, VideoSegmentResult] = {}

        try:
            while completed_segments < len(tasks):
                # (추가) 목적/이유: 외부의 중단 시그널(예: UI '분석 중지' 클릭)을 
                # 감지하여 워커들에게 종료를 지시하고 루프를 빠져나옴.
                if stop_signal and stop_signal():
                    logger.info("[VideoPipeline] Stop signal received for session=%s", session.session_id)
                    self.stop_event.set()
                    return None

                try:
                    result = self.segment_results.get(timeout=1.0)
                except queue.Empty:
                    continue

                if isinstance(result, Exception):
                    self.stop_event.set()
                    raise result

                pending_results[result.segment_index] = result
                while next_segment_index in pending_results:
                    ordered_result = pending_results.pop(next_segment_index)
                    self.persistence_service.save_segment(
                        session=session,
                        segment_index=ordered_result.segment_index,
                        segment_start_sec=ordered_result.segment_start_sec,
                        segment_end_sec=ordered_result.segment_end_sec,
                        representative_frame_path=ordered_result.representative_frame_path,
                        representative_frame_info=ordered_result.representative_frame_info,
                        people_results=ordered_result.people_results,
                    )
                    processed_frames += ordered_result.processed_frames
                    completed_segments += 1
                    next_segment_index += 1

                    # (복구) 프론트엔드 진행률 게이지 업데이트
                    self.realtime_event_service.emit_progress(
                        session_id=session.session_id,
                        source_type=source_type,
                        current_time_sec=ordered_result.segment_end_sec,
                        total_time_sec=total_time_sec,
                        processed_frames=processed_frames,
                        current_counts=ordered_result.current_counts,
                    )

                    ordered_result.people_results.clear()

                    if ordered_result.representative_frame_info is not None:
                        ordered_result.representative_frame_info.clear()
                    ordered_result.current_counts.clear()
        finally:
            self.stop_event.set()
            for worker in workers:
                worker.join()
            pending_results.clear()

        return processed_frames

    def _run_segment_worker(
        self,
        session_id: str,
        video_path: str,
        fps: float,
        inspection_item_keys: list[str] | None,
    ) -> None:
        while not self.stop_event.is_set():
            task = self.segment_tasks.get()
            if task is None:
                self.segment_tasks.task_done()
                break

            try:
                result = self._process_segment(
                    session_id=session_id,
                    video_path=video_path,
                    fps=fps,
                    task=task,
                    inspection_item_keys=inspection_item_keys,
                )
                self.segment_results.put(result)
            except Exception as exc:
                logger.exception(
                    "[Segment] processing failed session_id=%s segment_index=%s",
                    session_id,
                    getattr(task, "segment_index", None),
                )
                self.segment_results.put(exc)
            finally:
                self.segment_tasks.task_done()

    def _process_segment(
        self,
        session_id: str,
        video_path: str,
        fps: float,
        task: VideoSegmentTask,
        inspection_item_keys: list[str] | None,
    ) -> VideoSegmentResult:
        segment_started_at = time.perf_counter()
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("업로드한 영상 파일을 열 수 없습니다.")

        aggregation = SegmentAggregationService(
            best_frame_selector=BestFrameSelector(),
            file_service=self.file_service,
            active_inspection_items=self.ocr_service.normalize_inspection_item_keys(
                inspection_item_keys
            ),
        )

        sample_step = max(int(round(fps / self.analysis_fps)), 1)
        person_states: dict[int, SegmentPersonState] = {}
        processed_frames = 0
        ocr_request_count = 0
        violating_candidate_count = 0

        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, task.start_frame_index)
            frame_index = task.start_frame_index

            while frame_index < task.end_frame_index and not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    break

                if (frame_index - task.start_frame_index) % sample_step != 0:
                    frame_index += 1
                    continue

                frame_no = frame_index + 1
                frame_time_sec = frame_no / fps if fps > 0 else 0.0
                detected_people = self.yolo_pool.submit(frame).result()
                people = self._sync_tracked_people(
                    detected_people=detected_people,
                    person_states=person_states,
                    frame_no=frame_no,
                )

                ocr_jobs = []
                for person in people:
                    violation_flags = self.ocr_service.get_selected_item_violation_flags(
                        person,
                        inspection_item_keys,
                    )
                    has_selected_item_violation = any(violation_flags.values())
                    state = person_states.get(person.id)
                    if state is not None:
                        state.current_violation_flags = dict(violation_flags)
                        state.has_selected_item_violation = has_selected_item_violation

                    if has_selected_item_violation:
                        violating_candidate_count += 1

                    if not self._should_request_ocr(
                        person=person,
                        current_time_sec=frame_time_sec,
                        inspection_item_keys=inspection_item_keys,
                        state=state,
                    ):
                        continue

                    person.last_ocr_at_sec = frame_time_sec
                    if state is not None:
                        state.last_ocr_at_sec = frame_time_sec
                        state.ocr_attempt_count += 1
                    ocr_jobs.append((person, self.ocr_pool.submit(person.crop_image)))
                    ocr_request_count += 1

                for person, future in ocr_jobs:
                    ocr_data = future.result()
                    self.ocr_service.apply_ocr_result_to_person(person, ocr_data)
                    state = person_states.get(person.id)
                    if state is not None:
                        self._sync_person_state(state, person)

                aggregation.add_frame(
                    session_id=session_id,
                    segment_index=task.segment_index,
                    frame_no=frame_no,
                    frame_time_sec=frame_time_sec,
                    frame=frame,
                    people=people,
                )
                processed_frames += 1
                frame_index += 1

                for person in people:
                    person.crop_image = None
                del people
                del detected_people
                del frame

            people_results = aggregation.build_people_results()
            representative_frame_path = aggregation.get_representative_frame_path()
            representative_frame_info = aggregation.get_representative_frame_info()
            current_counts = {
                "detected_person_count": len(people_results),
                "confirmed_ocr_person_count": sum(
                    1 for item in people_results if item.get("ocr_confirmed")
                ),
                "helmet_not_worn_count": sum(
                    1 for item in people_results if item.get("helmet_status") != "WORN"
                ),
                "vest_not_worn_count": sum(
                    1 for item in people_results if item.get("vest_status") != "WORN"
                ),
            }
            logger.info(
                "[Segment] processed session_id=%s segment_index=%s frames=%s people=%s violating_candidates=%s ocr_requests=%s elapsed_sec=%.2f",
                session_id,
                task.segment_index,
                processed_frames,
                len(people_results),
                violating_candidate_count,
                ocr_request_count,
                time.perf_counter() - segment_started_at,
            )
            return VideoSegmentResult(
                segment_index=task.segment_index,
                segment_start_sec=task.segment_start_sec,
                segment_end_sec=task.segment_end_sec,
                processed_frames=processed_frames,
                people_results=people_results,
                representative_frame_path=representative_frame_path,
                representative_frame_info=representative_frame_info,
                current_counts=current_counts,
            )
        finally:
            cap.release()
            person_states.clear()
            aggregation.cleanup()
            del aggregation
            self._release_runtime_memory()

    def _run_yolo_prediction(self, frame):
        results = self.analyze_worker.run_inference_for_video(frame)
        return list(results.values())

    def _run_ocr_prediction(self, crop_image):
        if crop_image is None or getattr(crop_image, "size", 0) == 0:
            return None
        return self.ocr_engine.extract_worker_id(crop_image)

    def _sync_tracked_people(
        self,
        detected_people: list,
        person_states: dict[int, SegmentPersonState],
        frame_no: int,
    ) -> list:
        tracked_people = []
        for person in detected_people:
            state = person_states.get(person.id)
            if state is None:
                state = SegmentPersonState(
                    track_id=person.id,
                    bbox=list(person.bbox),
                    last_seen_frame_no=frame_no,
                )
                person_states[person.id] = state

            state.bbox = list(person.bbox)
            state.last_seen_frame_no = frame_no
            person.employee_no = state.employee_no
            person.ocr_confirmed = state.ocr_confirmed
            person.last_ocr_at_sec = state.last_ocr_at_sec
            person.ocr_candidate_counts = dict(state.ocr_candidate_counts)
            person.latest_ocr_regex_matched = state.last_regex_matched
            tracked_people.append(person)

        return tracked_people

    def _sync_person_state(self, state: SegmentPersonState, person) -> None:
        state.employee_no = getattr(person, "employee_no", None)
        state.ocr_confirmed = bool(getattr(person, "ocr_confirmed", False))
        state.last_ocr_at_sec = getattr(person, "last_ocr_at_sec", None)
        state.ocr_candidate_counts = dict(getattr(person, "ocr_candidate_counts", {}))
        state.last_regex_matched = bool(getattr(person, "latest_ocr_regex_matched", False))

    def _build_segment_tasks(
        self,
        total_frames: int,
        total_time_sec: float,
        fps: float,
    ) -> list[VideoSegmentTask]:
        if total_frames <= 0 or fps <= 0:
            return []

        segment_count = max(
            int(math.ceil(total_time_sec / self.segment_window_service.segment_seconds)),
            1,
        )
        tasks = []
        for segment_index in range(segment_count):
            segment_start_sec = self.segment_window_service.get_segment_start_sec(segment_index)
            segment_end_sec = self.segment_window_service.get_segment_end_sec(
                segment_index=segment_index,
                actual_end_sec=total_time_sec,
            )
            start_frame_index = min(int(segment_start_sec * fps), total_frames)
            end_frame_index = min(int(math.ceil(segment_end_sec * fps)), total_frames)
            if start_frame_index >= end_frame_index:
                continue

            tasks.append(
                VideoSegmentTask(
                    segment_index=segment_index,
                    segment_start_sec=segment_start_sec,
                    segment_end_sec=segment_end_sec,
                    start_frame_index=start_frame_index,
                    end_frame_index=end_frame_index,
                )
            )

        return tasks

    def _should_request_ocr(
        self,
        person,
        current_time_sec: float,
        inspection_item_keys: list[str] | None,
        state: SegmentPersonState | None,
    ) -> bool:
        ocr_attempt_count = state.ocr_attempt_count if state is not None else 0
        return self.ocr_service.should_run_ocr_for_person(
            person=person,
            current_time_sec=current_time_sec,
            inspection_item_keys=inspection_item_keys,
            ocr_attempt_count=ocr_attempt_count,
            max_attempt_count=self.max_track_ocr_count,
        )

    def _calculate_iou(self, bbox1: list[int], bbox2: list[int]) -> float:
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        if intersection <= 0:
            return 0.0

        area1 = max(0, bbox1[2] - bbox1[0]) * max(0, bbox1[3] - bbox1[1])
        area2 = max(0, bbox2[2] - bbox2[0]) * max(0, bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection
        if union <= 0:
            return 0.0
        return intersection / union

    def _drain_queue(self, target_queue: queue.Queue) -> None:
        while True:
            try:
                item = target_queue.get_nowait()
            except queue.Empty:
                break
            target_queue.task_done()
            if hasattr(item, "people_results"):
                item.people_results.clear()
            if hasattr(item, "representative_frame_info") and item.representative_frame_info is not None:
                item.representative_frame_info.clear()

    def _release_runtime_memory(self) -> None:
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
