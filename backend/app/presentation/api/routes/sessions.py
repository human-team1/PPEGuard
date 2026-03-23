from flask import Blueprint, request, jsonify
from app.infrastructure.service_db.repositories.analysis_session_repository import SQLAlchemyAnalysisSessionRepository
from app.infrastructure.service_db.repositories.detection_result_repository import SQLAlchemyDetectionResultRepository
from app.application.usecases.start_analysis_session import StartAnalysisSessionUseCase
from app.application.usecases.get_analysis_session import GetAnalysisSessionUseCase
from app.application.usecases.stop_analysis_session import StopAnalysisSessionUseCase
from app.application.usecases.get_session_results import GetSessionResultsUseCase
from app.application.dtos import StartSessionCommand
from app.domain.entities.analysis_session import AnalysisSourceType
from app.presentation.api.schemas.serializers import serialize

sessions_bp = Blueprint('sessions', __name__, url_prefix='/api/v1/sessions')

def get_session_repo():
    return SQLAlchemyAnalysisSessionRepository()

def get_result_repo():
    return SQLAlchemyDetectionResultRepository()

@sessions_bp.route('', methods=['POST'])
def create_session():
    data = request.get_json() or {}
    try:
        source_type_str = data.get('source_type', 'WEBCAM')
        source_type = AnalysisSourceType[source_type_str]
        
        cmd = StartSessionCommand(
            source_type=source_type,
            frame_interval_sec=int(data.get('frame_interval_sec', 3)),
            source_name=data.get('source_name'),
            requested_by=data.get('requested_by')
        )
    except KeyError as e:
        return jsonify({"error": "Bad Request", "details": f"source_type '{source_type_str}' is not valid. Use WEBCAM or VIDEO_FILE."}), 400
    except Exception as e:
        return jsonify({"error": "Bad Request", "details": str(e)}), 400

    try:
        usecase = StartAnalysisSessionUseCase(get_session_repo())
        session = usecase.execute(cmd)
        return jsonify(serialize(session)), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return jsonify({"error": "Internal Server Error", "details": str(e), "trace": error_trace}), 500

@sessions_bp.route('/<session_id>', methods=['GET'])
def get_session(session_id: str):
    usecase = GetAnalysisSessionUseCase(get_session_repo())
    session = usecase.execute(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(serialize(session)), 200

@sessions_bp.route('/<session_id>/stop', methods=['POST'])
def stop_session(session_id: str):
    usecase = StopAnalysisSessionUseCase(get_session_repo())
    try:
        session = usecase.execute(session_id)
        return jsonify(serialize(session)), 200
    except ValueError:
        return jsonify({"error": "Session not found"}), 404

@sessions_bp.route('/<session_id>/results', methods=['GET'])
def get_session_results(session_id: str):
    usecase = GetSessionResultsUseCase(get_session_repo(), get_result_repo())
    try:
        results = usecase.execute(session_id)
        return jsonify(serialize(results)), 200
    except ValueError:
        return jsonify({"error": "Session not found"}), 404
