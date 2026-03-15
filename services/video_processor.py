"""Video processing service using ffmpeg (subprocess).

Handles:
- Concatenating multiple MP4 clips into one video
- Mixing audio (music/voice) into a video
- Splitting a video at a time offset
- Trimming a video to exact duration
- Extracting a thumbnail frame
- Probing video duration
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger("aizavod.video_processor")

_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"
_OUTPUT_DIR = _MEDIA_DIR / "generated"


def _resolve_path(path: str) -> Path:
    """Resolve /media/... relative path to absolute."""
    if path.startswith("/media/"):
        return _MEDIA_DIR.parent / path.lstrip("/")
    return Path(path)


def _output_path(prefix: str, ext: str = ".mp4") -> Path:
    """Generate a unique output file path."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return _OUTPUT_DIR / f"{prefix}_{uuid.uuid4().hex[:12]}{ext}"


async def _run_ffmpeg(*args: str) -> str:
    """Run ffmpeg command asynchronously, return stdout."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"] + list(args)
    logger.debug("ffmpeg cmd: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr.decode(errors="replace").strip()
        raise RuntimeError(f"ffmpeg failed (code {proc.returncode}): {err_msg}")

    return stdout.decode(errors="replace").strip()


async def _run_ffprobe(*args: str) -> str:
    """Run ffprobe command asynchronously, return stdout."""
    cmd = ["ffprobe"] + list(args)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr.decode(errors="replace").strip()
        raise RuntimeError(f"ffprobe failed (code {proc.returncode}): {err_msg}")

    return stdout.decode(errors="replace").strip()


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

async def concatenate_clips(
    clip_paths: list[str],
    output_filename: str | None = None,
) -> str:
    """Concatenate a list of MP4 clips into a single MP4.

    Uses ffmpeg concat demuxer (lossless, no re-encode if codecs match).

    Args:
        clip_paths: List of /media/generated/xxx.mp4 paths in order.
        output_filename: Optional output name; auto-generated if None.

    Returns:
        Output path string like /media/generated/concat_abc123.mp4
    """
    if not clip_paths:
        raise ValueError("No clips provided for concatenation")

    if len(clip_paths) == 1:
        return clip_paths[0]

    # Write concat manifest to temp file
    manifest_lines = []
    for p in clip_paths:
        abs_p = _resolve_path(p)
        if not abs_p.exists():
            raise FileNotFoundError(f"Clip not found: {abs_p}")
        # Use forward slashes and escape single quotes
        safe_path = str(abs_p).replace("\\", "/").replace("'", "'\\''")
        manifest_lines.append(f"file '{safe_path}'")

    manifest_text = "\n".join(manifest_lines)

    # Create temp manifest file
    fd, manifest_path = tempfile.mkstemp(suffix=".txt", prefix="concat_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(manifest_text)

        if output_filename:
            out = _OUTPUT_DIR / output_filename
        else:
            out = _output_path("concat")

        await _run_ffmpeg(
            "-f", "concat",
            "-safe", "0",
            "-i", str(manifest_path),
            "-c", "copy",
            str(out),
        )
    finally:
        os.unlink(manifest_path)

    rel_path = f"/media/generated/{out.name}"
    logger.info(
        "Concatenated %d clips -> %s (%.1f MB)",
        len(clip_paths), out.name, out.stat().st_size / 1_048_576,
    )
    return rel_path


async def mix_audio(
    video_path: str,
    audio_path: str,
    output_filename: str | None = None,
    audio_volume: float = 0.8,
    video_audio_volume: float = 0.0,
    loop_audio: bool = True,
) -> str:
    """Mix an audio track (music MP3) into a video.

    Args:
        video_path: Source video path.
        audio_path: Audio file path (MP3/WAV).
        audio_volume: Background music volume (0.0-1.0).
        video_audio_volume: Original video audio volume (0.0 = mute).
        loop_audio: If True, loop audio to fill video duration.

    Returns:
        Output video path with mixed audio.
    """
    abs_video = _resolve_path(video_path)
    abs_audio = _resolve_path(audio_path)

    if not abs_video.exists():
        raise FileNotFoundError(f"Video not found: {abs_video}")
    if not abs_audio.exists():
        raise FileNotFoundError(f"Audio not found: {abs_audio}")

    out = _output_path("mixed") if not output_filename else _OUTPUT_DIR / output_filename

    # Build ffmpeg command
    audio_input_args = []
    if loop_audio:
        audio_input_args = ["-stream_loop", "-1"]

    if video_audio_volume > 0:
        # Mix both: original video audio + new audio
        filter_complex = (
            f"[0:a]volume={video_audio_volume}[va];"
            f"[1:a]volume={audio_volume}[aa];"
            f"[va][aa]amix=inputs=2:duration=first[out]"
        )
        await _run_ffmpeg(
            "-i", str(abs_video),
            *audio_input_args,
            "-i", str(abs_audio),
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            "-shortest",
            str(out),
        )
    else:
        # Replace audio entirely with new audio
        await _run_ffmpeg(
            "-i", str(abs_video),
            *audio_input_args,
            "-i", str(abs_audio),
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            f"-af", f"volume={audio_volume}",
            "-shortest",
            str(out),
        )

    rel_path = f"/media/generated/{out.name}"
    logger.info("Mixed audio into video: %s (vol=%.1f)", out.name, audio_volume)
    return rel_path


async def split_video(
    video_path: str,
    split_at_seconds: float,
) -> tuple[str, str]:
    """Split a video into two parts at the given timestamp.

    Args:
        video_path: Input video path.
        split_at_seconds: Where to cut (e.g. 32.5).

    Returns:
        Tuple of (part1_path, part2_path).
    """
    abs_video = _resolve_path(video_path)
    if not abs_video.exists():
        raise FileNotFoundError(f"Video not found: {abs_video}")

    part1 = _output_path("part1")
    part2 = _output_path("part2")

    # Part 1: from start to split_at
    await _run_ffmpeg(
        "-i", str(abs_video),
        "-t", str(split_at_seconds),
        "-c", "copy",
        str(part1),
    )

    # Part 2: from split_at to end
    await _run_ffmpeg(
        "-i", str(abs_video),
        "-ss", str(split_at_seconds),
        "-c", "copy",
        str(part2),
    )

    p1_rel = f"/media/generated/{part1.name}"
    p2_rel = f"/media/generated/{part2.name}"

    p1_dur = await get_video_duration(p1_rel)
    p2_dur = await get_video_duration(p2_rel)
    logger.info(
        "Split video at %.1fs: part1=%.1fs, part2=%.1fs",
        split_at_seconds, p1_dur, p2_dur,
    )

    return p1_rel, p2_rel


async def trim_video(
    video_path: str,
    duration_seconds: float,
    start_seconds: float = 0.0,
    output_filename: str | None = None,
) -> str:
    """Trim video to exact duration.

    Args:
        video_path: Input path.
        duration_seconds: Target duration (e.g. 65.0).
        start_seconds: Start offset (default 0).

    Returns:
        Output path.
    """
    abs_video = _resolve_path(video_path)
    if not abs_video.exists():
        raise FileNotFoundError(f"Video not found: {abs_video}")

    out = _output_path("trimmed") if not output_filename else _OUTPUT_DIR / output_filename

    args = ["-i", str(abs_video)]
    if start_seconds > 0:
        args.extend(["-ss", str(start_seconds)])
    args.extend(["-t", str(duration_seconds), "-c", "copy", str(out)])

    await _run_ffmpeg(*args)

    rel_path = f"/media/generated/{out.name}"
    actual_dur = await get_video_duration(rel_path)
    logger.info("Trimmed video to %.1fs (actual: %.1fs): %s", duration_seconds, actual_dur, out.name)
    return rel_path


async def extract_thumbnail(
    video_path: str,
    at_seconds: float = 0.5,
) -> str:
    """Extract a single frame as JPEG thumbnail.

    Returns:
        Path to JPEG thumbnail file.
    """
    abs_video = _resolve_path(video_path)
    if not abs_video.exists():
        raise FileNotFoundError(f"Video not found: {abs_video}")

    out = _output_path("thumb", ext=".jpg")

    await _run_ffmpeg(
        "-i", str(abs_video),
        "-ss", str(at_seconds),
        "-vframes", "1",
        "-q:v", "2",
        str(out),
    )

    rel_path = f"/media/generated/{out.name}"
    logger.info("Extracted thumbnail at %.1fs: %s", at_seconds, out.name)
    return rel_path


async def get_video_duration(video_path: str) -> float:
    """Probe video duration using ffprobe.

    Returns:
        Duration in seconds.
    """
    abs_video = _resolve_path(video_path)
    if not abs_video.exists():
        raise FileNotFoundError(f"Video not found: {abs_video}")

    output = await _run_ffprobe(
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(abs_video),
    )

    data = json.loads(output)
    duration = float(data.get("format", {}).get("duration", 0))
    return duration
