from app.domain.entities.detection_result import ItemWearStatus


class VideoAnalysisAggregationService:
    def __init__(self, process_detection_result_usecase):
        self.process_detection_result_usecase = process_detection_result_usecase

    def aggregate_and_save(self, buffer: dict) -> None:
        for person_id, frames_data in buffer.items():
            if not frames_data:
                continue

            avg_helmet_conf = sum(data["helmet_conf"] for data in frames_data) / len(frames_data)
            avg_vest_conf = sum(data["vest_conf"] for data in frames_data) / len(frames_data)

            print(
                f"  ==> [AggregationLog] Person {person_id} (Data Count: {len(frames_data)}): "
                f"Avg Helmet={avg_helmet_conf:.4f}, Avg Vest={avg_vest_conf:.4f}"
            )

            final_cmd = frames_data[-1]["cmd"]
            final_cmd.helmet_status = (
                ItemWearStatus.WEARING if avg_helmet_conf >= 0.7 else ItemWearStatus.NOT_WEARING
            )
            final_cmd.vest_status = (
                ItemWearStatus.WEARING if avg_vest_conf >= 0.7 else ItemWearStatus.NOT_WEARING
            )

            self.process_detection_result_usecase.execute(final_cmd)
            print(
                f"[VideoAnalysis] 집계 결과 저장 완료 - Person ID: {person_id}, "
                f"Helmet_Avg: {avg_helmet_conf:.2f}, Vest_Avg: {avg_vest_conf:.2f}"
            )
