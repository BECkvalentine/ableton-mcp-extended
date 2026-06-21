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

import AbletonMCP_Remote_Script as remote_script  # noqa: E402
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
        self.input_routing_type = _Route("No Input")
        self.input_routing_channel = _Route("All Channels")
        self.output_routing_type = _Route("Master")
        self.output_routing_channel = _Route("Track Out")
        self.available_input_routing_types = [
            self.input_routing_type,
            _Route("Ext. In"),
        ]
        self.available_output_routing_types = [
            self.output_routing_type,
            _Route("Sends Only"),
        ]


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


class _Route:
    def __init__(self, display_name):
        self.display_name = display_name


class _ClipSlot:
    def __init__(self, clip=None):
        self.clip = clip
        self.has_clip = clip is not None
        self.has_stop_button = True
        self.is_triggered = False

    def duplicate_clip_to(self, target_slot):
        target_slot.clip = self.clip.clone()
        target_slot.has_clip = True

    def create_audio_clip(self, file_path):
        self.clip = _AudioClip("Audio")
        self.clip.sample.file_path = file_path
        self.has_clip = True


class _Note:
    def __init__(self, pitch=60, start_time=0.0, duration=1.0,
                 velocity=100, mute=False):
        self.pitch = pitch
        self.start_time = start_time
        self.duration = duration
        self.velocity = velocity
        self.mute = mute


class _MidiClip:
    is_audio_clip = False
    is_midi_clip = True
    is_playing = False
    is_recording = False

    def __init__(self, name="Clip", length=4.0, notes=None):
        self.name = name
        self.length = length
        self.color = 0
        self.looping = True
        self.loop_start = 0.0
        self.loop_end = length
        self.start_marker = 0.0
        self.end_marker = length
        self.notes = list(notes or [])
        self.added_notes = None
        self.quantize_calls = []

    def clone(self):
        return _MidiClip(self.name, self.length, list(self.notes))

    def set_notes(self, notes):
        self.added_notes = tuple(notes)

    def get_notes_extended(self, **kwargs):
        return self.notes

    def remove_notes_extended(self, **kwargs):
        self.remove_args = kwargs
        self.notes = []

    def apply_note_modifications(self, notes):
        self.notes = list(notes)

    def quantize(self, quantize_to, amount):
        self.quantize_calls.append((quantize_to, amount))


class _AudioClip:
    is_audio_clip = True
    is_midi_clip = False
    is_playing = False
    is_recording = False

    def __init__(self, name="Audio", length=4.0):
        self.name = name
        self.length = length
        self.color = 0
        self.looping = True
        self.loop_start = 0.0
        self.loop_end = length
        self.start_marker = 0.0
        self.end_marker = length
        self.sample = MagicMock()
        self.sample.file_path = "/tmp/audio.wav"
        self.gain = 1.0
        self.gain_display_string = "0.00 dB"
        self.warping = False
        self.warp_mode = 0
        self.pitch_coarse = 0
        self.pitch_fine = 0.0


def _make_script(tracks=()):
    script = AbletonMCP.__new__(AbletonMCP)
    script.log_message = lambda msg: None
    script._song = MagicMock()
    script._song.tracks = list(tracks)
    script._song.scenes = []
    script._song.return_tracks = []
    script._song.master_track = MagicMock()
    script._song.current_song_time = 0.0
    script._song.signature_numerator = 4
    script._song.signature_denominator = 4
    script._song.metronome = False
    script._song.overdub = False
    script._song.session_record = False
    script._song.record_mode = False
    script._song.nudge_up = False
    script._song.nudge_down = False
    script._song.tempo = 120.0
    script._song.punch_in = False
    script._song.punch_out = False
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


