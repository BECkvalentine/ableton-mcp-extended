"""Unit tests for transport and global song-state MCP tools."""

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
    get_current_song_time,
    redo,
    set_arrangement_record,
    set_current_song_time,
    set_metronome,
    set_nudge_down,
    set_nudge_up,
    set_overdub,
    set_punch_points,
    set_session_record,
    set_time_signature,
    tap_tempo,
    undo,
)


class TestTransportCommands:
    @patch("MCP_Server.server.get_ableton_connection")
    def test_get_current_song_time(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {"current_song_time": 12.5}
        mock_conn.return_value = mock_ableton

        result = get_current_song_time(MagicMock())

        mock_ableton.send_command.assert_called_with("get_current_song_time", {})
        assert "12.500" in result

    @patch("MCP_Server.server.get_ableton_connection")
    def test_set_current_song_time(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {"current_song_time": 16.0}
        mock_conn.return_value = mock_ableton

        set_current_song_time(MagicMock(), time=16.0)

        mock_ableton.send_command.assert_called_with("set_current_song_time", {
            "time": 16.0,
        })

    @patch("MCP_Server.server.get_ableton_connection")
    def test_set_time_signature(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {"numerator": 6, "denominator": 8}
        mock_conn.return_value = mock_ableton

        result = set_time_signature(MagicMock(), numerator=6, denominator=8)

        mock_ableton.send_command.assert_called_with("set_time_signature", {
            "numerator": 6,
            "denominator": 8,
        })
        assert "6/8" in result

    @patch("MCP_Server.server.get_ableton_connection")
    def test_global_toggles(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {}
        mock_conn.return_value = mock_ableton

        set_metronome(MagicMock(), metronome=True)
        set_overdub(MagicMock(), overdub=True)
        set_session_record(MagicMock(), record=False)
        set_arrangement_record(MagicMock(), record=False)
        set_nudge_up(MagicMock(), nudge=True)
        set_nudge_down(MagicMock(), nudge=False)

        calls = mock_ableton.send_command.call_args_list
        assert calls[0][0] == ("set_metronome", {"metronome": True})
        assert calls[1][0] == ("set_overdub", {"overdub": True})
        assert calls[2][0] == ("set_session_record", {"record": False})
        assert calls[3][0] == ("set_arrangement_record", {"record": False})
        assert calls[4][0] == ("set_nudge_up", {"nudge": True})
        assert calls[5][0] == ("set_nudge_down", {"nudge": False})

    @patch("MCP_Server.server.get_ableton_connection")
    def test_tap_undo_redo_and_punch_points(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.side_effect = [
            {"tempo": 120.0},
            {},
            {},
            {"punch_in": True, "punch_out": False},
        ]
        mock_conn.return_value = mock_ableton

        tap_tempo(MagicMock())
        undo(MagicMock())
        redo(MagicMock())
        set_punch_points(MagicMock(), punch_in=True, punch_out=False)

        calls = mock_ableton.send_command.call_args_list
        assert calls[0][0] == ("tap_tempo", {})
        assert calls[1][0] == ("undo", {})
        assert calls[2][0] == ("redo", {})
        assert calls[3][0] == ("set_punch_points", {
            "punch_in": True,
            "punch_out": False,
        })
