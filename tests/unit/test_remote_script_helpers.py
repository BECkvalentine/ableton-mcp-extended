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
        self.can_be_armed = True
        self.color = 0
        self.clip_slots = []
        self.devices = []
        self.arrangement_clips = list(arrangement_clips or [])
        self.mixer_device = MagicMock()
        self.mixer_device.volume.value = 0.85
        self.mixer_device.volume.min = 0.0
        self.mixer_device.volume.max = 1.0
        self.mixer_device.panning.value = 0.0
        self.mixer_device.panning.min = -1.0
        self.mixer_device.panning.max = 1.0
        send = MagicMock()
        send.value = 0.0
        self.mixer_device.sends = [send]


class _ReturnTrack:
    def __init__(self, name="A-Reverb"):
        self.name = name
        self.mute = False
        self.color = 0
        self.devices = []
        self.mixer_device = MagicMock()
        self.mixer_device.volume.value = 0.85
        self.mixer_device.volume.min = 0.0
        self.mixer_device.volume.max = 1.0
        self.mixer_device.panning.value = 0.0
        self.mixer_device.panning.min = -1.0
        self.mixer_device.panning.max = 1.0

    def delete_device(self, device_index):
        del self.devices[device_index]


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


class _Scene:
    def __init__(self, name="", color=0, tempo=0.0):
        self.name = name
        self.color = color
        self.tempo = tempo
        self.fire = MagicMock()


def _make_script(tracks=()):
    script = AbletonMCP.__new__(AbletonMCP)
    script.log_message = lambda msg: None
    script._song = MagicMock()
    script._song.tracks = list(tracks)
    script._song.scenes = []
    script._song.return_tracks = []
    script._song.master_track = MagicMock()
    script._song.master_track.mixer_device.volume.value = 0.85
    script._song.master_track.mixer_device.volume.min = 0.0
    script._song.master_track.mixer_device.volume.max = 1.0
    script._song.master_track.mixer_device.panning.value = 0.0
    script._song.master_track.mixer_device.panning.min = -1.0
    script._song.master_track.mixer_device.panning.max = 1.0
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

    def test_blank_name_does_not_overwrite(self):
        script = _make_script()
        cue = MagicMock()
        cue.time = 16.0
        cue.name = "1.1.1"
        self._wire_toggle(script, cue)

        script._create_cue_point(time=16.0, name="")

        assert cue.name == "1.1.1"


class TestMixerHelpers:
    def test_track_mute_solo_arm_and_color(self):
        track = _NormalTrack("Keys")
        script = _make_script([track])

        assert script._set_track_mute(0, True) == {"track_name": "Keys", "mute": True}
        assert script._set_track_solo(0, True) == {"track_name": "Keys", "solo": True}
        assert script._set_track_arm(0, True) == {"track_name": "Keys", "arm": True}
        assert script._set_track_color(0, 0x336699) == {
            "track_name": "Keys",
            "color": 0x336699,
        }

    def test_return_track_controls(self):
        script = _make_script()
        script._song.return_tracks = [_ReturnTrack("A-Reverb")]

        assert script._set_return_track_name(0, "A-Verb") == {"name": "Verb"}
        assert script._set_return_track_volume(0, 1.2) == {
            "track_name": "Verb",
            "volume": 1.0,
        }
        assert script._set_return_track_panning(0, -2.0) == {
            "track_name": "Verb",
            "panning": -1.0,
        }
        assert script._set_return_track_mute(0, True) == {
            "track_name": "Verb",
            "mute": True,
        }
        assert script._set_return_track_color(0, 0xFFAA00) == {
            "track_name": "Verb",
            "color": 0xFFAA00,
        }

    def test_get_return_tracks(self):
        script = _make_script()
        script._song.return_tracks = [_ReturnTrack("A-Reverb")]

        result = script._get_return_tracks()

        assert result["return_track_count"] == 1
        assert result["return_tracks"][0]["name"] == "A-Reverb"
        assert result["return_tracks"][0]["volume"] == 0.85

    def test_create_return_track(self):
        script = _make_script()

        def create_return_track():
            script._song.return_tracks.append(_ReturnTrack("B-Delay"))

        script._song.create_return_track.side_effect = create_return_track

        result = script._create_return_track()

        script._song.create_return_track.assert_called_once_with()
        assert result == {"index": 0, "name": "B-Delay"}

    def test_delete_return_track(self):
        script = _make_script()
        script._song.return_tracks = [_ReturnTrack("B-Delay")]

        def delete_return_track(index):
            del script._song.return_tracks[index]

        script._song.delete_return_track.side_effect = delete_return_track

        result = script._delete_return_track(0)

        script._song.delete_return_track.assert_called_once_with(0)
        assert result == {
            "deleted_return_track": "B-Delay",
            "remaining_return_tracks": 0,
        }

    def test_delete_device_can_target_return_track(self):
        track = _NormalTrack("Keys")
        return_track = _ReturnTrack("A-Reverb")
        device = MagicMock()
        device.name = "Hybrid Reverb"
        return_track.devices = [device]
        script = _make_script([track])
        script._song.return_tracks = [return_track]

        result = script._delete_device(1, 0)

        assert result == {
            "deleted_device": "Hybrid Reverb",
            "remaining_devices": 0,
        }
        assert return_track.devices == []

    def test_master_controls_clamp_values(self):
        script = _make_script()

        assert script._set_master_volume(2.0) == {"volume": 1.0}
        assert script._set_master_panning(-2.0) == {"panning": -1.0}

    def test_set_send_clamps_amount(self):
        track = _NormalTrack("Vocal")
        script = _make_script([track])
        script._song.return_tracks = [_ReturnTrack("A-Reverb")]

        result = script._set_send(0, 0, 2.0)

        assert track.mixer_device.sends[0].value == 1.0
        assert result == {
            "source_track_name": "Vocal",
            "return_track_index": 0,
            "send_amount": 1.0,
        }


