"""Unit tests for AbletonMCP Remote Script helpers."""

import os
import sys
import types
from unittest.mock import MagicMock


class _StubControlSurface:
    def __init__(self, c_instance):
        pass

    def log_message(self, msg):
        pass


_framework = types.ModuleType("_Framework")
_cs_module = types.ModuleType("_Framework.ControlSurface")
_cs_module.ControlSurface = _StubControlSurface
sys.modules.setdefault("_Framework", _framework)
sys.modules.setdefault("_Framework.ControlSurface", _cs_module)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from AbletonMCP_Remote_Script import AbletonMCP  # noqa: E402


class _NormalTrack:
    is_foldable = False

    def __init__(self, name="Track", arm=False, has_midi_input=True,
                 has_audio_input=False, arrangement_clips=None):
        self.name = name
        self.arm = arm
        self.mute = False
        self.solo = False
        self.has_midi_input = has_midi_input
        self.has_audio_input = has_audio_input
        self.clip_slots = []
        self.devices = []
        self.arrangement_clips = list(arrangement_clips or [])
        self.mixer_device = MagicMock()
        self.mixer_device.volume.value = 0.85
        self.mixer_device.panning.value = 0.0


class _GroupTrack:
    is_foldable = True

    def __init__(self, name="Mix Bus"):
        self.name = name
        self.mute = False
        self.solo = False
        self.has_midi_input = False
        self.has_audio_input = False
        self.clip_slots = []
        self.devices = []
        self.mixer_device = MagicMock()
        self.mixer_device.volume.value = 0.85
        self.mixer_device.panning.value = 0.0

    @property
    def arm(self):
        raise RuntimeError("Master and Return Tracks have no 'Arm' state!")

    @property
    def arrangement_clips(self):
        raise RuntimeError(
            "Master, Group and Return Tracks have no arrangement clips")


def _make_script(tracks=()):
    script = AbletonMCP.__new__(AbletonMCP)
    script.log_message = lambda msg: None
    script._song = MagicMock()
    script._song.tracks = list(tracks)
    script._song.return_tracks = []
    script._song.master_track = MagicMock()
    script._song.current_song_time = 0.0
    return script


class TestGetTrackInfoOnGroupTrack:
    def test_returns_info_without_raising(self):
        script = _make_script([_GroupTrack("Mix Bus")])

        result = script._get_track_info(0)

        assert result["name"] == "Mix Bus"
        assert result["is_group_track"] is True
        assert result["arm"] is None

    def test_normal_track_still_reports_arm(self):
        script = _make_script([_NormalTrack("Synth", arm=True)])

        result = script._get_track_info(0)

        assert result["arm"] is True
        assert result["is_group_track"] is False


class TestCreateAudioTrack:
    def test_create_audio_track_at_end(self):
        existing = _NormalTrack("1-MIDI")
        created = _NormalTrack("2-Audio", has_midi_input=False, has_audio_input=True)
        script = _make_script([existing])

        def create_audio_track(index):
            assert index == -1
            script._song.tracks.append(created)

        script._song.create_audio_track.side_effect = create_audio_track

        result = script._create_audio_track(-1)

        assert result == {"index": 1, "name": "2-Audio"}

    def test_create_audio_track_at_index(self):
        first = _NormalTrack("1-MIDI")
        second = _NormalTrack("2-MIDI")
        created = _NormalTrack("2-Audio", has_midi_input=False, has_audio_input=True)
        script = _make_script([first, second])

        def create_audio_track(index):
            assert index == 1
            script._song.tracks.insert(index, created)

        script._song.create_audio_track.side_effect = create_audio_track

        result = script._create_audio_track(1)

        assert result == {"index": 1, "name": "2-Audio"}


class TestGetArrangementInfoSkipsGroupTracks:
    def test_all_tracks_skips_group(self):
        normal = _NormalTrack("Drums")
        group = _GroupTrack("Mix Bus")
        script = _make_script([group, normal])

        result = script._get_arrangement_info(-1)

        names = [t["name"] for t in result["tracks"]]
        assert names == ["Drums"]

    def test_explicit_group_returns_empty_clips(self):
        script = _make_script([_GroupTrack("Mix Bus")])

        result = script._get_arrangement_info(0)

        assert len(result["tracks"]) == 1
        assert result["tracks"][0]["arrangement_clips"] == []
        assert result["tracks"][0]["is_group_track"] is True

    def test_normal_track_unaffected(self):
        script = _make_script([_NormalTrack("Drums")])

        result = script._get_arrangement_info(0)

        assert result["tracks"][0]["name"] == "Drums"
        assert result["tracks"][0]["is_group_track"] is False


