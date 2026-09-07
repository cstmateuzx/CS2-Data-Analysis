"""
Fixtures compartilhadas para a suite de testes do Pytest.
Fornece dados sintéticos consistentes sem necessidade de requisições de rede.
"""

import pytest


@pytest.fixture
def sample_raw_matches():
    """
    Retorna uma lista de partidas brutas no formato retornado pela API csapi.de.
    Inclui uma partida duplicada para testar o algoritmo de desduplicação.
    """
    return [
        {
            "id": 1001,
            "team1": {"id": 7020, "name": "Spirit", "score": 2, "rank": 1},
            "team2": {"id": 11283, "name": "Falcons", "score": 0, "rank": 3},
            "maps": [
                {"id": 3, "name": "Ancient", "team1_score": 13, "team2_score": 11},
                {"id": 5, "name": "Nuke", "team1_score": 13, "team2_score": 8},
            ],
            "best_of": 3,
            "date": "2026-09-01",
            "event": "BLAST Premier 2026",
            "winner": {"id": 7020, "name": "Spirit"},
        },
        {
            "id": 1002,
            "team1": {"id": 8297, "name": "FURIA", "score": 1, "rank": 7},
            "team2": {"id": 4494, "name": "MOUZ", "score": 2, "rank": 4},
            "maps": [
                {"id": 6, "name": "Mirage", "team1_score": 13, "team2_score": 5},
                {"id": 4, "name": "Dust2", "team1_score": 10, "team2_score": 13},
                {"id": 7, "name": "Inferno", "team1_score": 8, "team2_score": 13},
            ],
            "best_of": 3,
            "date": "2026-09-02",
            "event": "IEM Cologne 2026",
            "winner": {"id": 4494, "name": "MOUZ"},
        },
        # Partida duplicada com ID 1001 (simulando confronto direto entre equipes monitoradas)
        {
            "id": 1001,
            "team1": {"id": 7020, "name": "Spirit", "score": 2, "rank": 1},
            "team2": {"id": 11283, "name": "Falcons", "score": 0, "rank": 3},
            "maps": [
                {"id": 3, "name": "Ancient", "team1_score": 13, "team2_score": 11},
                {"id": 5, "name": "Nuke", "team1_score": 13, "team2_score": 8},
            ],
            "best_of": 3,
            "date": "2026-09-01",
            "event": "BLAST Premier 2026",
            "winner": {"id": 7020, "name": "Spirit"},
        },
    ]


@pytest.fixture
def sample_match_stats():
    """
    Retorna a estrutura de estatísticas de jogadores para uma partida (/matches/{id}/stats).
    """
    return [
        {
            "id": 0,
            "name": "All",
            "team1": {
                "id": 7020,
                "name": "Spirit",
                "players": [
                    {
                        "id": 21167,
                        "name": "donk",
                        "k": 35,
                        "d": 20,
                        "swing": 3.5,
                        "adr": 95.0,
                        "kast": 80.0,
                        "rating": 1.45,
                    },
                    {
                        "id": 16920,
                        "name": "sh1ro",
                        "k": 28,
                        "d": 18,
                        "swing": 2.1,
                        "adr": 78.5,
                        "kast": 75.0,
                        "rating": 1.25,
                    },
                ],
            },
            "team2": {
                "id": 11283,
                "name": "Falcons",
                "players": [
                    {
                        "id": 22425,
                        "name": "m0nesy",
                        "k": 30,
                        "d": 22,
                        "swing": 2.8,
                        "adr": 85.0,
                        "kast": 76.0,
                        "rating": 1.30,
                    },
                    {
                        "id": 429,
                        "name": "karrigan",
                        "k": 15,
                        "d": 30,
                        "swing": -2.0,
                        "adr": 50.0,
                        "kast": 60.0,
                        "rating": 0.75,
                    },
                ],
            },
        }
    ]
