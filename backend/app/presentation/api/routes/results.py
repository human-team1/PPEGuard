from flask import Blueprint, request, jsonify
from app.infrastructure.service_db.repositories.detection_result_repository import SQLAlchemyDetectionResultRepository
from app.application.usecases.get_recent_results import GetRecentResultsUseCase
from app.application.usecases.get_detection_result import GetDetectionResultUseCase
from app.presentation.api.schemas.serializers import serialize

results_bp = Blueprint('results', __name__, url_prefix='/api/v1/results')

def get_result_repo():
    return SQLAlchemyDetectionResultRepository()

@results_bp.route('', methods=['GET'])
def get_recent_results():
    try:
        limit = int(request.args.get('limit', 20))
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400
        
    usecase = GetRecentResultsUseCase(get_result_repo())
    results = usecase.execute(limit=limit)
    return jsonify(serialize(results)), 200

@results_bp.route('/<int:result_id>', methods=['GET'])
def get_result(result_id: int):
    usecase = GetDetectionResultUseCase(get_result_repo())
    result = usecase.execute(result_id)
    if not result:
        return jsonify({"error": "Result not found"}), 404
    return jsonify(serialize(result)), 200