class TestCreateCuePointAssignsName:
    @staticmethod
    def _wire_toggle(script, returned_cue):
        script._song.cue_points = ()

        def toggle():
            script._song.cue_points = (returned_cue,)

        script._song.set_or_delete_cue.side_effect = toggle

    def test_assigns_name_to_created_cue(self):
        script = _make_script()
        cue = MagicMock()
        cue.time = 16.0
        cue.name = ""
        self._wire_toggle(script, cue)

        script._create_cue_point(time=16.0, name="Drop")

        assert cue.name == "Drop"
        assert script._song.current_song_time == 16.0
        assert script._song.start_time == 16.0

    def test_blank_name_does_not_overwrite(self):
        script = _make_script()
        cue = MagicMock()
        cue.time = 16.0
        cue.name = "1.1.1"
        self._wire_toggle(script, cue)

        script._create_cue_point(time=16.0, name="")

        assert cue.name == "1.1.1"

    def test_name_assignment_failure_does_not_fail_created_cue(self):
        class ReadOnlyNameCue:
            time = 16.0

            @property
            def name(self):
                return "1.1.1"

            @name.setter
            def name(self, value):
                raise AttributeError("can't set attribute")

        script = _make_script()
        cue = ReadOnlyNameCue()
        self._wire_toggle(script, cue)

        result = script._create_cue_point(time=16.0, name="Drop")

        assert result == {"time": 16.0, "name": "Drop"}

    def test_updates_current_and_start_time_before_creating(self):
        script = _make_script()
        script._song.current_song_time = 716.0
        cue = MagicMock()
        cue.time = 16.0
        cue.name = ""
        self._wire_toggle(script, cue)

        script._create_cue_point(time=16.0, name="")

        assert script._song.current_song_time == 16.0
        assert script._song.start_time == 16.0

    def test_rolls_back_when_cue_created_at_wrong_time(self):
        script = _make_script()
        cue = MagicMock()
        cue.time = 128.0
        cue.name = "1"
        self._wire_toggle(script, cue)

        try:
            script._create_cue_point(time=16.0, name="")
        except ValueError as exc:
            assert "wrong position" in str(exc)
        else:
            raise AssertionError("Expected wrong-position cue creation to fail")

        script._song.undo.assert_called_once()

    def test_snapshots_wrong_cue_time_before_rollback(self):
        class InvalidAfterUndoCue:
            def __init__(self, script):
                self.script = script
                self.name = "1"

            @property
            def time(self):
                if self.script._undone:
                    raise TypeError("Cue object is invalid after undo")
                return 128.0

        script = _make_script()
        script._undone = False

        def undo():
            script._undone = True

        script._song.undo.side_effect = undo
        cue = InvalidAfterUndoCue(script)
        self._wire_toggle(script, cue)

        try:
            script._create_cue_point(time=16.0, name="")
        except ValueError as exc:
            assert "128.0" in str(exc)
        else:
            raise AssertionError("Expected wrong-position cue creation to fail")

    def test_does_not_compare_live_cue_objects_directly(self):
        class Cue:
            def __init__(self, time):
                self.time = time
                self.name = ""

            def __eq__(self, other):
                raise TypeError("Live object equality is unavailable")

        script = _make_script()
        cue = Cue(16.0)
        self._wire_toggle(script, cue)

        result = script._create_cue_point(time=16.0, name="")

        assert result == {"time": 16.0, "name": ""}


class TestDeleteCuePoint:
    def test_deletes_cue_at_requested_time(self):
        script = _make_script()
        cue = MagicMock()
        cue.time = 16.0
        cue.name = "1"
        script._song.cue_points = (cue,)

        def toggle():
            script._song.cue_points = ()

        script._song.set_or_delete_cue.side_effect = toggle

        result = script._delete_cue_point(time=16.0)

        assert result == {"deleted": True}
        assert script._song.current_song_time == 16.0
        assert script._song.start_time == 16.0
        script._song.undo.assert_not_called()

    def test_rolls_back_when_delete_does_not_remove_requested_cue(self):
        script = _make_script()
        cue = MagicMock()
        cue.time = 16.0
        cue.name = "1"
        script._song.cue_points = (cue,)

        try:
            script._delete_cue_point(time=16.0)
        except ValueError as exc:
            assert "not deleted" in str(exc)
        else:
            raise AssertionError("Expected failed cue deletion")

        script._song.undo.assert_called_once()