class TestTransportHelpers:
    def test_get_and_set_current_song_time(self):
        script = _make_script()
        script._song.current_song_time = 12.5

        assert script._get_current_song_time() == {"current_song_time": 12.5}
        assert script._set_current_song_time(16.0) == {"current_song_time": 16.0}

    def test_rejects_negative_song_time(self):
        script = _make_script()

        try:
            script._set_current_song_time(-1)
            raised = False
        except ValueError:
            raised = True

        assert raised is True

    def test_set_time_signature(self):
        script = _make_script()

        result = script._set_time_signature(6, 8)

        assert script._song.signature_numerator == 6
        assert script._song.signature_denominator == 8
        assert result == {"numerator": 6, "denominator": 8}

    def test_rejects_invalid_time_signature(self):
        script = _make_script()

        try:
            script._set_time_signature(4, 3)
            raised = False
        except ValueError:
            raised = True

        assert raised is True

    def test_global_toggles(self):
        script = _make_script()

        assert script._set_metronome(True) == {"metronome": True}
        assert script._set_overdub(True) == {"overdub": True}
        assert script._set_session_record(True) == {"session_record": True}
        assert script._set_arrangement_record(True) == {"arrangement_record": True}
        assert script._set_nudge_up(True) == {"nudge_up": True}
        assert script._set_nudge_down(True) == {"nudge_down": True}

    def test_tap_undo_redo_and_punch_points(self):
        script = _make_script()

        assert script._tap_tempo() == {"tempo": 120.0}
        script._song.tap_tempo.assert_called_once_with()
        assert script._undo() == {"undone": True}
        script._song.undo.assert_called_once_with()
        assert script._redo() == {"redone": True}
        script._song.redo.assert_called_once_with()
        assert script._set_punch_points(True, False) == {
            "punch_in": True,
            "punch_out": False,
        }

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


class TestSessionClipHelpers:
    def test_add_notes_uses_live_note_specifications_when_available(self):
        class _Spec:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        live_stub = types.SimpleNamespace(
            Clip=types.SimpleNamespace(MidiNoteSpecification=_Spec))
        original_live = remote_script.Live
        remote_script.Live = live_stub
        try:
            clip = _MidiClip("Verse")
            clip.add_new_notes = MagicMock()
            track = _NormalTrack("Keys")
            track.clip_slots = [_ClipSlot(clip)]
            script = _make_script([track])

            result = script._add_notes_to_clip(0, 0, [
                {"pitch": 64, "start_time": 0.5, "duration": 1.0,
                 "velocity": 90, "mute": False}
            ])

            spec = clip.add_new_notes.call_args[0][0][0]
            assert spec.pitch == 64
            assert spec.start_time == 0.5
            assert result == {"note_count": 1}
        finally:
            remote_script.Live = original_live

    def test_add_notes_falls_back_to_legacy_tuple_payload(self):
        original_live = remote_script.Live
        remote_script.Live = None
        try:
            clip = _MidiClip("Verse")
            track = _NormalTrack("Keys")
            track.clip_slots = [_ClipSlot(clip)]
            script = _make_script([track])

            script._add_notes_to_clip(0, 0, [{"pitch": 60}])

            assert clip.added_notes == ((60, 0.0, 0.25, 100, False),)
        finally:
            remote_script.Live = original_live

    def test_get_clip_and_slot_info(self):
        clip = _MidiClip("Verse", length=8.0)
        track = _NormalTrack("Keys")
        track.clip_slots = [_ClipSlot(clip)]
        script = _make_script([track])

        clip_info = script._get_clip_info(0, 0)
        slot_info = script._get_clip_slot_info(0, 0)

        assert clip_info["name"] == "Verse"
        assert clip_info["length"] == 8.0
        assert slot_info["has_clip"] is True
        assert slot_info["clip"]["name"] == "Verse"

    def test_get_remove_and_modify_notes(self):
        note = _Note(pitch=60, start_time=0.0)
        clip = _MidiClip("Verse", notes=[note])
        track = _NormalTrack("Keys")
        track.clip_slots = [_ClipSlot(clip)]
        script = _make_script([track])

        notes_result = script._get_notes_from_clip(0, 0)
        update_result = script._apply_note_modifications(0, 0, [{
            "pitch": 60,
            "start_time": 0.0,
            "new_pitch": 62,
            "new_velocity": 80,
        }])
        remove_result = script._remove_notes_from_clip(0, 0, 0, 128, 0.0, 4.0)

        assert notes_result["notes"][0]["pitch"] == 60
        assert update_result == {"updated": 1}
        assert note.pitch == 62
        assert note.velocity == 80
        assert remove_result == {"removed": True, "track_index": 0, "clip_index": 0}
        assert clip.notes == []

    def test_clip_loop_color_duplicate_and_quantize(self):
        clip = _MidiClip("Verse")
        track = _NormalTrack("Keys")
        target_slot = _ClipSlot()
        track.clip_slots = [_ClipSlot(clip), target_slot]
        script = _make_script([track])

        loop_result = script._set_clip_loop(0, 0, 1.0, 3.0, True)
        color_result = script._set_clip_color(0, 0, 0x336699)
        duplicate_result = script._duplicate_clip(0, 0, 1)
        quantize_result = script._quantize_clip(0, 0, 0.25, 0.75)

        assert loop_result == {"loop_start": 1.0, "loop_end": 3.0, "looping": True}
        assert color_result == {"color": 0x336699}
        assert target_slot.has_clip is True
        assert duplicate_result == {
            "source_clip_index": 0,
            "target_clip_index": 1,
            "clip_name": "Verse",
        }
        assert clip.quantize_calls == [(5, 0.75)]
        assert quantize_result == {
            "track_index": 0,
            "clip_index": 0,
            "quantize_to": 0.25,
            "amount": 0.75,
        }


