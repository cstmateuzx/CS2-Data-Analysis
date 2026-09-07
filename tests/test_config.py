"""
Testes unitários para o módulo de configurações (src/config.py).
"""

from pathlib import Path
from src.config import (
    BASE_API_URL,
    BASE_DIR,
    DATA_DIR,
    MATCHES_STATS_DIR,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    TEAMS,
)


def test_config_paths():
    """Valida se os caminhos de diretórios estão definidos corretamente como instâncias de Path."""
    assert isinstance(BASE_DIR, Path)
    assert isinstance(DATA_DIR, Path)
    assert isinstance(RAW_DATA_DIR, Path)
    assert isinstance(MATCHES_STATS_DIR, Path)
    assert isinstance(PROCESSED_DATA_DIR, Path)

    # Verifica se os subdiretórios apontam para dentro de DATA_DIR
    assert RAW_DATA_DIR.parent == DATA_DIR
    assert PROCESSED_DATA_DIR.parent == DATA_DIR
    assert MATCHES_STATS_DIR.parent == RAW_DATA_DIR


def test_teams_mapping():
    """Valida a integridade do dicionário de equipes mapeadas."""
    assert isinstance(TEAMS, dict)
    assert len(TEAMS) == 6

    # IDs oficiais conhecidos
    expected_teams = {
        7020: "spirit",
        4494: "mouz",
        11283: "falcons",
        13286: "fut",
        9565: "vitality",
        8297: "furia",
    }
    assert TEAMS == expected_teams


def test_api_base_url():
    """Valida a URL base da API."""
    assert BASE_API_URL.startswith("https://")
    assert "csapi.de" in BASE_API_URL
