"""Helpers to manage ambient audio playback."""
from __future__ import annotations

import random
import random
import time
from pathlib import Path
from typing import Dict, Optional, Set, TYPE_CHECKING

import settings
import audio_settings as audio_cfg

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from entity import Item, Actor

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

    mixer_kwargs = {
        "frequency": int(getattr(audio_cfg, "MIXER_FREQUENCY", 44100)),
        "size": int(getattr(audio_cfg, "MIXER_SIZE", -16)),
        "channels": int(getattr(audio_cfg, "MIXER_CHANNELS", 2)),
        "buffer": int(getattr(audio_cfg, "MIXER_BUFFER", 2048)),
    }

    try:
        pygame.mixer.pre_init(**mixer_kwargs)
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
_campfire_loop_channel: Optional["pygame.mixer.Channel"] = None
_campfire_active_sources: Set[int] = set()
_current_campfire_track: Optional[str] = None
_campfire_preloaded = False

_PICKUP_SOUND_CONFIG = {
    "potion": {
        "list_attr": "POTION_PICKUP_SOUNDS",
        "single_attr": "POTION_PICKUP_SOUND",
        "volume_attr": "POTION_PICKUP_VOLUME",
    },
    "scroll": {
        "list_attr": "SCROLL_PICKUP_SOUNDS",
        "single_attr": "SCROLL_PICKUP_SOUND",
        "volume_attr": "SCROLL_PICKUP_VOLUME",
    },
    "generic": {
        "list_attr": "GENERIC_PICKUP_SOUNDS",
        "single_attr": "GENERIC_PICKUP_SOUND",
        "volume_attr": "GENERIC_PICKUP_VOLUME",
    },
}

_MELEE_CATEGORY_KEYWORDS = {
    "dagger": ("dagger",),
    "short_sword": ("short sword", "shortsword"),
    "long_sword": ("long sword", "longsword"),
    "spear": ("spear",),
    "natural": ("claw", "fang", "bite", "fist", "talon"),
}


