from flask import Blueprint, request, jsonify
from app.infrastructure.dependencies import (
    build_get_detection_result_usecase,
    build_get_recent_results_usecase,
)
from app.presentation.api.schemas.serializers import serialize

results_bp = Blueprint('results', __name__, url_prefix='/api/v1/results')

@results_bp.route('', methods=['GET'])
def get_recent_results():
    try:
        limit = int(request.args.get('limit', 20))
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400
        
    usecase = build_get_recent_results_usecase()
    results = usecase.execute(limit=limit)
    return jsonify(serialize(results)), 200

@results_bp.route('/<int:result_id>', methods=['GET'])
def get_result(result_id: int):
    usecase = build_get_detection_result_usecase()

    try:
        result = usecase.execute(result_id)
        return jsonify(serialize(result)), 200
    except ValueError:
        return jsonify({"error": "Result not found"}), 404
