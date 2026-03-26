from app.domain.entities.analysis_segment import AnalysisSegmentPersonResult, SegmentWearStatus
from app.domain.ports.repository import AnalysisSegmentPersonResultRepository
from app.infrastructure.service_db.models.analysis_segment_person_result import (
    AnalysisSegmentPersonResultModel,
)
from app.infrastructure.service_db.session import SessionLocal


class SQLAlchemyAnalysisSegmentPersonResultRepository(
    AnalysisSegmentPersonResultRepository
):
    def _to_domain(self, model: AnalysisSegmentPersonResultModel) -> AnalysisSegmentPersonResult:
        return AnalysisSegmentPersonResult(
            id=model.id,
            segment_summary_id=model.segment_summary_id,
            track_id=model.track_id,
            employee_id=model.employee_id,
            ocr_number=model.ocr_number,
            ocr_confirmed=model.ocr_confirmed,
            helmet_status=SegmentWearStatus(model.helmet_status),
            vest_status=SegmentWearStatus(model.vest_status),
            observed_frames=model.observed_frames,
            helmet_detected_frames=model.helmet_detected_frames,
            vest_detected_frames=model.vest_detected_frames,
            regex_match_count=model.regex_match_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def save_many(self, results: list[AnalysisSegmentPersonResult]):
        if not results:
            return

        with SessionLocal() as db_session:
            models = []
            for result in results:
                model = AnalysisSegmentPersonResultModel(
                    id=result.id,
                    segment_summary_id=result.segment_summary_id,
                    track_id=result.track_id,
                    employee_id=result.employee_id,
                    ocr_number=result.ocr_number,
                    ocr_confirmed=result.ocr_confirmed,
                    helmet_status=result.helmet_status.value,
                    vest_status=result.vest_status.value,
                    observed_frames=result.observed_frames,
                    helmet_detected_frames=result.helmet_detected_frames,
                    vest_detected_frames=result.vest_detected_frames,
                    regex_match_count=result.regex_match_count,
                    created_at=result.created_at,
                    updated_at=result.updated_at,
                )
                models.append(model)

            db_session.add_all(models)
            db_session.commit()

            for result, model in zip(results, models):
                result.id = model.id

    def find_by_segment_summary_ids(self, segment_summary_ids: list[int]):
        if not segment_summary_ids:
            return {}

        with SessionLocal() as db_session:
            models = (
                db_session.query(AnalysisSegmentPersonResultModel)
                .filter(AnalysisSegmentPersonResultModel.segment_summary_id.in_(segment_summary_ids))
                .order_by(
                    AnalysisSegmentPersonResultModel.segment_summary_id.asc(),
                    AnalysisSegmentPersonResultModel.track_id.asc(),
                )
                .all()
            )

            grouped = {segment_summary_id: [] for segment_summary_id in segment_summary_ids}
            for model in models:
                grouped.setdefault(model.segment_summary_id, []).append(self._to_domain(model))

            return grouped
