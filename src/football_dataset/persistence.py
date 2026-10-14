"""Primitivas compartidas para persistencia segura y versionada."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any


class CacheError(RuntimeError):
    """Error al leer o validar una caché persistida."""


class CacheVersionError(CacheError):
    """La versión de una caché no es compatible con la aplicación."""


class CacheCorruptError(CacheError):
    """La caché no contiene un payload JSON válido o completo."""


def atomic_write_text(path: str | Path, content: str) -> None:
    """Escribe texto de forma atómica en el mismo directorio del destino."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def atomic_json_dump(path: str | Path, payload: Any) -> None:
    """Serializa JSON y lo publica mediante escritura atómica."""
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def load_versioned_json(
    path: str | Path,
    *,
    cache_name: str,
    current_version: int,
    migrations: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] | None = None,
) -> dict[str, Any] | None:
    """Carga una caché, aplica migraciones registradas y valida su contrato."""
    source = Path(path)
    if not source.exists():
        return None
    try:
        with source.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CacheCorruptError(f"Caché de {cache_name} corrupta: {source}") from error
    if not isinstance(payload, dict) or "version" not in payload:
        raise CacheCorruptError(f"Caché de {cache_name} sin campo 'version': {source}")
    version = payload["version"]
    if not isinstance(version, int):
        raise CacheVersionError(f"Versión de caché de {cache_name} inválida: {version!r}")
    if version > current_version or version < 1:
        raise CacheVersionError(
            f"Versión de caché de {cache_name} no compatible: {version}; "
            f"versión actual {current_version}"
        )
    migrations = migrations or {}
    while version < current_version:
        migrate = migrations.get(version)
        if migrate is None:
            raise CacheVersionError(
                f"No existe migración para caché de {cache_name} desde la versión {version}"
            )
        try:
            payload = migrate(payload)
        except (KeyError, TypeError, ValueError) as error:
            raise CacheCorruptError(
                f"No se pudo migrar la caché de {cache_name} desde la versión {version}"
            ) from error
        if not isinstance(payload, dict) or payload.get("version") != version + 1:
            raise CacheVersionError(f"Migración inválida de caché de {cache_name}: {version}")
        version += 1
    if "cache" not in payload or not isinstance(payload["cache"], dict):
        raise CacheCorruptError(f"Caché de {cache_name} sin campo 'cache' válido: {source}")
    return payload