def _resolve_volume(value: Optional[float], default_value: float) -> float:
    if value is not None:
        return max(0.0, min(1.0, float(value)))
    return max(0.0, min(1.0, float(default_value)))


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

    def stop(self, *, fade_out_ms: Optional[int] = None) -> None:
        fade_ms = max(0, int(fade_out_ms or 0))
        if self._initialized and pygame is not None:
            try:
                if fade_ms > 0 and pygame.mixer.music.get_busy():
                    pygame.mixer.music.fadeout(fade_ms)
                    self._wait_for_music_stop(timeout_ms=fade_ms)
                else:
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

        fade_out_ms = max(0, int(getattr(audio_cfg, "AMBIENT_SOUND_FADE_OUT_MS", 0)))
        fade_in_ms = max(0, int(getattr(audio_cfg, "AMBIENT_SOUND_FADE_IN_MS", 0)))
        volume = _resolve_volume(
            getattr(audio_cfg, "AMBIENT_SOUND_VOLUME", None),
            1.0,
        )
        if self._switch_to_track(
            track,
            fade_out_ms=fade_out_ms,
            fade_in_ms=fade_in_ms,
            volume=volume,
        ):
            self._current_floor = floor

    def _wait_for_music_stop(self, *, timeout_ms: int, poll_interval: float = 0.05) -> None:
        """Wait briefly for the current music to finish fading out."""
        if pygame is None:
            return
        end_time = time.monotonic() + max(0.0, timeout_ms) / 1000.0
        while pygame.mixer.music.get_busy() and time.monotonic() < end_time:
            time.sleep(max(0.0, poll_interval))

    def _track_for_floor(self, floor: int) -> Optional[str]:
        tracks = getattr(audio_cfg, "AMBIENT_SOUND_TRACKS", {}) or {}
        track_choice: Optional[str] = None
        if isinstance(tracks, dict):
            track_choice = tracks.get(floor)
        if track_choice is None:
            track_choice = getattr(audio_cfg, "AMBIENT_SOUND_DEFAULT_TRACK", None)
        return self._resolve_track_choice(track_choice)

    def _resolve_track_choice(self, entry: Optional[object]) -> Optional[str]:
        if entry is None:
            return None
        if isinstance(entry, (list, tuple, set)):
            candidates = [str(value).strip() for value in entry if isinstance(value, str) and value.strip()]
            if not candidates:
                return None
            return random.choice(candidates)
        if isinstance(entry, str) and entry.strip():
            return entry
        return None

    def _switch_to_track(
        self,
        track: str,
        *,
        fade_out_ms: int,
        fade_in_ms: int,
        volume: float,
        allow_when_disabled: bool = False,
    ) -> bool:
        self.initialize(allow_when_disabled=allow_when_disabled)
        if not self._initialized or pygame is None:
            return False

        resolved = _resolve_audio_path(track)
        if not resolved:
            if track not in self._missing_tracks and settings.DEBUG_MODE:
                print(f"[audio] Ambient track '{track}' not found.")
                self._missing_tracks.add(track)
            self.stop()
            return False

        if self._current_track == resolved and pygame.mixer.music.get_busy():
            self.set_volume(volume)
            self._current_track = resolved
            return True

        if self._current_track and self._current_track != resolved and pygame.mixer.music.get_busy():
            try:
                if fade_out_ms > 0:
                    pygame.mixer.music.fadeout(fade_out_ms)
                    self._wait_for_music_stop(timeout_ms=fade_out_ms)
                else:
                    pygame.mixer.music.stop()
            except Exception:
                pass
        try:
            pygame.mixer.music.load(str(resolved))
            self.set_volume(volume)
            if fade_in_ms > 0:
                pygame.mixer.music.play(-1, fade_ms=fade_in_ms)
            else:
                pygame.mixer.music.play(-1)
        except Exception as exc:  # pragma: no cover - runtime environment issue
            if settings.DEBUG_MODE:
                print(f"[audio] Unable to play '{resolved}': {exc}")
            return False

        self._current_track = resolved
        return True

    def play_menu_track(self) -> None:
        if not getattr(audio_cfg, "MENU_AMBIENT_SOUND_ENABLED", False):
            self.stop()
            return
        track_choice = getattr(audio_cfg, "MENU_AMBIENT_SOUND_TRACKS", None)
        if track_choice is None:
            track_choice = getattr(audio_cfg, "MENU_AMBIENT_SOUND_TRACK", None)
        track = self._resolve_track_choice(track_choice)
        if not track:
            self.stop()
            return
        fade_out_ms = max(
            0,
            int(
                getattr(
                    audio_cfg,
                    "MENU_AMBIENT_SOUND_FADE_OUT_MS",
                    getattr(audio_cfg, "AMBIENT_SOUND_FADE_OUT_MS", 0),
                )
            ),
        )
        fade_in_ms = max(
            0,
            int(
                getattr(
                    audio_cfg,
                    "MENU_AMBIENT_SOUND_FADE_IN_MS",
                    getattr(audio_cfg, "AMBIENT_SOUND_FADE_IN_MS", 0),
                )
            ),
        )
        volume = _resolve_volume(
            getattr(audio_cfg, "MENU_AMBIENT_SOUND_VOLUME", None),
            getattr(audio_cfg, "AMBIENT_SOUND_VOLUME", 1.0),
        )
        if self._switch_to_track(
            track,
            fade_out_ms=fade_out_ms,
            fade_in_ms=fade_in_ms,
            volume=volume,
            allow_when_disabled=True,
        ):
            self._current_floor = None

    def stop_menu_track(self) -> None:
        fade_out_ms = max(
            0,
            int(
                getattr(
                    audio_cfg,
                    "MENU_AMBIENT_SOUND_FADE_OUT_MS",
                    getattr(audio_cfg, "AMBIENT_SOUND_FADE_OUT_MS", 0),
                )
            ),
        )
        self.stop(fade_out_ms=fade_out_ms)


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


def _load_sound(track: str) -> Optional["pygame.mixer.Sound"]:
    resolved = _resolve_audio_path(track)
    if not resolved:
        if track not in _missing_effects and settings.DEBUG_MODE:
            print(f"[audio] Effect track '{track}' not found.")
            _missing_effects.add(track)
        return None

    cache_key = str(resolved)
    sound = _sound_cache.get(cache_key)
    if sound is None:
        try:
            sound = pygame.mixer.Sound(str(resolved))
        except Exception as exc:  # pragma: no cover
            if settings.DEBUG_MODE and cache_key not in _missing_effects:
                print(f"[audio] Unable to load '{resolved}': {exc}")
            _missing_effects.add(cache_key)
            return None
        _sound_cache[cache_key] = sound
    return sound


