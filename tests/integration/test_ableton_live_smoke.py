"""Optional Ableton Live smoke tests for the Ableton MCP Remote Script.

These tests talk directly to the Ableton Remote Script socket. They are marked
``integration`` and excluded by the default pytest configuration.
"""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

import pytest


HOST = os.environ.get("ABLETON_MCP_HOST", "localhost")
PORT = int(os.environ.get("ABLETON_MCP_PORT", "9877"))


def send_command(command_type: str, params: dict | None = None, timeout: float = 30.0):
    command = {"type": command_type, "params": params or {}}
    response = None
    with socket.create_connection((HOST, PORT), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(json.dumps(command).encode("utf-8"))
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            try:
                response = json.loads(b"".join(chunks).decode("utf-8"))
                break
            except json.JSONDecodeError:
                continue

    if response is None:
        raise RuntimeError(f"No response for {command_type}")
    if response.get("status") == "error":
        raise RuntimeError(response.get("message", "Unknown Ableton error"))
    return response.get("result", {})


def approx_equal(left, right, epsilon=0.001):
    return abs((left or 0.0) - (right or 0.0)) < epsilon


def find_arrangement_audio_clip():
    arrangement = send_command("get_arrangement_info", {"track_index": -1}, timeout=60)
    for track in arrangement.get("tracks", []):
        if not track.get("is_audio"):
            continue
        for clip in track.get("arrangement_clips", []):
            if clip.get("is_audio"):
                return track, clip
    pytest.skip("No Arrangement View audio clip is available in the current set")


@pytest.mark.integration
def test_live_read_smoke():
    session = send_command("get_session_info")
    arrangement_loop = send_command("get_arrangement_loop")
    scenes = send_command("get_scenes")

    assert session["track_count"] >= 1
    assert "tempo" in session
    assert set(arrangement_loop) >= {"enabled", "start", "length", "punch_in", "punch_out"}
    assert "scenes" in scenes


@pytest.mark.integration
def test_copy_arrangement_audio_clip_to_session_fixture():
    source_file_path = os.environ.get("ABLETON_MCP_AUDIO_FIXTURE_PATH", "")
    if source_file_path and not Path(source_file_path).exists():
        pytest.fail(f"ABLETON_MCP_AUDIO_FIXTURE_PATH does not exist: {source_file_path}")

    track, clip = find_arrangement_audio_clip()
    source_path = clip.get("sample_path") or source_file_path
    if not source_path:
        pytest.skip(
            "Arrangement clip sample_path is empty; set ABLETON_MCP_AUDIO_FIXTURE_PATH"
        )

    baseline = send_command("get_session_info")
    created_track_index = None
    try:
        copied = send_command(
            "copy_arrangement_audio_clip_to_session",
            {
                "source_track_index": track["index"],
                "arrangement_clip_index": clip["index"],
                "target_track_index": -1,
                "target_clip_index": 0,
                "create_missing_scenes": True,
                "target_track_name": "Phase 8 Audio Fixture",
                "source_file_path": source_path,
            },
            timeout=60,
        )
        created_track_index = copied["target_track_index"]
        readback = send_command(
            "get_audio_clip_info",
            {
                "track_index": copied["target_track_index"],
                "clip_index": copied["target_clip_index"],
            },
        )

        assert readback["name"] == copied["name"]
        assert approx_equal(readback.get("start_marker"), clip.get("start_marker"))
        assert approx_equal(readback.get("end_marker"), clip.get("end_marker"))
        assert readback.get("looping") == clip.get("looping")
        if clip.get("looping"):
            assert approx_equal(readback.get("loop_start"), clip.get("loop_start"))
            assert approx_equal(readback.get("loop_end"), clip.get("loop_end"))
        assert approx_equal(readback.get("gain"), clip.get("gain"))
        assert readback.get("pitch_coarse") == clip.get("pitch_coarse")
        assert approx_equal(readback.get("pitch_fine"), clip.get("pitch_fine"))
        assert readback.get("warping") == clip.get("warping")
        assert readback.get("warp_mode") == clip.get("warp_mode")
    finally:
        if created_track_index is not None:
            send_command("delete_track", {"track_index": created_track_index}, timeout=30)
            time.sleep(0.2)

    final = send_command("get_session_info")
    assert final["track_count"] == baseline["track_count"]
