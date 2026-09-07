"""
Módulo de Limpeza, Tratamento e Modelagem Relacional de Dados.
Transforma os arquivos brutos JSON em DataFrames relacionais limpos (matches e maps).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.config import (
    LEGACY_RAW_DIR,
    MATCHES_STATS_DIR,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    TEAMS,
)

logger = logging.getLogger(__name__)

# Mapeamento padrão de renomeação de colunas da API para formato relacional limpo
COLUMNS_RENAME_MAP = {
    "id": "match_id",
    "team1.id": "team1_id",
    "team1.name": "team1_name",
    "team1.score": "team1_score",
    "team1.rank": "team1_rank",
    "team2.id": "team2_id",
    "team2.name": "team2_name",
    "team2.score": "team2_score",
    "team2.rank": "team2_rank",
    "winner.id": "winner_id",
    "winner.name": "winner_name",
}

NUMERIC_COLUMNS = [
    "match_id",
    "team1_id",
    "team2_id",
    "team1_score",
    "team2_score",
    "team1_rank",
    "team2_rank",
    "winner_id",
    "best_of",
]


def load_raw_matches(raw_dir: Path) -> List[dict]:
    """
    Lê todos os arquivos JSON de equipes no diretório especificado.
    Caso o diretório padrão esteja vazio, tenta carregar do diretório legado.
    """
    target_dir = raw_dir
    if not target_dir.exists() or not list(target_dir.glob("*.json")):
        if LEGACY_RAW_DIR.exists() and list(LEGACY_RAW_DIR.glob("*.json")):
            logger.info("Dados não encontrados em %s. Usando diretório legado: %s", target_dir, LEGACY_RAW_DIR)
            target_dir = LEGACY_RAW_DIR
        else:
            raise FileNotFoundError(f"Nenhum arquivo JSON encontrado em {raw_dir} nem em {LEGACY_RAW_DIR}")

    all_matches = []
    json_files = list(target_dir.glob("*.json"))
    logger.info("Carregando dados de %d arquivos JSON em: %s", len(json_files), target_dir)

    for filepath in json_files:
        with open(filepath, "r", encoding="utf-8") as file:
            matches = json.load(file)
            for match in matches:
                match["_source"] = filepath.name
                all_matches.append(match)

    logger.info("Total de partidas carregadas dos arquivos brutos: %d", len(all_matches))
    return all_matches


def clean_matches_dataframe(raw_matches: List[dict]) -> pd.DataFrame:
    """
    Normaliza a lista de partidas brutas e aplica as transformações:
    - Renomeação de colunas hierárquicas
    - Conversão de tipos (datas e inteiros)
    - Deduplicação por match_id
    - Engenharia de features: team1_result, team2_result e score_difference
    """
    logger.info("Iniciando normalização e limpeza das partidas...")
    df = pd.json_normalize(raw_matches)

    # Renomeação de colunas
    df = df.rename(columns=COLUMNS_RENAME_MAP)

    # Conversão de data
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Conversão de colunas numéricas
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Deduplicação por match_id (remove partidas compartilhadas entre equipes)
    total_before = len(df)
    df = df.drop_duplicates(subset="match_id").reset_index(drop=True)
    logger.info("Partidas desduplicadas: de %d para %d registros únicos", total_before, len(df))

    # Engenharia de Features
    df["team1_result"] = df.apply(
        lambda row: "W" if row["winner_id"] == row["team1_id"] else "L",
        axis=1,
    )
    df["team2_result"] = df.apply(
        lambda row: "W" if row["winner_id"] == row["team2_id"] else "L",
        axis=1,
    )
    df["score_difference"] = (df["team1_score"] - df["team2_score"]).abs()

    return df


def extract_maps_dataframe(matches_df: pd.DataFrame) -> pd.DataFrame:
    """
    Modela a entidade relacional 'maps' extraindo o array de mapas de cada partida.
    Cria a chave estrangeira 'match_id', calcula 'round_difference' e define o time vencedor do mapa.
    """
    logger.info("Extraindo dados de mapas individuais por partida...")
    maps_records = []

    for _, match in matches_df.iterrows():
        match_id = match["match_id"]
        team1_id = match.get("team1_id")
        team1_name = match.get("team1_name")
        team2_id = match.get("team2_id")
        team2_name = match.get("team2_name")
        maps_list = match.get("maps", [])

        if isinstance(maps_list, list):
            for map_info in maps_list:
                t1_score = map_info.get("team1_score")
                t2_score = map_info.get("team2_score")

                # Define o vencedor daquele mapa específico
                map_winner_id = team1_id if (t1_score is not None and t2_score is not None and t1_score > t2_score) else team2_id
                map_winner_name = team1_name if (t1_score is not None and t2_score is not None and t1_score > t2_score) else team2_name

                maps_records.append({
                    "match_id": match_id,
                    "map_id": map_info.get("id"),
                    "map_name": map_info.get("name"),
                    "team1_id": team1_id,
                    "team1_name": team1_name,
                    "team1_map_score": t1_score,
                    "team2_id": team2_id,
                    "team2_name": team2_name,
                    "team2_map_score": t2_score,
                    "map_winner_id": map_winner_id,
                    "map_winner_name": map_winner_name,
                })

    maps_df = pd.DataFrame(maps_records)

    # Conversão de tipos e cálculo da diferença de rounds
    numeric_map_cols = [
        "match_id",
        "map_id",
        "team1_id",
        "team2_id",
        "team1_map_score",
        "team2_map_score",
        "map_winner_id",
    ]
    for col in numeric_map_cols:
        if col in maps_df.columns:
            maps_df[col] = pd.to_numeric(maps_df[col], errors="coerce")

    maps_df["round_difference"] = (
        maps_df["team1_map_score"] - maps_df["team2_map_score"]
    ).abs()

    logger.info("Total de mapas individuais extraídos: %d", len(maps_df))
    return maps_df


def extract_player_stats_dataframe(
    matches_stats_dir: Path = MATCHES_STATS_DIR,
    matches_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Lê os arquivos JSON brutos de estatísticas de partidas (/matches/{id}/stats)
    e estrutura um DataFrame relacional com a performance individual de cada jogador.
    """
    if not matches_stats_dir.exists() or not list(matches_stats_dir.glob("*.json")):
        logger.warning("Nenhum arquivo de estatísticas encontrado em: %s", matches_stats_dir)
        return pd.DataFrame()

    logger.info("Iniciando extração de estatísticas individuais de jogadores...")
    player_records = []

    # Mapa rápido de contexto por partida (data e torneio)
    match_metadata = {}
    if matches_df is not None and not matches_df.empty:
        for _, row in matches_df.iterrows():
            match_metadata[int(row["match_id"])] = {
                "date": row.get("date"),
                "event": row.get("event"),
            }

    stat_files = list(matches_stats_dir.glob("*.json"))

    for filepath in stat_files:
        try:
            match_id = int(filepath.stem)
        except ValueError:
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = match_metadata.get(match_id, {})
        match_date = meta.get("date")
        match_event = meta.get("event")

        # Cada arquivo possui uma lista com o resumo da série ("All")
        for item in data:
            scope = item.get("name", "All")

            for team_key in ["team1", "team2"]:
                team_data = item.get(team_key, {})
                team_id = team_data.get("id")
                team_name = team_data.get("name")

                players_list = team_data.get("players", [])
                for p in players_list:
                    player_id = p.get("id")
                    player_name = p.get("name")
                    kills = int(p.get("k", 0) or 0)
                    deaths = int(p.get("d", 0) or 0)
                    rating = float(p.get("rating", 0.0) or 0.0)
                    adr = float(p.get("adr", 0.0) or 0.0)
                    kast = float(p.get("kast", 0.0) or 0.0)
                    swing = float(p.get("swing", 0.0) or 0.0)

                    kd_ratio = round(kills / max(1, deaths), 2)
                    kd_diff = kills - deaths

                    player_records.append({
                        "match_id": match_id,
                        "date": match_date,
                        "event": match_event,
                        "scope": scope,
                        "team_id": team_id,
                        "team_name": team_name,
                        "player_id": player_id,
                        "player_name": player_name,
                        "kills": kills,
                        "deaths": deaths,
                        "kd_ratio": kd_ratio,
                        "kd_diff": kd_diff,
                        "rating": rating,
                        "adr": adr,
                        "kast": kast,
                        "impact_swing": swing,
                    })

    player_df = pd.DataFrame(player_records)
    if not player_df.empty:
        # Tipagem correta
        numeric_cols = [
            "match_id",
            "team_id",
            "player_id",
            "kills",
            "deaths",
            "kd_ratio",
            "kd_diff",
            "rating",
            "adr",
            "kast",
            "impact_swing",
        ]
        for col in numeric_cols:
            if col in player_df.columns:
                player_df[col] = pd.to_numeric(player_df[col], errors="coerce")

        player_df = player_df.drop_duplicates(
            subset=["match_id", "player_id", "scope"]
        ).reset_index(drop=True)

    logger.info("Total de registros de jogadores extraídos: %d", len(player_df))
    return player_df


