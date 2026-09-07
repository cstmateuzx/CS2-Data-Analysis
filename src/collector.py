"""
Módulo de Coleta de Dados da API CS2 (api.csapi.de).
Responsável por buscar o histórico de partidas das equipes selecionadas e armazenar em formato JSON bruto.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

from src.config import (
    BASE_API_URL,
    DEFAULT_MATCH_LIMIT,
    MATCHES_STATS_DIR,
    RAW_DATA_DIR,
    REQUEST_TIMEOUT,
    TEAMS,
)

# Configuração de logs para rastreabilidade
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_team_matches(
    team_id: int,
    limit: int = DEFAULT_MATCH_LIMIT,
    timeout: int = REQUEST_TIMEOUT,
) -> List[dict]:
    """
    Busca o histórico de partidas de um time específico na API da CSAPI.

    Args:
        team_id: Identificador numérico do time.
        limit: Quantidade de partidas recentes a consultar.
        timeout: Tempo limite da requisição em segundos.

    Returns:
        Lista de dicionários com os dados brutos das partidas.
    """
    endpoint = f"{BASE_API_URL}/teams/{team_id}/matchhistory?limit={limit}"
    logger.info("Requisitando dados da equipe ID %s: %s", team_id, endpoint)

    try:
        response = requests.get(endpoint, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        logger.info("Sucesso: %d partidas retornadas para o time ID %s", len(data), team_id)
        return data
    except requests.exceptions.Timeout:
        logger.error("Timeout de %s segundos excedido ao consultar time %s", timeout, team_id)
        raise
    except requests.exceptions.RequestException as err:
        logger.error("Erro na requisição para o time %s: %s", team_id, err)
        raise


def save_raw_json(data: List[dict], filepath: Path) -> None:
    """
    Salva os dados coletados em formato JSON formatado e com codificação UTF-8.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    logger.info("Arquivo salvo em: %s", filepath)


def collect_all_teams(
    output_dir: Path = RAW_DATA_DIR,
    teams: Optional[Dict[int, str]] = None,
    limit: int = DEFAULT_MATCH_LIMIT,
) -> Dict[str, Path]:
    """
    Executa a coleta de partidas para todos os times mapeados.

    Args:
        output_dir: Diretório de destino para os arquivos JSON.
        teams: Dicionário {team_id: team_name}. Se None, usa o padrão em config.
        limit: Limite de partidas por time.

    Returns:
        Dicionário com o nome do time e o caminho do arquivo gerado.
    """
    teams_to_fetch = teams or TEAMS
    saved_files = {}

    logger.info("Iniciando coleta para %d equipes...", len(teams_to_fetch))

    for team_id, team_name in teams_to_fetch.items():
        try:
            data = fetch_team_matches(team_id=team_id, limit=limit)
            filepath = output_dir / f"{team_name}.json"
            save_raw_json(data, filepath)
            saved_files[team_name] = filepath
        except Exception as err:
            logger.warning("Falha ao coletar dados do time '%s' (%s): %s", team_name, team_id, err)

    logger.info("Coleta finalizada. Total de arquivos salvos: %d", len(saved_files))
    return saved_files


def fetch_match_stats(
    match_id: int,
    timeout: int = REQUEST_TIMEOUT,
    max_retries: int = 3,
) -> List[dict]:
    """
    Busca as estatísticas detalhadas de jogadores para uma partida específica (/matches/{id}/stats).
    Inclui tratamento de retry com espera exponencial caso encontre rate limit (HTTP 429).
    """
    endpoint = f"{BASE_API_URL}/matches/{match_id}/stats"
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(endpoint, timeout=timeout)
            if response.status_code == 429:
                wait_time = attempt * 2.5
                logger.warning(
                    "Rate limit (429) na partida %s. Aguardando %.1fs (tentativa %d/%d)...",
                    match_id,
                    wait_time,
                    attempt,
                    max_retries,
                )
                time.sleep(wait_time)
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            if attempt == max_retries:
                logger.warning("Falha definitiva ao buscar stats da partida %s: %s", match_id, err)
                return []
            time.sleep(1.0)
    return []


def collect_all_matches_stats(
    match_ids: List[int],
    output_dir: Path = MATCHES_STATS_DIR,
    delay: float = 0.2,
) -> int:
    """
    Coleta e armazena em cache os JSONs de estatísticas de todas as partidas informadas.
    Se o arquivo já existir localmente, pula a requisição para economizar rede e tempo.

    Args:
        match_ids: Lista de IDs de partidas a coletar.
        output_dir: Diretório de destino para os arquivos JSON por partida.
        delay: Pausa entre requisições (em segundos) para evitar bloqueio por rate limit.

    Returns:
        Quantidade total de arquivos de partidas em cache/salvos.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(match_ids)
    saved_count = 0
    new_requests = 0

    logger.info("Iniciando coleta/verificação de estatísticas de %d partidas...", total)

    for idx, match_id in enumerate(match_ids, start=1):
        filepath = output_dir / f"{match_id}.json"

        # Cache local inteligente: se já baixou, não requisita novamente
        if filepath.exists() and filepath.stat().st_size > 5:
            saved_count += 1
            continue

        data = fetch_match_stats(match_id)
        if data:
            save_raw_json(data, filepath)
            saved_count += 1
            new_requests += 1

        if delay > 0:
            time.sleep(delay)

        if idx % 20 == 0 or idx == total:
            logger.info("Progresso: %d/%d partidas processadas...", idx, total)

    logger.info("Coleta de stats finalizada: %d partidas em cache (%d novas baixadas)", saved_count, new_requests)
    return saved_count


if __name__ == "__main__":
    collect_all_teams()