def _play_sound_effect(track: str, *, volume: float) -> None:
    if not _ensure_mixer_initialized(allow_when_disabled=True):
        return

    if pygame is None:
        return

    sound = _load_sound(track)
    if sound is None:
        return

    clamped = max(0.0, min(1.0, float(volume)))
    try:
        sound.set_volume(clamped)
        sound.play()
    except Exception as exc:  # pragma: no cover
        if settings.DEBUG_MODE:
            print(f"[audio] Unable to play effect '{track}': {exc}")


def preload_campfire_audio() -> None:
    """Warm up the campfire audio so the first playback has no hitch."""
    global _campfire_preloaded
    if _campfire_preloaded:
        return
    if not getattr(audio_cfg, "CAMPFIRE_SOUND_ENABLED", False):
        return
    if not _ensure_mixer_initialized(allow_when_disabled=True) or pygame is None:
        return

    tracks = getattr(audio_cfg, "CAMPFIRE_SOUNDS", []) or []
    single = getattr(audio_cfg, "CAMPFIRE_SOUND", None)
    candidates = list(tracks)
    if single:
        candidates.append(single)
    for track in candidates:
        if not isinstance(track, str):
            continue
        _load_sound(track)
    _campfire_preloaded = True


def _categorize_pickup_item(item: Optional["Item"]) -> str:
    """Return the pickup sound category (potion/scroll/generic) for the item."""
    text_bits = []
    if item is None:
        return "generic"
    for attr in ("id_name", "name"):
        value = getattr(item, attr, None)
        if isinstance(value, str):
            text_bits.append(value.lower())
    char = getattr(item, "char", None)
    descriptor = " ".join(text_bits)
    if char == "!" or "potion" in descriptor:
        return "potion"
    if char == "~" or "scroll" in descriptor:
        return "scroll"
    return "generic"


def _resolve_pickup_volume(category: str) -> float:
    config = _PICKUP_SOUND_CONFIG.get(category, _PICKUP_SOUND_CONFIG["generic"])
    volume_attr = config.get("volume_attr")
    if volume_attr:
        volume = getattr(audio_cfg, volume_attr, None)
        if volume is not None:
            return float(volume)
    return float(getattr(audio_cfg, "ITEM_PICKUP_VOLUME", 1.0))


def play_item_pickup_sound(item: Optional["Item"]) -> None:
    """Play the appropriate pickup sound for the provided item."""
    if not getattr(audio_cfg, "ITEM_PICKUP_SOUND_ENABLED", False):
        return

    category = _categorize_pickup_item(item)
    config = _PICKUP_SOUND_CONFIG.get(category, _PICKUP_SOUND_CONFIG["generic"])
    track = _pick_random_track(config["list_attr"], config["single_attr"])
    if not track:
        return

    volume = _resolve_pickup_volume(category)
    _play_sound_effect(track, volume=volume)


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


def _extract_melee_event_track(event_config: Optional[dict]) -> tuple[Optional[str], Optional[float]]:
    if not event_config:
        return None, None
    tracks: list[str] = []
    raw_tracks = event_config.get("tracks")
    if raw_tracks:
        tracks.extend([t for t in raw_tracks if isinstance(t, str) and t.strip()])
    single = event_config.get("track")
    if isinstance(single, str) and single.strip():
        tracks.append(single)
    if not tracks:
        return None, None
    return random.choice(tracks), event_config.get("volume")


def _resolve_melee_volume(value: Optional[float]) -> float:
    default_value = float(getattr(audio_cfg, "MELEE_ATTACK_DEFAULT_VOLUME", 1.0))
    return _resolve_volume(value, default_value)


def _categorize_melee_weapon(attacker: Optional["Actor"]) -> str:
    if attacker is None:
        return "generic"
    fighter = getattr(attacker, "fighter", None)
    if not fighter:
        return "generic"

    weapon = getattr(fighter, "main_hand_weapon", None)
    descriptors: list[str] = []
    if weapon:
        for attr in ("name", "id_name"):
            value = getattr(weapon, attr, None)
            if isinstance(value, str):
                descriptors.append(value)
        equippable = getattr(weapon, "equippable", None)
        if equippable:
            descriptors.append(equippable.__class__.__name__)
        normalized = " ".join(s.lower() for s in descriptors)
        for category, keywords in _MELEE_CATEGORY_KEYWORDS.items():
            if category == "natural":
                continue
            if any(keyword in normalized for keyword in keywords):
                return category
        return "generic"

    natural_name = fighter.natural_weapon_name
    normalized = natural_name.lower() if isinstance(natural_name, str) else ""
    if normalized:
        if any(keyword in normalized for keyword in _MELEE_CATEGORY_KEYWORDS.get("natural", ())):
            return "natural"
        return "natural"

    return "generic"


