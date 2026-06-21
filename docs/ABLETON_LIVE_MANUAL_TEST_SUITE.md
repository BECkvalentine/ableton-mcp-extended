# Ableton Live Manual Test Suite

This suite captures the local PR 99 integration smoke path for this fork.
It is intentionally different from the upstream `TEST_SUITE.md` examples:

- Public MCP tool indices are 1-based.
- Direct Remote Script socket commands are 0-based.
- Normal unit tests should stay offline; Live checks are manual or marked `integration`.
- Destructive or stateful commands must be run only against a reset/template set.

## Prerequisites

- Ableton Live is open.
- The `AbletonMCP` Control Surface is loaded.
- The Remote Script socket is reachable at `localhost:9877`.
- The repository branch is `feature/upstream-pr-99-live-api-tools`.
- After any edit to `AbletonMCP_Remote_Script/__init__.py`, restart Ableton or reload the Control Surface before smoke testing.

Recommended local verification before Live smoke:

```bash
python3 -m pytest tests/unit
python3 -m compileall -q MCP_Server AbletonMCP_Remote_Script
git diff --check
```

Run optional Live integration tests explicitly:

```bash
pytest -m integration tests/integration
```

The Phase 8 arrangement-to-session fixture needs a source audio file path when Live does not expose `clip.sample.file_path`:

```bash
ABLETON_MCP_AUDIO_FIXTURE_PATH="/path/to/source-audio.wav" \
pytest -m integration tests/integration/test_ableton_live_smoke.py::test_copy_arrangement_audio_clip_to_session_fixture
```

## Baseline Readback

Use `get_session_info` before and after each smoke group.

Expected reset-template baseline for Kevin's current Worship Tracks setup:

- 48 normal tracks
- 1 scene
- 1 return track
- tempo around 63 BPM

If a test creates temporary tracks, scenes, returns, devices, or clips, verify the baseline is restored afterward.

## Phase 3: Mixer, Return, Master, Sends

Smoke on temporary or restorable targets:

- `set_track_mute`
- `set_track_solo`
- `set_track_arm`
- `set_track_color`
- `get_return_tracks`
- `create_return_track`
- `delete_return_track`
- `set_return_track_name`
- `set_return_track_volume`
- `set_return_track_panning`
- `set_return_track_mute`
- `set_return_track_color`
- `set_master_volume`
- `set_master_panning`
- `set_send`
- `load_device_on_return`
- `delete_device` against return-track global indices

Restore master volume/pan, return volume/pan/mute/color, send amount, and delete temporary return tracks/devices.

## Phase 4: Scene Management

Smoke on temporary scenes:

- `get_scenes`
- `create_scene`
- `set_scene_name`
- `set_scene_color`
- `set_scene_tempo`
- `duplicate_scene`
- `fire_scene`
- `stop_all_clips`
- `delete_scene`

Important behavior: firing a scene with a tempo override changes the global song tempo. Restore tempo afterward.

## Phase 5: Transport And Global State

Safe/reversible smoke path:

- `get_current_song_time`
- `set_current_song_time`
- `set_time_signature`
- invalid time signature rejection
- `set_metronome`
- `set_overdub`
- `set_nudge_up`
- `set_nudge_down`
- `set_punch_points`
- `set_session_record(false)`
- `set_arrangement_record(false)`

Manual-confirmation only:

- `tap_tempo`
- `undo`
- `redo`
- turning session or arrangement record on

Restore song position, 4/4 time signature, punch state, metronome, overdub, and record flags.

## Phase 6: Session Clip And MIDI

Use a temporary MIDI track and a temporary second scene when duplicate target slots are needed.

Smoke path:

- create temporary scene
- create temporary MIDI track
- `create_clip`
- `set_clip_name`
- `add_notes_to_clip`
- `get_notes_from_clip`
- `get_clip_info`
- `get_clip_slot_info`
- `set_clip_loop`
- `set_clip_color`
- `duplicate_clip`
- `quantize_clip`
- `apply_note_modifications`
- `remove_notes_from_clip`
- delete temporary MIDI track
- delete temporary scene

Known behavior: Ableton normalizes arbitrary clip colors to its palette. Verify readback as an integer, not exact RGB equality.

## Phase 7: Routing And Audio Clip Controls

Routing smoke should use a temporary track:

- `get_track_routing`
- `get_available_routings`
- `set_input_routing`
- `set_output_routing`

Audio clip smoke needs a Session View audio clip:

- `get_audio_clip_info`
- `set_audio_clip_gain`
- `set_audio_clip_pitch`
- `set_audio_clip_warp`

Restore gain, pitch coarse/fine, warping, and warp mode after testing.

## Phase 8: Arrangement Reconciliation

Read smoke:

- `get_arrangement_loop`
- `get_arrangement_info`

Arrangement-to-session fixture smoke:

- find a safe Arrangement View audio clip
- call `copy_arrangement_audio_clip_to_session`
- provide `source_file_path` if Live returns an empty Arrangement `sample_path`
- read copied clip with `get_audio_clip_info`
- verify copied clip name, start/end markers, loop enabled state, gain, pitch, warp state, and warp mode
- delete the temporary Session track

Known behavior: if the source Arrangement clip is not looping, Ableton may normalize inactive Session loop bounds after clip creation. Treat start/end markers as the crop/section authority in that case.

## Phase 9: Final Hardening

Before merging the integration branch:

- `python3 -m pytest tests/unit`
- `python3 -m compileall -q MCP_Server AbletonMCP_Remote_Script`
- `git diff --check`
- `pytest -m integration tests/integration` when Ableton is running and a safe test set is loaded
- confirm every Remote Script change has been smoke-tested after a Control Surface reload
- confirm the PR 99 integration notes reflect completed phases and known Live-native behaviors
