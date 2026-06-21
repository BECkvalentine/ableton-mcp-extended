"""Unit tests for Ableton command metadata."""

import os
import sys
from unittest.mock import MagicMock

# Mock mcp dependencies before importing server module
_mock_mcp_module = MagicMock()
_mock_fastmcp = MagicMock()
_mock_fastmcp.FastMCP.return_value.tool.return_value = lambda fn: fn
sys.modules["mcp"] = _mock_mcp_module
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = _mock_fastmcp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from MCP_Server.server import MUTATING_COMMANDS, is_mutating_command


def test_known_read_commands_are_not_mutating():
    assert not is_mutating_command("get_session_info")
    assert not is_mutating_command("get_track_info")
    assert not is_mutating_command("get_arrangement_info")
    assert not is_mutating_command("get_device_parameters")


def test_existing_local_mutating_commands_are_registered():
    expected_commands = {
        "create_midi_track",
        "create_return_track",
        "set_track_name",
        "set_track_mute",
        "set_track_solo",
        "set_track_arm",
        "set_track_color",
        "create_clip",
        "add_notes_to_clip",
        "set_clip_name",
        "remove_notes_from_clip",
        "apply_note_modifications",
        "set_clip_loop",
        "set_clip_color",
        "duplicate_clip",
        "quantize_clip",
        "set_input_routing",
        "set_output_routing",
        "set_audio_clip_gain",
        "set_audio_clip_pitch",
        "set_audio_clip_warp",
        "create_scene",
        "delete_scene",
        "duplicate_scene",
        "delete_return_track",
        "fire_scene",
        "set_scene_name",
        "set_scene_color",
        "set_scene_tempo",
        "stop_all_clips",
        "set_tempo",
        "set_current_song_time",
        "set_time_signature",
        "set_metronome",
        "set_overdub",
        "set_session_record",
        "set_arrangement_record",
        "set_nudge_up",
        "set_nudge_down",
        "tap_tempo",
        "undo",
        "redo",
        "set_punch_points",
        "set_return_track_name",
        "set_return_track_volume",
        "set_return_track_panning",
        "set_return_track_mute",
        "set_return_track_color",
        "set_master_volume",
        "set_master_panning",
        "set_send",
        "load_device_on_return",
        "load_browser_item",
        "fire_clip",
        "stop_clip",
        "start_playback",
        "stop_playback",
        "set_song_time",
        "set_arrangement_loop",
        "jump_to_cue",
        "create_cue_point",
        "delete_cue_point",
        "create_arrangement_clip",
        "create_arrangement_audio_clip",
        "copy_arrangement_audio_clip_to_session",
        "duplicate_to_arrangement",
        "delete_arrangement_clip",
        "set_arrangement_clip_property",
        "set_view",
        "control_arrangement_view",
        "manage_clip_automation",
        "set_device_parameter",
        "set_device_enabled",
        "delete_device",
        "delete_track",
        "navigate_preset",
        "set_track_volume",
        "set_track_panning",
    }

    assert expected_commands <= MUTATING_COMMANDS
    assert all(is_mutating_command(command) for command in expected_commands)
