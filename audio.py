"""Helpers to manage ambient audio playback."""
from __future__ import annotations

import random
import random
from pathlib import Path
from typing import Dict, Optional, Set

import settings
import audio_settings as audio_cfg

try:
    import pygame
except Exception as exc:  # pragma: no cover - optional dependency
    pygame = None
    _pygame_import_error = exc
else:
    _pygame_import_error = None

_mixer_initialized = False
_mixer_attempted = False
_sound_cache: Dict[str, "pygame.mixer.Sound"] = {}


def _ensure_mixer_initialized(*, allow_when_disabled: bool = False) -> bool:
    """Try to initialize pygame.mixer.

    Parameters
    ----------
    allow_when_disabled:
        When False, the mixer won't initialize if AMBIENT_SOUND_ENABLED is False.
        When True, this bypasses that restriction (used for sound effects that
        should work even though ambient music is off).
    """
    global _mixer_initialized, _mixer_attempted

    if _mixer_initialized:
        return True

    if not allow_when_disabled and not audio_cfg.AMBIENT_SOUND_ENABLED:
        _mixer_attempted = True
        return False

    if _mixer_attempted and not allow_when_disabled:
        return False

    if pygame is None:
        if _pygame_import_error and settings.DEBUG_MODE:
            print(f"[audio] pygame is not available: {_pygame_import_error}")
        _mixer_attempted = True
        return False

    try:
        pygame.mixer.init()
    except Exception as exc:  # pragma: no cover - runtime environment issue
        if settings.DEBUG_MODE:
            print(f"[audio] Unable to initialize mixer: {exc}")
        _mixer_attempted = True
        return False

    _mixer_initialized = True
    _mixer_attempted = True
    return True


def _resolve_audio_path(track: str) -> Optional[Path]:
    """Resolve the configured track path to an existing file.

    Users sometimes copy/paste absolute-looking paths (``/data/...``) even
    though the file lives inside the project. To be forgiving we try the
    literal path first and then fall back to treating it as relative to the
    project root (settings' folder) and the current working directory.
    """
    settings_dir = Path(settings.__file__).resolve().parent
    raw_candidates = [track]
    stripped = track.lstrip("/\\")
    if stripped and stripped not in raw_candidates:
        raw_candidates.append(stripped)

    candidate_paths = []
    for raw in raw_candidates:
        path = Path(raw)
        candidate_paths.append(path)
        if not path.is_absolute():
            candidate_paths.append(settings_dir / path)
            cwd_candidate = Path.cwd() / path
            if cwd_candidate != settings_dir / path:
                candidate_paths.append(cwd_candidate)

    seen = set()
    for candidate in candidate_paths:
        normalized = candidate.resolve() if candidate.exists() else candidate
        key = str(normalized)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate

    return None


_missing_effects: Set[str] = set()


class AmbientSoundController:
    """Simple wrapper around pygame.mixer to loop ambient tracks per floor."""

    def __init__(self) -> None:
        self._initialized = False
        self._current_track: Optional[Path] = None
        self._current_floor: Optional[int] = None
        self._missing_tracks: Set[str] = set()

    def initialize(self, *, allow_when_disabled: bool = False) -> None:
        """Initialize pygame mixer if needed."""
        if self._initialized:
            return

        if not _ensure_mixer_initialized(allow_when_disabled=allow_when_disabled):
            return

        self._initialized = True
        self.set_volume(audio_cfg.AMBIENT_SOUND_VOLUME)

    def set_volume(self, value: float) -> None:
        if not self._initialized or pygame is None:
            return
        clamped = max(0.0, min(1.0, float(value)))
        try:
            pygame.mixer.music.set_volume(clamped)
        except Exception as exc:  # pragma: no cover - runtime issue
            if settings.DEBUG_MODE:
                print(f"[audio] Unable to set volume: {exc}")

    def stop(self) -> None:
        if not self._initialized or pygame is None:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self._current_track = None
        self._current_floor = None

    def play_for_floor(self, floor: int) -> None:
        """Play (or switch to) the ambient track requested for this floor."""
        if not audio_cfg.AMBIENT_SOUND_ENABLED:
            self.stop()
            return

        track = self._track_for_floor(floor)
        if not track:
            self.stop()
            return

        self.initialize()
        if not self._initialized or pygame is None:
            return

        resolved = _resolve_audio_path(track)
        if not resolved:
            if track not in self._missing_tracks and settings.DEBUG_MODE:
                print(f"[audio] Ambient track '{track}' not found.")
                self._missing_tracks.add(track)
            self.stop()
            return

        if self._current_track == resolved:
            if pygame.mixer.music.get_busy():
                return
        try:
            pygame.mixer.music.load(str(resolved))
            self.set_volume(audio_cfg.AMBIENT_SOUND_VOLUME)
            pygame.mixer.music.play(-1)
        except Exception as exc:  # pragma: no cover - runtime environment issue
            if settings.DEBUG_MODE:
                print(f"[audio] Unable to play '{resolved}': {exc}")
            return

        self._current_track = resolved
        self._current_floor = floor

    def _track_for_floor(self, floor: int) -> Optional[str]:
        tracks = getattr(audio_cfg, "AMBIENT_SOUND_TRACKS", {}) or {}
        track = None
        if isinstance(tracks, dict):
            track = tracks.get(floor)
        if not track:
            track = getattr(audio_cfg, "AMBIENT_SOUND_DEFAULT_TRACK", None)
        return track


