from app.infrastructure.library_repository import LibraryRepository


def test_duplicate_finder_and_find_replace_with_undo(tmp_path) -> None:
    repository = LibraryRepository(db_path=tmp_path / "app.db")
    playlist_id = repository.create_playlist("Set")

    t1 = repository.add_track_to_playlist(playlist_id, "My Song", "Artist X", "/a.wav")
    t2 = repository.add_track_to_playlist(playlist_id, "my song", "artist x", "/b.wav")
    repository.add_track_to_playlist(playlist_id, "Other", "Artist Y", "/c.wav")

    duplicates = repository.find_duplicate_tracks()
    assert len(duplicates) == 1
    assert duplicates[0]["track_count"] == 2
    assert set(duplicates[0]["track_ids"]) == {t1, t2}

    preview = repository.preview_find_replace("title", "Song", "Track")
    assert len(preview) >= 1

    result = repository.apply_find_replace("op-1", "title", "Song", "Track")
    assert result["changed_tracks"] >= 1

    restored = repository.undo_find_replace("op-1")
    assert restored["restored_tracks"] >= 1
