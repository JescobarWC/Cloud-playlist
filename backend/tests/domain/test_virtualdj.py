from app.domain.virtualdj import parse_virtualdj_database_xml


def test_parse_virtualdj_database_xml_tracks_and_playlists() -> None:
    xml = """
    <VirtualDJ_Database>
      <Song FilePath="/music/a.mp3">
        <Tags Author="Artist A" Title="Track A" Bpm="124.5" />
      </Song>
      <Song FilePath="/music/b.mp3">
        <Tags Author="Artist B" Title="Track B" Bpm="bad" />
      </Song>
      <Playlists>
        <Playlist Name="Main Set">
          <Song FilePath="/music/a.mp3" />
          <Song FilePath="/music/missing.mp3" />
        </Playlist>
      </Playlists>
    </VirtualDJ_Database>
    """

    tracks, playlists = parse_virtualdj_database_xml(xml)

    assert len(tracks) == 2
    assert tracks[0]["title"] == "Track A"
    assert tracks[0]["artist"] == "Artist A"
    assert tracks[0]["bpm"] == 124.5

    assert playlists[0]["name"] == "Main Set"
    assert playlists[0]["track_ids"] == ["vdj-1"]


def test_parse_virtualdj_database_xml_defaults_missing_tags() -> None:
    xml = """
    <VirtualDJ_Database>
      <Song FilePath="/music/a.mp3" />
    </VirtualDJ_Database>
    """

    tracks, playlists = parse_virtualdj_database_xml(xml)

    assert len(tracks) == 1
    assert tracks[0]["title"] == "Unknown title"
    assert tracks[0]["artist"] == "Unknown artist"
    assert tracks[0]["bpm"] is None
    assert playlists == []
