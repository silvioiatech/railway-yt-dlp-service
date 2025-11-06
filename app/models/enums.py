"""Enumeration types for the application."""

from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QualityPreset(str, Enum):
    """Video quality presets."""
    BEST = "best"
    UHD_4K = "4k"
    FHD_1080P = "1080p"
    HD_720P = "720p"
    SD_480P = "480p"
    LD_360P = "360p"
    AUDIO_ONLY = "audio"


class VideoFormat(str, Enum):
    """Video container formats."""
    MP4 = "mp4"
    MKV = "mkv"
    WEBM = "webm"
    AVI = "avi"
    MOV = "mov"
    FLV = "flv"


class AudioFormat(str, Enum):
    """Audio formats."""
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"
    WAV = "wav"
    OPUS = "opus"
    AAC = "aac"
    VORBIS = "vorbis"


class SubtitleFormat(str, Enum):
    """Subtitle formats."""
    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"
    LRC = "lrc"