ambient_sound = AmbientSoundController()


def _pick_random_track(list_attr: str, single_attr: Optional[str] = None, *, max_entries: int = 10) -> Optional[str]:
    raw_list = getattr(audio_cfg, list_attr, None)
    valid: list[str] = []
    if raw_list:
        valid.extend([s for s in raw_list if isinstance(s, str) and s.strip()])
    if single_attr:
        single = getattr(audio_cfg, single_attr, None)
        if single and isinstance(single, str) and single.strip():
            valid.append(single)
    if not valid:
        return None
    return random.choice(valid[:max_entries])


def _play_sound_effect(track: str, *, volume: float) -> None:
    if not _ensure_mixer_initialized(allow_when_disabled=True):
        return

    if pygame is None:
        return

    resolved = _resolve_audio_path(track)
    if not resolved:
        if track not in _missing_effects and settings.DEBUG_MODE:
            print(f"[audio] Effect track '{track}' not found.")
            _missing_effects.add(track)
        return

    cache_key = str(resolved)
    sound = _sound_cache.get(cache_key)
    if sound is None:
        try:
            sound = pygame.mixer.Sound(str(resolved))
        except Exception as exc:  # pragma: no cover
            if settings.DEBUG_MODE and cache_key not in _missing_effects:
                print(f"[audio] Unable to load '{resolved}': {exc}")
            _missing_effects.add(cache_key)
            return
        _sound_cache[cache_key] = sound

    clamped = max(0.0, min(1.0, float(volume)))
    try:
        sound.set_volume(clamped)
        sound.play()
    except Exception as exc:  # pragma: no cover
        if settings.DEBUG_MODE:
            print(f"[audio] Unable to play effect '{resolved}': {exc}")


def play_player_footstep() -> None:
    """Play the configured footstep sound, if any."""
    if (
        not getattr(audio_cfg, "PLAYER_FOOTSTEP_SOUND_ENABLED", False)
    ):
        return

    track = _pick_random_track("PLAYER_FOOTSTEP_SOUNDS", "PLAYER_FOOTSTEP_SOUND")
    if not track:
        return

    volume = getattr(audio_cfg, "PLAYER_FOOTSTEP_VOLUME", 1.0)
    _play_sound_effect(track, volume=volume)


def play_door_open_sound() -> None:
    if not getattr(audio_cfg, "DOOR_OPEN_SOUND_ENABLED", False):
        return
    track = _pick_random_track("DOOR_OPEN_SOUNDS", "DOOR_OPEN_SOUND")
    if not track:
        return
    volume = getattr(audio_cfg, "DOOR_OPEN_VOLUME", 1.0)
    _play_sound_effect(track, volume=volume)


def play_door_close_sound() -> None:
    if not getattr(audio_cfg, "DOOR_CLOSE_SOUND_ENABLED", False):
        return
    track = _pick_random_track("DOOR_CLOSE_SOUNDS", "DOOR_CLOSE_SOUND")
    if not track:
        return
    volume = getattr(audio_cfg, "DOOR_CLOSE_VOLUME", 1.0)
    _play_sound_effect(track, volume=volume)