class TestSetSceneName:
    def test_renames_existing_scene(self):
        script = _make_script()
        script._song.scenes = [_Scene("Old")]

        result = script._set_scene_name(0, "Intro")

        assert script._song.scenes[0].name == "Intro"
        assert result == {"index": 0, "name": "Intro", "color": 0, "tempo": 0.0}

    def test_can_create_missing_scenes(self):
        script = _make_script()

        def create_scene(index):
            script._song.scenes.insert(index, _Scene(""))

        script._song.create_scene.side_effect = create_scene

        result = script._set_scene_name(2, "Chorus", create_missing=True)

        assert len(script._song.scenes) == 3
        assert script._song.scenes[2].name == "Chorus"
        assert result == {"index": 2, "name": "Chorus", "color": 0, "tempo": 0.0}

    def test_raises_when_scene_is_missing_without_create_flag(self):
        script = _make_script()

        try:
            script._set_scene_name(0, "Intro")
            raised = False
        except IndexError:
            raised = True

        assert raised is True


class TestSceneManagement:
    def test_get_scenes_returns_scene_details(self):
        script = _make_script()
        script._song.scenes = [
            _Scene("Intro", color=0x112233),
            _Scene("Verse", tempo=118.5),
        ]

        result = script._get_scenes()

        assert result == {
            "scene_count": 2,
            "scenes": [
                {"index": 0, "name": "Intro", "color": 0x112233, "tempo": 0.0},
                {"index": 1, "name": "Verse", "color": 0, "tempo": 118.5},
            ],
        }

    def test_create_scene_appends(self):
        script = _make_script()

        def create_scene(index):
            insert_at = len(script._song.scenes) if index == -1 else index
            script._song.scenes.insert(insert_at, _Scene("New"))

        script._song.create_scene.side_effect = create_scene

        result = script._create_scene(-1)

        script._song.create_scene.assert_called_once_with(-1)
        assert result == {"index": 0, "name": "New", "color": 0, "tempo": 0.0}

    def test_delete_scene_removes_by_index(self):
        script = _make_script()
        script._song.scenes = [_Scene("Intro")]

        result = script._delete_scene(0)

        script._song.delete_scene.assert_called_once_with(0)
        assert result == {"deleted_index": 0, "name": "Intro"}

    def test_duplicate_scene_reports_new_index(self):
        script = _make_script()
        script._song.scenes = [_Scene("Intro")]

        def duplicate_scene(index):
            scene = script._song.scenes[index]
            script._song.scenes.insert(index + 1, _Scene(scene.name))

        script._song.duplicate_scene.side_effect = duplicate_scene

        result = script._duplicate_scene(0)

        script._song.duplicate_scene.assert_called_once_with(0)
        assert result == {"source_index": 0, "new_index": 1, "name": "Intro"}

    def test_fire_scene_launches_scene(self):
        script = _make_script()
        scene = _Scene("Chorus")
        script._song.scenes = [scene]

        result = script._fire_scene(0)

        scene.fire.assert_called_once_with()
        assert result == {"index": 0, "name": "Chorus"}

    def test_set_scene_color(self):
        script = _make_script()
        script._song.scenes = [_Scene("Bridge")]

        result = script._set_scene_color(0, 0xFF0000)

        assert script._song.scenes[0].color == 0xFF0000
        assert result == {"index": 0, "name": "Bridge", "color": 0xFF0000, "tempo": 0.0}

    def test_set_scene_tempo(self):
        script = _make_script()
        script._song.scenes = [_Scene("Outro")]

        result = script._set_scene_tempo(0, 72.5)

        assert script._song.scenes[0].tempo == 72.5
        assert result == {"index": 0, "name": "Outro", "color": 0, "tempo": 72.5}

    def test_stop_all_clips_delegates_to_song(self):
        script = _make_script()

        result = script._stop_all_clips()

        script._song.stop_all_clips.assert_called_once_with()
        assert result == {"stopped": True}
