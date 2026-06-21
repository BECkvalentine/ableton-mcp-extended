"""Unit tests for Session View clip MCP tools."""

import os
import sys
from unittest.mock import MagicMock, patch


_mock_mcp_module = MagicMock()
_mock_fastmcp = MagicMock()
_mock_fastmcp.FastMCP.return_value.tool.return_value = lambda fn: fn
sys.modules["mcp"] = _mock_mcp_module
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = _mock_fastmcp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from MCP_Server.server import (  # noqa: E402
    apply_note_modifications,
    duplicate_clip,
    get_clip_info,
    get_clip_slot_info,
    get_notes_from_clip,
    quantize_clip,
    remove_notes_from_clip,
    set_clip_color,
    set_clip_loop,
)


class TestClipCommands:
    @patch("MCP_Server.server.get_ableton_connection")
    def test_read_commands_use_one_based_indices(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.side_effect = [
            {"name": "Verse"},
            {"has_clip": True},
            {"clip_name": "Verse", "clip_length": 4.0, "notes": []},
        ]
        mock_conn.return_value = mock_ableton

        get_clip_info(MagicMock(), track_index=2, clip_index=3)
        get_clip_slot_info(MagicMock(), track_index=2, clip_index=3)
        get_notes_from_clip(MagicMock(), track_index=2, clip_index=3)

        calls = mock_ableton.send_command.call_args_list
        assert calls[0][0] == ("get_clip_info", {"track_index": 1, "clip_index": 2})
        assert calls[1][0] == ("get_clip_slot_info", {"track_index": 1, "clip_index": 2})
        assert calls[2][0] == ("get_notes_from_clip", {"track_index": 1, "clip_index": 2})

    @patch("MCP_Server.server.get_ableton_connection")
    def test_mutating_commands_use_one_based_indices(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.side_effect = [
            {"removed": True},
            {"updated": 1},
            {"loop_start": 0.0, "loop_end": 4.0, "looping": True},
            {"color": 0x336699},
            {"clip_name": "Verse"},
            {"quantize_to": 0.25, "amount": 1.0},
        ]
        mock_conn.return_value = mock_ableton

        remove_notes_from_clip(MagicMock(), track_index=2, clip_index=3)
        apply_note_modifications(
            MagicMock(),
            track_index=2,
            clip_index=3,
            notes=[{"pitch": 60, "start_time": 0.0, "new_velocity": 80}],
        )
        set_clip_loop(
            MagicMock(),
            track_index=2,
            clip_index=3,
            loop_start=0.0,
            loop_end=4.0,
        )
        set_clip_color(MagicMock(), track_index=2, clip_index=3, color=0x336699)
        duplicate_clip(
            MagicMock(),
            track_index=2,
            clip_index=3,
            target_clip_index=4,
        )
        quantize_clip(MagicMock(), track_index=2, clip_index=3)

        calls = mock_ableton.send_command.call_args_list
        assert calls[0][0][0] == "remove_notes_from_clip"
        assert calls[0][0][1]["track_index"] == 1
        assert calls[0][0][1]["clip_index"] == 2
        assert calls[1][0][0] == "apply_note_modifications"
        assert calls[1][0][1]["track_index"] == 1
        assert calls[1][0][1]["clip_index"] == 2
        assert calls[2][0][0] == "set_clip_loop"
        assert calls[2][0][1]["track_index"] == 1
        assert calls[2][0][1]["clip_index"] == 2
        assert calls[3][0] == (
            "set_clip_color",
            {"track_index": 1, "clip_index": 2, "color": 0x336699},
        )
        assert calls[4][0] == (
            "duplicate_clip",
            {"track_index": 1, "clip_index": 2, "target_clip_index": 3},
        )
        assert calls[5][0][0] == "quantize_clip"
        assert calls[5][0][1]["track_index"] == 1
        assert calls[5][0][1]["clip_index"] == 2
