"""Harmony engine: chord vocabulary, loop generation, colour and key changes."""

from .progression import ChordEvent, Loop, generate_loop
from .modulation import maybe_modulate, modulate
from .vocabulary import build_pool

__all__ = ["ChordEvent", "Loop", "build_pool", "generate_loop", "maybe_modulate", "modulate"]
