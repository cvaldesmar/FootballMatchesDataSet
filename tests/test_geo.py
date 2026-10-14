from src.football_dataset.UtilsAndGlobals import (
    get_travel_distance_km,
    haversine_distance_km,
)


def test_haversine_is_zero_for_same_stadium_and_symmetric():
    madrid = (40.4168, -3.7038)
    assert haversine_distance_km(madrid, madrid) == 0
    assert haversine_distance_km((40.4168, -3.7038), (41.3874, 2.1686)) == (
        haversine_distance_km((41.3874, 2.1686), (40.4168, -3.7038))
    )


def test_known_barcelona_madrid_distance_is_reasonable():
    distance = haversine_distance_km((41.3874, 2.1686), (40.4168, -3.7038))
    assert 500 <= distance <= 600


def test_missing_historical_team_uses_neutral_value():
    assert get_travel_distance_km("Equipo histórico desconocido", "Barcelona") == -1


def test_derby_distance_is_local_scale():
    distance = get_travel_distance_km("Real Madrid", "Atlético de Madrid")
    assert 0 < distance < 10
