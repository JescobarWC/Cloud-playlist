import pytest
from app.infrastructure.library_repository import LibraryRepository


def test_playback_controls_and_navigation(tmp_path) -> None:
    repository = LibraryRepository(db_path=tmp_path / "app.db")
    playlist_id = repository.create_playlist("Set")

    first_track = repository.add_track_to_playlist(playlist_id, "A", "Artist", "/a.wav")
    second_track = repository.add_track_to_playlist(playlist_id, "B", "Artist", "/b.wav")

    state = repository.get_playback_state(playlist_id)
    assert state["current_track_id"] == first_track
    assert state["is_playing"] is False

    state = repository.set_playing(playlist_id, True)
    assert state["is_playing"] is True

    state = repository.seek(playlist_id, 12.5)
    assert state["current_position_seconds"] == 12.5

    state = repository.move_track(playlist_id, "next")
    assert state["current_track_id"] == second_track
    assert state["current_position_seconds"] == 0.0

    state = repository.move_track(playlist_id, "previous")
    assert state["current_track_id"] == first_track


def test_set_current_track_requires_track_inside_playlist(tmp_path) -> None:
    repository = LibraryRepository(db_path=tmp_path / "app.db")
    playlist_id = repository.create_playlist("Set")
    repository.add_track_to_playlist(playlist_id, "A", "Artist", "/a.wav")

    with pytest.raises(ValueError, match="is not in playlist"):
        repository.set_current_track(playlist_id, 999)
