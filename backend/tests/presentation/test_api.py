import pytest
from app import create_app
from datetime import datetime


@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_create_session(client):
    data = {
        "source_type": "WEBCAM",
        "source_name": "Test-Cam",
        "frame_interval_sec": 3,
        "requested_by": "tester"
    }
    response = client.post("/api/v1/sessions", json=data)
    assert response.status_code == 201
    json_data = response.get_json()
    assert "session_id" in json_data
    assert json_data["status"] == "QUEUED"


def test_create_session_bad_request(client):
    data = {"source_type": "INVALID_TYPE"}
    response = client.post("/api/v1/sessions", json=data)
    assert response.status_code == 400


@pytest.fixture
def test_session(client):
    data = {"source_type": "VIDEO_FILE"}
    response = client.post("/api/v1/sessions", json=data)
    return response.get_json()["session_id"]


def test_get_session(client, test_session):
    response = client.get(f"/api/v1/sessions/{test_session}")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["session_id"] == test_session


def test_get_session_not_found(client):
    response = client.get("/api/v1/sessions/non-existent")
    assert response.status_code == 404


def test_stop_session(client, test_session):
    response = client.post(f"/api/v1/sessions/{test_session}/stop")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "STOPPED"


def test_stop_session_not_found(client):
    response = client.post("/api/v1/sessions/non-existent/stop")
    assert response.status_code == 404


@pytest.fixture
def test_result(app, test_session):
    from decimal import Decimal

    from app.infrastructure.db.repositories.analysis_session_repository import SQLAlchemyAnalysisSessionRepository
    from app.infrastructure.db.repositories.analysis_frame_repository import SQLAlchemyAnalysisFrameRepository
    from app.infrastructure.db.repositories.detection_result_repository import SQLAlchemyDetectionResultRepository

    from app.application.usecases.process_detection_result import ProcessDetectionResultUseCase
    from app.application.dtos import ProcessDetectionCommand

    from app.domain.entities.analysis_frame import AnalysisFrame, FrameProcessingStatus
    from app.domain.entities.detection_result import ItemWearStatus

    with app.app_context():
        session_repo = SQLAlchemyAnalysisSessionRepository()
        frame_repo = SQLAlchemyAnalysisFrameRepository()
        result_repo = SQLAlchemyDetectionResultRepository()

        session = session_repo.find_by_session_id(test_session)
        assert session is not None
        assert session.id is not None

        frame = AnalysisFrame(
            session_id=session.id,
            frame_no=1,
            frame_time_sec=Decimal("0.0"),
            person_count=0,
            processing_status=FrameProcessingStatus.PENDING,
            frame_image_path="frame_1.jpg",
        )
        frame_repo.save(frame)

        usecase = ProcessDetectionResultUseCase(session_repo, frame_repo, result_repo)

        cmd = ProcessDetectionCommand(
            session_id=test_session,
            frame_id=frame.id,
            person_index=1,
            employee_no="123",
            ocr_text="123",
            ocr_confidence=Decimal("0.99"),
            helmet_status=ItemWearStatus.WEARING,
            vest_status=ItemWearStatus.WEARING,
            person_box_x=0,
            person_box_y=0,
            person_box_width=100,
            person_box_height=100,
            crop_image_path="test.jpg",
        )

        result = usecase.execute(cmd)
        return {"session_id_str": test_session, "result_id": result.id}


def test_get_session_results(client, test_result):
    session_id_str = test_result["session_id_str"]
    response = client.get(f"/api/v1/sessions/{session_id_str}/results")
    assert response.status_code == 200
    assert len(response.get_json()) >= 1


def test_get_result(client, test_result):
    result_id = test_result["result_id"]
    response = client.get(f"/api/v1/results/{result_id}")
    assert response.status_code == 200
    assert response.get_json()["id"] == result_id


def test_get_recent_results(client, test_result):
    response = client.get("/api/v1/results")
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
    assert len(response.get_json()) >= 1


def test_get_recent_results_limit(client, test_result):
    response = client.get("/api/v1/results?limit=1")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) <= 1


def test_get_result_not_found(client):
    response = client.get("/api/v1/results/99999")
    assert response.status_code == 404