def _select_melee_sound(attacker: Optional["Actor"], result: str) -> tuple[Optional[str], Optional[float]]:
    config = getattr(audio_cfg, "MELEE_ATTACK_SOUNDS", {}) or {}
    category = _categorize_melee_weapon(attacker)
    search_order = [category]
    if category != "generic":
        search_order.append("generic")
    for key in search_order:
        event_cfg = (config.get(key) or {}).get(result)
        track, volume = _extract_melee_event_track(event_cfg)
        if track:
            return track, volume
    return None, None


def _select_dummy_sound(result: str) -> tuple[Optional[str], Optional[float]]:
    config = getattr(audio_cfg, "MELEE_DUMMY_SOUNDS", {}) or {}
    event_cfg = config.get(result)
    return _extract_melee_event_track(event_cfg)


def play_melee_attack_sound(attacker: Optional["Actor"], result: str, *, target_is_dummy: bool = False) -> None:
    if not getattr(audio_cfg, "MELEE_ATTACK_SOUND_ENABLED", False):
        return
    if result not in {"hit_damage", "hit_no_damage", "miss"}:
        return
    track: Optional[str]
    volume: Optional[float]
    if target_is_dummy:
        track, volume = _select_dummy_sound(result)
        if track is None:
            track, volume = _select_melee_sound(attacker, result)
    else:
        track, volume = _select_melee_sound(attacker, result)
    if not track:
        return
    resolved_volume = _resolve_melee_volume(volume)
    _play_sound_effect(track, volume=resolved_volume)


def _select_pain_sound(entity: Optional["Actor"]) -> tuple[Optional[str], Optional[float]]:
    config = getattr(audio_cfg, "PAIN_SOUNDS", {}) or {}
    name = getattr(entity, "name", None)
    entry = None
    if isinstance(name, str):
        entry = config.get(name.lower())
    if not entry:
        entry = config.get("default")
    return _extract_melee_event_track(entry)


def play_pain_sound(entity: Optional["Actor"]) -> None:
    if not getattr(audio_cfg, "PAIN_SOUND_ENABLED", False):
        return
    track, volume = _select_pain_sound(entity)
    if not track:
        return
    default_value = float(getattr(audio_cfg, "PAIN_SOUND_DEFAULT_VOLUME", 1.0))
    resolved_volume = _resolve_volume(volume, default_value)
    _play_sound_effect(track, volume=resolved_volume)


def _select_death_sound(entity: Optional["Actor"]) -> tuple[Optional[str], Optional[float]]:
    config = getattr(audio_cfg, "DEATH_SOUNDS", {}) or {}
    name = getattr(entity, "name", None)
    entry = None
    if isinstance(name, str):
        entry = config.get(name.lower())
    if not entry:
        entry = config.get("default")
    return _extract_melee_event_track(entry)


def play_death_sound(entity: Optional["Actor"]) -> None:
    if not getattr(audio_cfg, "DEATH_SOUND_ENABLED", False):
        return
    track, volume = _select_death_sound(entity)
    if not track:
        return
    default_value = float(getattr(audio_cfg, "DEATH_SOUND_DEFAULT_VOLUME", 1.0))
    resolved_volume = _resolve_volume(volume, default_value)
    _play_sound_effect(track, volume=resolved_volume)


def play_chest_open_sound() -> None:
    if not getattr(audio_cfg, "CHEST_OPEN_SOUND_ENABLED", False):
        return
    track = _pick_random_track("CHEST_OPEN_SOUNDS", "CHEST_OPEN_SOUND")
    if not track:
        return
    volume = getattr(audio_cfg, "CHEST_OPEN_VOLUME", 1.0)
    _play_sound_effect(track, volume=volume)


def play_table_open_sound() -> None:
    if not getattr(audio_cfg, "TABLE_OPEN_SOUND_ENABLED", False):
        return
    track = _pick_random_track("TABLE_OPEN_SOUNDS", "TABLE_OPEN_SOUND")
    if not track:
        return
    volume = getattr(audio_cfg, "TABLE_OPEN_VOLUME", 1.0)
    _play_sound_effect(track, volume=volume)

