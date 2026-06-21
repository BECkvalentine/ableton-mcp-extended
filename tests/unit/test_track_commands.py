"""Unit tests for track-level MCP tools."""
import sys
import os
from unittest.mock import MagicMock, patch

# Mock MCP dependencies before importing server
_mock_mcp_module = MagicMock()
_mock_fastmcp = MagicMock()
_mock_fastmcp.FastMCP.return_value.tool.return_value = lambda fn: fn
sys.modules['mcp'] = _mock_mcp_module
sys.modules['mcp.server'] = MagicMock()
sys.modules['mcp.server.fastmcp'] = _mock_fastmcp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from MCP_Server.server import (
    create_audio_track,
    create_return_track,
    delete_return_track,
    delete_track,
    get_track_deletion_status,
    load_device_on_return,
    set_master_panning,
    set_master_volume,
    set_return_track_color,
    set_return_track_mute,
    set_return_track_name,
    set_return_track_panning,
    set_return_track_volume,
    set_send,
    set_track_arm,
    set_track_color,
    set_track_mute,
    set_track_solo,
)


class TestCreateAudioTrack:
    """Tests for the create_audio_track MCP tool."""

    @patch('MCP_Server.server.get_ableton_connection')
    def test_create_audio_track_at_end(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {
            "index": 3,
            "name": "4-Audio",
        }
        mock_conn.return_value = mock_ableton

        result = create_audio_track(MagicMock())

        assert "Created new audio track: 4-Audio" in result
        mock_ableton.send_command.assert_called_once_with(
            "create_audio_track", {"index": -1})

    @patch('MCP_Server.server.get_ableton_connection')
    def test_create_audio_track_at_index(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {
            "index": 1,
            "name": "2-Audio",
        }
        mock_conn.return_value = mock_ableton

        result = create_audio_track(MagicMock(), index=1)

        assert "Created new audio track: 2-Audio" in result
        mock_ableton.send_command.assert_called_once_with(
            "create_audio_track", {"index": 1})


class TestDeleteTrackSafetyGuard:
    """Prevent deleting the final remaining session track."""

    @patch('MCP_Server.server.get_ableton_connection')
    def test_blocks_delete_by_index_when_only_one_track_remains(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {"track_count": 1}
        mock_conn.return_value = mock_ableton

        result = delete_track(MagicMock(), track_index=1)

        assert "Cannot delete the last remaining session track" in result
        assert "Create a new track before deleting" in result
        mock_ableton.send_command.assert_called_once_with("get_session_info")

    @patch('MCP_Server.server.get_ableton_connection')
    def test_blocks_delete_by_name_when_only_one_track_remains(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {"track_count": 1}
        mock_conn.return_value = mock_ableton

        result = delete_track(MagicMock(), track_index=0, track_name="My Track")

        assert "Cannot delete the last remaining session track" in result
        assert "Create a new track before deleting" in result
        mock_ableton.send_command.assert_called_once_with("get_session_info")


class TestDeleteTrackBehavior:
    """Normal delete behavior when more than one track exists."""

    @patch('MCP_Server.server.get_ableton_connection')
    def test_delete_by_index_still_works_with_multiple_tracks(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.side_effect = [
            {"track_count": 3},  # get_session_info
            {"deleted_track": "Bass", "remaining_tracks": 2},  # delete_track
        ]
        mock_conn.return_value = mock_ableton

        result = delete_track(MagicMock(), track_index=2)

        assert "Deleted track 'Bass'" in result
        calls = mock_ableton.send_command.call_args_list
        assert calls[1][0][0] == "delete_track"
        assert calls[1][0][1]["track_index"] == 1  # 2 -> 1

    @patch('MCP_Server.server.get_ableton_connection')
    def test_delete_by_name_resolves_and_deletes(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.side_effect = [
            {"track_count": 3},  # get_session_info
            {"name": "Drums"},   # get_track_info index 0
            {"name": "Bass"},    # get_track_info index 1
            {"deleted_track": "Bass", "remaining_tracks": 2},  # delete_track
        ]
        mock_conn.return_value = mock_ableton

        result = delete_track(MagicMock(), track_index=0, track_name="Bass")

        assert "Deleted track 'Bass'" in result
        delete_call = mock_ableton.send_command.call_args_list[-1]
        assert delete_call[0][0] == "delete_track"
        assert delete_call[0][1]["track_index"] == 1


class TestTrackDeletionStatus:
    """Tests for get_track_deletion_status precheck tool."""

    @patch('MCP_Server.server.get_ableton_connection')
    def test_reports_blocked_when_one_track_remains(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {"track_count": 1}
        mock_conn.return_value = mock_ableton

        result = get_track_deletion_status(MagicMock())

        assert "Track deletion blocked" in result
        assert "Create a new track before deleting" in result

    @patch('MCP_Server.server.get_ableton_connection')
    def test_reports_max_deletions_when_multiple_tracks_exist(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {"track_count": 4}
        mock_conn.return_value = mock_ableton

        result = get_track_deletion_status(MagicMock())

        assert "Track deletion available" in result
        assert "up to 3 more track(s)" in result


class TestMixerCommandIndexing:
    @patch('MCP_Server.server.get_ableton_connection')
    def test_track_state_commands_use_one_based_indices(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {"track_name": "Bass", "mute": True}
        mock_conn.return_value = mock_ableton

        set_track_mute(MagicMock(), track_index=2, mute=True)

        mock_ableton.send_command.assert_called_with("set_track_mute", {
            "track_index": 1,
            "mute": True,
        })

    @patch('MCP_Server.server.get_ableton_connection')
    def test_track_solo_arm_and_color_use_one_based_indices(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {"track_name": "Keys", "solo": True}
        mock_conn.return_value = mock_ableton

        set_track_solo(MagicMock(), track_index=3, solo=True)
        set_track_arm(MagicMock(), track_index=3, arm=False)
        set_track_color(MagicMock(), track_index=3, color=0x112233)

        calls = mock_ableton.send_command.call_args_list
        assert calls[0][0] == ("set_track_solo", {"track_index": 2, "solo": True})
        assert calls[1][0] == ("set_track_arm", {"track_index": 2, "arm": False})
        assert calls[2][0] == ("set_track_color", {"track_index": 2, "color": 0x112233})

    @patch('MCP_Server.server.get_ableton_connection')
    def test_return_track_commands_use_one_based_indices(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {"track_name": "Verb", "volume": 0.5}
        mock_conn.return_value = mock_ableton

        set_return_track_name(MagicMock(), return_track_index=1, name="Verb")
        set_return_track_volume(MagicMock(), return_track_index=1, volume=0.5)
        set_return_track_panning(MagicMock(), return_track_index=1, panning=-0.25)
        set_return_track_mute(MagicMock(), return_track_index=1, mute=True)
        set_return_track_color(MagicMock(), return_track_index=1, color=0xABCDEF)
        load_device_on_return(MagicMock(), return_track_index=1, uri="query:AudioFx#Verb")

        calls = mock_ableton.send_command.call_args_list
        assert calls[0][0] == ("set_return_track_name", {"return_track_index": 0, "name": "Verb"})
        assert calls[1][0] == ("set_return_track_volume", {"return_track_index": 0, "volume": 0.5})
        assert calls[2][0] == ("set_return_track_panning", {"return_track_index": 0, "panning": -0.25})
        assert calls[3][0] == ("set_return_track_mute", {"return_track_index": 0, "mute": True})
        assert calls[4][0] == ("set_return_track_color", {"return_track_index": 0, "color": 0xABCDEF})
        assert calls[5][0] == ("load_device_on_return", {
            "return_track_index": 0,
            "item_uri": "query:AudioFx#Verb",
        })

    @patch('MCP_Server.server.get_ableton_connection')
    def test_delete_return_track_uses_one_based_index(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {
            "deleted_return_track": "B-Delay",
            "remaining_return_tracks": 1,
        }
        mock_conn.return_value = mock_ableton

        delete_return_track(MagicMock(), return_track_index=2)

        mock_ableton.send_command.assert_called_with("delete_return_track", {
            "return_track_index": 1,
        })

    @patch('MCP_Server.server.get_ableton_connection')
    def test_set_send_uses_one_based_source_and_return_indices(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.return_value = {
            "source_track_name": "Vocal",
            "send_amount": 0.4,
        }
        mock_conn.return_value = mock_ableton

        set_send(MagicMock(), source_track_index=4, return_track_index=2, send_amount=0.4)

        mock_ableton.send_command.assert_called_with("set_send", {
            "source_track_index": 3,
            "return_track_index": 1,
            "send_amount": 0.4,
        })

    @patch('MCP_Server.server.get_ableton_connection')
    def test_master_and_create_return_commands_do_not_translate_indices(self, mock_conn):
        mock_ableton = MagicMock()
        mock_ableton.send_command.side_effect = [
            {"volume": 0.8},
            {"panning": 0.1},
            {"index": 0, "name": "A-Reverb"},
        ]
        mock_conn.return_value = mock_ableton

        set_master_volume(MagicMock(), volume=0.8)
        set_master_panning(MagicMock(), panning=0.1)
        create_return_track(MagicMock())

        calls = mock_ableton.send_command.call_args_list
        assert calls[0][0] == ("set_master_volume", {"volume": 0.8})
        assert calls[1][0] == ("set_master_panning", {"panning": 0.1})
        assert calls[2][0] == ("create_return_track", {})
