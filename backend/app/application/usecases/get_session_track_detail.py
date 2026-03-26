from app.application.usecases.get_session_tracks import GetSessionTracksUseCase


class GetSessionTrackDetailUseCase:
    def __init__(self, session_repo, track_summary_repo):
        self.session_repo = session_repo
        self.track_summary_repo = track_summary_repo

    def execute(self, session_id: str, track_id: int):
        session = self.session_repo.find_by_session_id(session_id)
        if session is None or session.id is None:
            raise ValueError("Analysis session not found")

        track = self.track_summary_repo.find_by_session_and_track_id(session.id, int(track_id))
        if track is None:
            raise ValueError("Track summary not found")

        return GetSessionTracksUseCase._to_dto(track)