def play_bookshelf_open_sound() -> None:
    if not getattr(audio_cfg, "BOOKSHELF_OPEN_SOUND_ENABLED", False):
        return
    track = _pick_random_track("BOOKSHELF_OPEN_SOUNDS", "BOOKSHELF_OPEN_SOUND")
    if not track:
        return
    volume = getattr(audio_cfg, "BOOKSHELF_OPEN_VOLUME", 1.0)
    _play_sound_effect(track, volume=volume)

def play_stair_descend_sound() -> None:
    if not getattr(audio_cfg, "STAIR_DESCEND_SOUND_ENABLED", False):
        return
    track = _pick_random_track("STAIR_DESCEND_SOUNDS", "STAIR_DESCEND_SOUND")
    if not track:
        return
    volume = getattr(audio_cfg, "STAIR_DESCEND_VOLUME", 1.0)
    _play_sound_effect(track, volume=volume)


def play_breakable_wall_destroy_sound() -> None:
    if not getattr(audio_cfg, "BREAKABLE_WALL_DESTROY_SOUND_ENABLED", False):
        return
    track = _pick_random_track("BREAKABLE_WALL_DESTROY_SOUNDS", "BREAKABLE_WALL_DESTROY_SOUND")
    if not track:
        return
    volume = getattr(audio_cfg, "BREAKABLE_WALL_DESTROY_VOLUME", 1.0)
    _play_sound_effect(track, volume=volume)


def play_table_destroy_sound() -> None:
    if not getattr(audio_cfg, "TABLE_DESTROY_SOUND_ENABLED", False):
        return
    track = _pick_random_track("TABLE_DESTROY_SOUNDS", "TABLE_DESTROY_SOUND")
    if not track:
        return
    volume = getattr(audio_cfg, "TABLE_DESTROY_VOLUME", 1.0)
    _play_sound_effect(track, volume=volume)


def play_player_stamina_depleted_sound() -> None:
    if not getattr(audio_cfg, "PLAYER_STAMINA_DEPLETED_SOUND_ENABLED", False):
        return
    track = _pick_random_track(
        "PLAYER_STAMINA_DEPLETED_SOUNDS",
        "PLAYER_STAMINA_DEPLETED_SOUND",
    )
    if not track:
        return
    volume = getattr(audio_cfg, "PLAYER_STAMINA_DEPLETED_VOLUME", 1.0)
    _play_sound_effect(track, volume=volume)


def _start_campfire_loop(volume: float) -> None:
    global _campfire_loop_channel, _current_campfire_track

    if not getattr(audio_cfg, "CAMPFIRE_SOUND_ENABLED", False):
        return
    if not _ensure_mixer_initialized(allow_when_disabled=True) or pygame is None:
        return

    channel = _campfire_loop_channel
    if channel and channel.get_busy():
        try:
            channel.set_volume(volume)
        except Exception:
            pass
        return

    track = _pick_random_track("CAMPFIRE_SOUNDS", "CAMPFIRE_SOUND")
    if not track:
        return

    sound = _load_sound(track)
    if sound is None:
        return

    try:
        channel = sound.play(loops=-1)
    except Exception as exc:  # pragma: no cover
        if settings.DEBUG_MODE:
            print(f"[audio] Unable to loop campfire '{track}': {exc}")
        return

    if channel is None:
        return

    try:
        channel.set_volume(max(0.0, min(1.0, volume)))
    except Exception:
        pass
    _campfire_loop_channel = channel
    _current_campfire_track = track


def _stop_campfire_loop(*, fade_ms: int = 500) -> None:
    global _campfire_loop_channel, _current_campfire_track

    channel = _campfire_loop_channel
    if not channel:
        return

    try:
        if fade_ms > 0:
            channel.fadeout(fade_ms)
        else:
            channel.stop()
    except Exception:
        pass

    _campfire_loop_channel = None
    _current_campfire_track = None


def update_campfire_audio(source: object, active: bool, *, fadeout_ms: int = 600) -> None:
    """Start or stop the looping campfire audio depending on player proximity."""
    if source is None:
        return

    if not getattr(audio_cfg, "CAMPFIRE_SOUND_ENABLED", False):
        _campfire_active_sources.clear()
        _stop_campfire_loop(fade_ms=fadeout_ms)
        return

    key = id(source)
    if active:
        if key not in _campfire_active_sources:
            _campfire_active_sources.add(key)
        _start_campfire_loop(float(getattr(audio_cfg, "CAMPFIRE_VOLUME", 1.0)))
    else:
        if key in _campfire_active_sources:
            _campfire_active_sources.remove(key)
        if not _campfire_active_sources:
            _stop_campfire_loop(fade_ms=fadeout_ms)