class TestRoutingAndAudioClipHelpers:
    def test_track_routing_read_and_write(self):
        track = _NormalTrack("Keys")
        script = _make_script([track])

        routing = script._get_track_routing(0)
        available = script._get_available_routings(0)
        input_result = script._set_input_routing(0, "Ext. In")
        output_result = script._set_output_routing(0, "Sends Only")

        assert routing["input_routing_type"] == "No Input"
        assert available["available_input_routing_types"] == ["No Input", "Ext. In"]
        assert input_result == {"track_index": 0, "input_routing_type": "Ext. In"}
        assert output_result == {"track_index": 0, "output_routing_type": "Sends Only"}
        assert track.input_routing_type.display_name == "Ext. In"
        assert track.output_routing_type.display_name == "Sends Only"

    def test_audio_clip_info_and_setters(self):
        clip = _AudioClip("Loop")
        track = _NormalTrack("Audio", has_midi_input=False, has_audio_input=True)
        track.clip_slots = [_ClipSlot(clip)]
        script = _make_script([track])

        info = script._get_audio_clip_info(0, 0)
        gain = script._set_audio_clip_gain(0, 0, 0.5)
        pitch = script._set_audio_clip_pitch(0, 0, 2, 5.0)
        warp = script._set_audio_clip_warp(0, 0, True, "Beats")

        assert info["name"] == "Loop"
        assert info["sample_name"] == "/tmp/audio.wav"
        assert info["start_marker"] == 0.0
        assert info["end_marker"] == 4.0
        assert info["looping"] is True
        assert info["loop_start"] == 0.0
        assert info["loop_end"] == 4.0
        assert gain["gain"] == 0.5
        assert pitch["pitch_coarse"] == 2
        assert pitch["pitch_fine"] == 5.0
        assert warp["warping"] is True
        assert warp["warp_mode"] == 0
        assert warp["warp_mode_name"] == "Beats"

    def test_audio_clip_setters_validate_ranges(self):
        clip = _AudioClip("Loop")
        track = _NormalTrack("Audio", has_midi_input=False, has_audio_input=True)
        track.clip_slots = [_ClipSlot(clip)]
        script = _make_script([track])

        try:
            script._set_audio_clip_gain(0, 0, 1.5)
            gain_raised = False
        except ValueError:
            gain_raised = True

        try:
            script._set_audio_clip_pitch(0, 0, 99, None)
            pitch_raised = False
        except ValueError:
            pitch_raised = True

        try:
            script._set_audio_clip_warp(0, 0, True, "Unknown")
            warp_raised = False
        except ValueError:
            warp_raised = True

        assert gain_raised is True
        assert pitch_raised is True
        assert warp_raised is True


