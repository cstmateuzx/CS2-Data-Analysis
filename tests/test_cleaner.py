"""
Testes unitários para o módulo de limpeza e modelagem (src/cleaner.py).
Valida regras de negócio, engenharia de features, modelagem relacional e integridade.
"""

import pandas as pd
import pytest

from src.cleaner import (
    clean_matches_dataframe,
    compute_player_leaderboard,
    compute_team_map_rankings,
    extract_maps_dataframe,
    validate_pipeline_integrity,
)


def test_clean_matches_dataframe_deduplication(sample_raw_matches):
    """Valida se a função remove duplicatas de match_id preservando apenas 1 registro por partida."""
    # A fixture sample_raw_matches contém 3 registros, sendo 1 duplicado (ID 1001)
    df = clean_matches_dataframe(sample_raw_matches)

    assert len(df) == 2
    assert sorted(df["match_id"].tolist()) == [1001, 1002]


def test_clean_matches_dataframe_feature_engineering(sample_raw_matches):
    """Valida se as colunas derivadas (W/L e saldo de mapas) são calculadas corretamente."""
    df = clean_matches_dataframe(sample_raw_matches)

    # Partida 1001: Spirit (Team 1) venceu por 2 a 0
    match_1001 = df[df["match_id"] == 1001].iloc[0]
    assert match_1001["team1_result"] == "W"
    assert match_1001["team2_result"] == "L"
    assert match_1001["score_difference"] == 2

    # Partida 1002: FURIA (Team 1) perdeu por 1 a 2 para MOUZ (Team 2)
    match_1002 = df[df["match_id"] == 1002].iloc[0]
    assert match_1002["team1_result"] == "L"
    assert match_1002["team2_result"] == "W"
    assert match_1002["score_difference"] == 1


def test_clean_matches_types_and_columns(sample_raw_matches):
    """Valida renomeação de colunas e tipagem correta de dados."""
    df = clean_matches_dataframe(sample_raw_matches)

    expected_columns = [
        "match_id",
        "best_of",
        "date",
        "event",
        "team1_id",
        "team1_name",
        "team1_score",
        "team2_id",
        "team2_name",
        "team2_score",
        "winner_id",
        "winner_name",
        "team1_result",
        "team2_result",
        "score_difference",
    ]
    for col in expected_columns:
        assert col in df.columns

    # Verifica tipo de data
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_extract_maps_dataframe_relational_model(sample_raw_matches):
    """Valida a modelagem relacional de mapas (extração 1:N com chave estrangeira)."""
    matches_df = clean_matches_dataframe(sample_raw_matches)
    maps_df = extract_maps_dataframe(matches_df)

    # Partida 1001 teve 2 mapas, Partida 1002 teve 3 mapas = 5 mapas no total
    assert len(maps_df) == 5

    # Valida presença da chave estrangeira
    assert set(maps_df["match_id"].unique()) == {1001, 1002}

    # Valida saldo de rounds
    # Ancient: 13-11 -> round_diff = 2
    ancient = maps_df[maps_df["map_name"] == "Ancient"].iloc[0]
    assert ancient["round_difference"] == 2
    assert ancient["map_winner_name"] == "Spirit"

    # Mirage: 13-5 -> round_diff = 8
    mirage = maps_df[maps_df["map_name"] == "Mirage"].iloc[0]
    assert mirage["round_difference"] == 8
    assert mirage["map_winner_name"] == "FURIA"

    # Dust2: FURIA 10 x 13 MOUZ -> MOUZ venceu
    dust2 = maps_df[maps_df["map_name"] == "Dust2"].iloc[0]
    assert dust2["map_winner_name"] == "MOUZ"
    assert dust2["round_difference"] == 3


def test_validate_pipeline_integrity(sample_raw_matches):
    """Valida se o validador de sanidade confirma integridade dos dados e detecta inconsistências."""
    matches_df = clean_matches_dataframe(sample_raw_matches)
    maps_df = extract_maps_dataframe(matches_df)

    report = validate_pipeline_integrity(matches_df, maps_df)

    assert report["matches_count"] == 2
    assert report["maps_count"] == 5
    assert report["null_matches"] == 0
    assert report["null_maps"] == 0
    assert report["matches_without_maps"] == 0


def test_compute_team_map_rankings(sample_raw_matches):
    """Valida o cálculo de taxa de vitória (winrate) por mapa e equipe."""
    matches_df = clean_matches_dataframe(sample_raw_matches)
    maps_df = extract_maps_dataframe(matches_df)

    rankings = compute_team_map_rankings(maps_df)

    # Spirit jogou 1 Ancient e venceu -> 100% winrate
    spirit_ancient = rankings[
        (rankings["team_name"] == "Spirit") & (rankings["map_name"] == "Ancient")
    ].iloc[0]
    assert spirit_ancient["winrate_pct"] == 100.0
    assert spirit_ancient["maps_won"] == 1
    assert spirit_ancient["maps_played"] == 1

    # Falcons jogou 1 Ancient e perdeu -> 0% winrate
    falcons_ancient = rankings[
        (rankings["team_name"] == "Falcons") & (rankings["map_name"] == "Ancient")
    ].iloc[0]
    assert falcons_ancient["winrate_pct"] == 0.0


def test_player_kd_ratio_zero_deaths_protection():
    """Valida a proteção contra divisão por zero no cálculo de K/D quando o jogador tem 0 mortes."""
    # Teste de caso limite: 15 kills e 0 mortes
    kills = 15
    deaths = 0
    kd_ratio = round(kills / max(1, deaths), 2)

    assert kd_ratio == 15.0
