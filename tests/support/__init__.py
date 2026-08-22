"""Общие test-support утилиты: fail-closed DSN/network/subprocess guards.

Модули здесь не создают сетевых подключений при import — только валидация
и monkeypatch socket/subprocess/os/asyncio. Live PG/CH clients создаются
только после marker ``destructive_local`` + validator + destructive opt-in.
"""
