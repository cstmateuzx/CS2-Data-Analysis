"""
Testes unitários para o módulo de coleta (src/collector.py).
Utiliza mocks para testar chamadas de rede, timeouts, retries em 429 e salvamento de arquivos.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.collector import fetch_match_stats, fetch_team_matches, save_raw_json


def test_fetch_team_matches_success():
    """Valida se a requisição bem-sucedida (status 200) retorna os dados em formato JSON."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": 1, "event": "Major"}]

    with patch("requests.get", return_value=mock_response) as mock_get:
        data = fetch_team_matches(team_id=7020, limit=1)

        assert len(data) == 1
        assert data[0]["id"] == 1
        mock_get.assert_called_once()


def test_fetch_team_matches_timeout():
    """Valida se a função trata e propaga o erro de Timeout adequadamente."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout):
        with pytest.raises(requests.exceptions.Timeout):
            fetch_team_matches(team_id=7020, limit=1, timeout=1)


def test_fetch_match_stats_retry_on_429():
    """Valida se o mecanismo de retry com backoff exponencial funciona quando recebe HTTP 429."""
    # 1ª tentativa: retorna 429; 2ª tentativa: retorna 200 com sucesso
    mock_429 = MagicMock()
    mock_429.status_code = 429

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = [{"id": 0, "name": "All"}]

    with patch("requests.get", side_effect=[mock_429, mock_200]):
        with patch("time.sleep", return_value=None):  # não trava o teste
            data = fetch_match_stats(match_id=9999, max_retries=2)

            assert len(data) == 1
            assert data[0]["name"] == "All"


def test_save_raw_json(tmp_path):
    """Valida se a função save_raw_json cria diretórios pais e grava JSON em UTF-8 formatado."""
    output_file = tmp_path / "subpasta" / "test_team.json"
    dummy_data = [{"team": "Spirit", "score": 2}]

    save_raw_json(dummy_data, output_file)

    assert output_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded == dummy_data