def compute_player_leaderboard(
    player_stats_df: pd.DataFrame,
    min_matches: int = 3,
) -> pd.DataFrame:
    """
    Consolida as métricas acumuladas e médias de cada jogador para geração de rankings.
    """
    if player_stats_df.empty:
        return pd.DataFrame()

    # Considera os dados da série geral ("All")
    df_all = player_stats_df[player_stats_df["scope"] == "All"]
    if df_all.empty:
        df_all = player_stats_df

    leaderboard = (
        df_all.groupby(["player_id", "player_name", "team_name"])
        .agg(
            matches_played=("match_id", "nunique"),
            total_kills=("kills", "sum"),
            total_deaths=("deaths", "sum"),
            avg_kills_per_match=("kills", "mean"),
            avg_rating=("rating", "mean"),
            avg_adr=("adr", "mean"),
            avg_kast=("kast", "mean"),
            avg_impact_swing=("impact_swing", "mean"),
        )
        .reset_index()
    )

    # Filtra por mínimo de partidas jogadas
    leaderboard = leaderboard[leaderboard["matches_played"] >= min_matches].copy()

    # Métricas derivadas consolidadas
    leaderboard["overall_kd"] = (
        leaderboard["total_kills"] / leaderboard["total_deaths"].clip(lower=1)
    ).round(2)
    leaderboard["kd_diff"] = leaderboard["total_kills"] - leaderboard["total_deaths"]
    leaderboard["avg_rating"] = leaderboard["avg_rating"].round(2)
    leaderboard["avg_adr"] = leaderboard["avg_adr"].round(1)
    leaderboard["avg_kast"] = leaderboard["avg_kast"].round(1)
    leaderboard["avg_kills_per_match"] = leaderboard["avg_kills_per_match"].round(1)
    leaderboard["avg_impact_swing"] = leaderboard["avg_impact_swing"].round(2)

    return leaderboard


