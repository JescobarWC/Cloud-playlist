from app.domain.normalize import normalize_library_payload


def test_normalize_library_payload_sets_defaults_and_filters_playlist_ids() -> None:
    snapshot = normalize_library_payload(
        raw_tracks=[
            {
                "id": "1",
                "title": "Losing It",
                "artist": "FISHER",
                "bpm": "125",
                "cue_points": [{"position_seconds": "32.5", "label": "Drop"}],
                "beatgrid": [{"position_seconds": "0", "bpm": "125"}],
            },
            {
                "title": None,
                "artist": None,
            },
        ],
        raw_playlists=[
            {
                "id": "pl-1",
                "name": "Peak Time",
                "track_ids": ["1", "does-not-exist"],
            }
        ],
    )

    assert len(snapshot.tracks) == 2
    assert snapshot.tracks[0].bpm == 125.0
    assert snapshot.tracks[0].cue_points[0].position_seconds == 32.5
    assert snapshot.tracks[1].title == "Unknown title"
    assert snapshot.tracks[1].artist == "Unknown artist"

    assert len(snapshot.playlists) == 1
    assert snapshot.playlists[0].track_ids == ["1"]


def test_normalize_library_payload_ignores_invalid_timing_values() -> None:
    snapshot = normalize_library_payload(
        raw_tracks=[
            {
                "id": "track-1",
                "title": "Track",
                "artist": "Artist",
                "cue_points": [{"position_seconds": "bad-value", "label": "X"}],
                "beatgrid": [{"position_seconds": "0", "bpm": "bad-value"}],
            }
        ],
        raw_playlists=[],
    )

    assert snapshot.tracks[0].cue_points == []
    assert snapshot.tracks[0].beatgrid == []
