"""Unit tests for routing and Session View audio clip MCP tools."""

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
    get_audio_clip_info,
    get_available_routings,
    get_track_routing,
    set_audio_clip_gain,
    set_audio_clip_pitch,
    set_audio_clip_warp,
    set_input_routing,
    set_output_routing,
)


class TestRoutingAndAudioCommands:
    @patch("MCP_Server.server.get_ableton_connection")
    def test_routing_commands_use_one_based_indices(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.side_effect = [
            {"input_routing_type": "No Input"},
            {"available_input_routing_types": ["No Input"]},
            {"input_routing_type": "No Input"},
            {"output_routing_type": "Master"},
        ]
        mock_conn.return_value = mock_ableton

        get_track_routing(MagicMock(), track_index=2)
        get_available_routings(MagicMock(), track_index=2)
        set_input_routing(MagicMock(), track_index=2, routing_type_name="No Input")
        set_output_routing(MagicMock(), track_index=2, routing_type_name="Master")

        calls = mock_ableton.send_command.call_args_list
        assert calls[0][0] == ("get_track_routing", {"track_index": 1})
        assert calls[1][0] == ("get_available_routings", {"track_index": 1})
        assert calls[2][0] == (
            "set_input_routing",
            {"track_index": 1, "routing_type_name": "No Input"},
        )
        assert calls[3][0] == (
            "set_output_routing",
            {"track_index": 1, "routing_type_name": "Master"},
        )

    @patch("MCP_Server.server.get_ableton_connection")
    def test_audio_clip_commands_use_one_based_indices(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.side_effect = [
            {"name": "Loop"},
            {"gain": 0.5, "gain_display_string": "-6 dB"},
            {"pitch_coarse": 2, "pitch_fine": 5.0},
            {"warping": True, "warp_mode_name": "Beats"},
        ]
        mock_conn.return_value = mock_ableton

        get_audio_clip_info(MagicMock(), track_index=3, clip_index=4)
        set_audio_clip_gain(MagicMock(), track_index=3, clip_index=4, gain=0.5)
        set_audio_clip_pitch(
            MagicMock(),
            track_index=3,
            clip_index=4,
            pitch_coarse=2,
            pitch_fine=5.0,
        )
        set_audio_clip_warp(
            MagicMock(),
            track_index=3,
            clip_index=4,
            warping=True,
            warp_mode="Beats",
        )

        calls = mock_ableton.send_command.call_args_list
        assert calls[0][0] == (
            "get_audio_clip_info",
            {"track_index": 2, "clip_index": 3},
        )
        assert calls[1][0] == (
            "set_audio_clip_gain",
            {"track_index": 2, "clip_index": 3, "gain": 0.5},
        )
        assert calls[2][0] == (
            "set_audio_clip_pitch",
            {
                "track_index": 2,
                "clip_index": 3,
                "pitch_coarse": 2,
                "pitch_fine": 5.0,
            },
        )
        assert calls[3][0] == (
            "set_audio_clip_warp",
            {
                "track_index": 2,
                "clip_index": 3,
                "warping": True,
                "warp_mode": "Beats",
            },
        )