class TestArrangementReconciliationHelpers:
    def test_get_arrangement_loop(self):
        script = _make_script()
        script._song.loop = True
        script._song.loop_start = 8.0
        script._song.loop_length = 16.0
        script._song.punch_in = True
        script._song.punch_out = False

        result = script._get_arrangement_loop()

        assert result == {
            "enabled": True,
            "start": 8.0,
            "length": 16.0,
            "punch_in": True,
            "punch_out": False,
        }

    def test_arrangement_clip_info_includes_audio_metadata(self):
        clip = _AudioClip("CLICK")
        clip.start_time = 8.0
        clip.end_time = 16.0
        clip.muted = False
        clip.start_marker = 1.0
        clip.end_marker = 5.0
        clip.gain = 0.4
        clip.warping = True
        clip.warp_mode = 0
        script = _make_script()

        result = script._get_arrangement_clip_info(clip)

        assert result["sample_path"] == "/tmp/audio.wav"
        assert result["sample_name"] == ""
        assert result["start_marker"] == 1.0
        assert result["end_marker"] == 5.0
        assert result["gain"] == 0.4
        assert result["warp_mode_name"] == "Beats"

    def test_copy_arrangement_audio_clip_to_new_session_track(self):
        source_clip = _AudioClip("CLICK")
        source_clip.start_time = 8.0
        source_clip.end_time = 16.0
        source_clip.muted = False
        source_clip.color = 0x112233
        source_clip.start_marker = 1.0
        source_clip.end_marker = 5.0
        source_clip.looping = True
        source_clip.loop_start = 1.0
        source_clip.loop_end = 5.0
        source_clip.gain = 0.4
        source_clip.pitch_coarse = 2
        source_clip.pitch_fine = 5.0
        source_clip.warping = True
        source_clip.warp_mode = 0

        source_track = _NormalTrack(
            "CLICK",
            has_midi_input=False,
            has_audio_input=True,
            arrangement_clips=[source_clip],
        )
        script = _make_script([source_track])
        script._song.scenes = [_Scene("")]

        def create_audio_track(index):
            track = _NormalTrack(
                "Audio",
                has_midi_input=False,
                has_audio_input=True,
            )
            track.clip_slots = [_ClipSlot()]
            script._song.tracks.append(track)

        script._song.create_audio_track.side_effect = create_audio_track

        result = script._copy_arrangement_audio_clip_to_session(
            source_track_index=0,
            arrangement_clip_index=0,
            target_track_index=-1,
            target_clip_index=0,
            create_missing_scenes=True,
            target_track_name="Fixture",
        )

        target_track = script._song.tracks[1]
        target_clip = target_track.clip_slots[0].clip
        assert result["created_track"] is True
        assert result["target_track_name"] == "Fixture"
        assert result["sample_path_source"] == "live"
        assert target_clip.name == "CLICK"
        assert target_clip.sample.file_path == "/tmp/audio.wav"
        assert target_clip.start_marker == 1.0
        assert target_clip.end_marker == 5.0
        assert target_clip.gain == 0.4
        assert target_clip.pitch_coarse == 2
        assert target_clip.warping is True

    def test_copy_arrangement_audio_clip_uses_source_file_path_fallback(self):
        source_clip = _AudioClip("CLICK")
        source_clip.sample.file_path = ""
        source_clip.start_marker = 2.0
        source_clip.end_marker = 6.0
        source_track = _NormalTrack(
            "CLICK",
            has_midi_input=False,
            has_audio_input=True,
            arrangement_clips=[source_clip],
        )
        script = _make_script([source_track])
        script._song.scenes = [_Scene("")]

        def create_audio_track(index):
            track = _NormalTrack(
                "Audio",
                has_midi_input=False,
                has_audio_input=True,
            )
            track.clip_slots = [_ClipSlot()]
            script._song.tracks.append(track)

        script._song.create_audio_track.side_effect = create_audio_track

        result = script._copy_arrangement_audio_clip_to_session(
            source_track_index=0,
            arrangement_clip_index=0,
            target_track_index=-1,
            target_clip_index=0,
            create_missing_scenes=True,
            target_track_name="Fixture",
            source_file_path="/tmp/provided-click.wav",
        )

        target_clip = script._song.tracks[1].clip_slots[0].clip
        assert result["sample_path"] == "/tmp/provided-click.wav"
        assert result["sample_path_source"] == "provided"
        assert target_clip.sample.file_path == "/tmp/provided-click.wav"
        assert target_clip.start_marker == 2.0
        assert target_clip.end_marker == 6.0