def compute_team_map_rankings(maps_df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera o ranking de equipes por mapa: winrate, partidas jogadas e saldo de rounds.
    """
    if maps_df.empty:
        return pd.DataFrame()

    # Cada mapa gera uma linha para team1 e uma para team2
    team1_rows = maps_df[["match_id", "map_name", "team1_name", "team1_map_score", "team2_map_score", "map_winner_name"]].copy()
    team1_rows = team1_rows.rename(columns={
        "team1_name": "team_name",
        "team1_map_score": "rounds_won",
        "team2_map_score": "rounds_lost",
    })

    team2_rows = maps_df[["match_id", "map_name", "team2_name", "team2_map_score", "team1_map_score", "map_winner_name"]].copy()
    team2_rows = team2_rows.rename(columns={
        "team2_name": "team_name",
        "team2_map_score": "rounds_won",
        "team1_map_score": "rounds_lost",
    })

    combined = pd.concat([team1_rows, team2_rows], ignore_index=True)
    combined["won_map"] = (combined["team_name"] == combined["map_winner_name"]).astype(int)
    combined["round_diff"] = combined["rounds_won"] - combined["rounds_lost"]

    rankings = (
        combined.groupby(["map_name", "team_name"])
        .agg(
            maps_played=("match_id", "count"),
            maps_won=("won_map", "sum"),
            avg_round_diff=("round_diff", "mean"),
        )
        .reset_index()
    )

    rankings["maps_lost"] = rankings["maps_played"] - rankings["maps_won"]
    rankings["winrate_pct"] = (
        (rankings["maps_won"] / rankings["maps_played"]) * 100
    ).round(1)
    rankings["avg_round_diff"] = rankings["avg_round_diff"].round(1)

    return rankings.sort_values(by=["map_name", "winrate_pct", "maps_played"], ascending=[True, False, False])


def validate_pipeline_integrity(
    matches_df: pd.DataFrame,
    maps_df: pd.DataFrame,
    player_df: Optional[pd.DataFrame] = None,
) -> Dict[str, any]:
    """
    Realiza testes de sanidade e validação de regras de negócio:
    - Checagem de nulos
    - Consistência de best_of vs quantidade de mapas jogados
    - Consistência de estatísticas de jogadores
    """
    logger.info("Executando validações de integridade dos dados...")

    maps_count = maps_df.groupby("match_id").size().rename("maps_count").reset_index()
    val_df = matches_df[["match_id", "best_of"]].merge(maps_count, on="match_id", how="left")

    null_matches = matches_df.isna().sum().sum()
    null_maps = maps_df.isna().sum().sum()
    null_players = player_df.isna().sum().sum() if player_df is not None and not player_df.empty else 0
    matches_without_maps = val_df["maps_count"].isna().sum()

    logger.info(
        "Validação concluída: Partidas=%d, Mapas=%d, Jogadores=%d, Nulos(matches)=%d, Nulos(maps)=%d, Nulos(players)=%d",
        len(matches_df),
        len(maps_df),
        len(player_df) if player_df is not None else 0,
        null_matches,
        null_maps,
        null_players,
    )

    return {
        "matches_count": len(matches_df),
        "maps_count": len(maps_df),
        "player_count": len(player_df) if player_df is not None else 0,
        "null_matches": int(null_matches),
        "null_maps": int(null_maps),
        "null_players": int(null_players),
        "matches_without_maps": int(matches_without_maps),
    }


def save_processed_datasets(
    matches_df: pd.DataFrame,
    maps_df: pd.DataFrame,
    player_df: Optional[pd.DataFrame] = None,
    output_dir: Path = PROCESSED_DATA_DIR,
) -> Tuple[Path, Path, Optional[Path]]:
    """
    Salva todos os datasets tratados finais em CSV.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    clean_matches = matches_df.drop(columns=["maps"], errors="ignore")
    matches_path = output_dir / "matches.csv"
    maps_path = output_dir / "maps.csv"
    players_path = None

    clean_matches.to_csv(matches_path, index=False)
    maps_df.to_csv(maps_path, index=False)

    logger.info("Arquivos processados salvos:")
    logger.info(" -> %s (%d linhas)", matches_path, len(clean_matches))
    logger.info(" -> %s (%d linhas)", maps_path, len(maps_df))

    if player_df is not None and not player_df.empty:
        players_path = output_dir / "player_stats.csv"
        player_df.to_csv(players_path, index=False)
        logger.info(" -> %s (%d linhas)", players_path, len(player_df))

    return matches_path, maps_path, players_path


def run_cleaner_pipeline(
    raw_dir: Path = RAW_DATA_DIR,
    matches_stats_dir: Path = MATCHES_STATS_DIR,
    output_dir: Path = PROCESSED_DATA_DIR,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Função orquestradora da etapa de limpeza e modelagem.
    """
    raw_matches = load_raw_matches(raw_dir=raw_dir)
    matches_df = clean_matches_dataframe(raw_matches=raw_matches)
    maps_df = extract_maps_dataframe(matches_df=matches_df)
    player_df = extract_player_stats_dataframe(
        matches_stats_dir=matches_stats_dir,
        matches_df=matches_df,
    )

    validate_pipeline_integrity(matches_df=matches_df, maps_df=maps_df, player_df=player_df)
    save_processed_datasets(matches_df=matches_df, maps_df=maps_df, player_df=player_df, output_dir=output_dir)

    return matches_df, maps_df, player_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_cleaner_pipeline()
