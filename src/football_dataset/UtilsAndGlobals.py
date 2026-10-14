"""Utilidades puras de normalización y validación.

El estado de una ejecución vive en ``ExecutionContext``; este módulo no conserva
registros, contadores, configuración ni singletons.
"""

from __future__ import annotations

import difflib
import logging
import math
import re
import unicodedata
from collections.abc import Callable
from typing import Any

from .Const import NAMES_CORRECTION, NAMES_TO_TRANSFERMARKT_NAMES, TRANSFERMARKT_NAMES_TO_NORMAL

logger = logging.getLogger(__name__)


def RAISE_IF(condition: bool, error_message: str) -> None:
    if condition:
        raise ValueError(error_message)


def RAISE(error_message: str) -> None:
    raise ValueError(error_message)


def CHECK_KEY_EXISTANCE(
    key: Any, collection: dict[Any, Any], new_element: Any | Callable[[], Any]
) -> bool:
    """Mantiene la utilidad histórica sin almacenar estado de módulo."""
    if key in collection:
        return True
    collection[key] = new_element() if callable(new_element) else new_element
    return False


def GET_NORMALIZED_TEAM_NAME(team_name: str) -> str:
    try:
        return NAMES_CORRECTION[team_name]
    except KeyError as error:
        raise ValueError(f"{team_name} no está en la corrección de nombres") from error


def GET_TRANSFERMARKT_TEAM_NAMES(team_name: str) -> list[str]:
    mapped = NAMES_TO_TRANSFERMARKT_NAMES.get(team_name, team_name)
    if isinstance(mapped, list):
        return [str(value) for value in mapped]
    return [str(mapped)]


def _clean_team_text(text: Any) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    stopwords = {
        "rcd",
        "ud",
        "cf",
        "sad",
        "sd",
        "ca",
        "rc",
        "fc",
        "cd",
        "up",
        "ce",
        "ad",
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "club",
        "futbol",
    }
    return " ".join(word for word in normalized.split() if word not in stopwords)


def GET_GLOBAL_EQUIPO_ID_FROM_TRANSFERMARKT_NAME(
    context: Any, team_name: str, alternate_name: str | None = None
) -> int | None:
    """Resuelve un nombre Transfermarkt usando únicamente el contexto recibido."""
    for name in (team_name, alternate_name):
        if not name:
            continue
        target = TRANSFERMARKT_NAMES_TO_NORMAL.get(name, NAMES_CORRECTION.get(name, name))
        if target in context.team_names_to_id:
            return int(context.team_names_to_id[target])
    candidates = list(context.team_names_to_id.items())
    for name in (team_name, alternate_name):
        if not name:
            continue
        query = _clean_team_text(name)
        exact = [
            (team_id, registered)
            for registered, team_id in candidates
            if _clean_team_text(registered) == query
        ]
        if exact:
            return int(exact[0][0])
        contained = [
            (team_id, registered)
            for registered, team_id in candidates
            if _clean_team_text(registered) in query or query in _clean_team_text(registered)
        ]
        if len(contained) == 1:
            return int(contained[0][0])
        fuzzy: tuple[float, int | None] = max(
            (
                (
                    difflib.SequenceMatcher(None, query, _clean_team_text(registered)).ratio(),
                    team_id,
                )
                for registered, team_id in candidates
            ),
            default=(0, None),
        )
        if fuzzy[0] >= 0.78 and fuzzy[1] is not None:
            return fuzzy[1]
    logger.warning(
        "No se pudo emparejar el equipo de Transfermarkt: %s / %s", team_name, alternate_name
    )
    return None


def haversine_distance_km(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    """Calcula la distancia ortodrómica entre dos puntos en kilómetros."""
    earth_radius_km = 6371.0088
    latitude_1, longitude_1 = map(math.radians, origin)
    latitude_2, longitude_2 = map(math.radians, destination)
    delta_latitude = latitude_2 - latitude_1
    delta_longitude = longitude_2 - longitude_1
    a = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_1) * math.cos(latitude_2) * math.sin(delta_longitude / 2) ** 2
    )
    return 2 * earth_radius_km * math.asin(math.sqrt(a))


def get_travel_distance_km(local_team: str, visiting_team: str) -> float:
    """Devuelve la distancia visitante→local o ``-1`` si falta una sede."""
    from .Const import CITY_COORDINATES

    local_coordinates = CITY_COORDINATES.get(local_team)
    visiting_coordinates = CITY_COORDINATES.get(visiting_team)
    if local_coordinates is None or visiting_coordinates is None:
        logger.warning(
            "Coordenadas ausentes para distancia de viaje: local=%s, visitante=%s",
            local_team,
            visiting_team,
        )
        return -1.0
    return haversine_distance_km(visiting_coordinates, local_coordinates)
