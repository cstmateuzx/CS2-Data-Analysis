"""
Pipeline Principal do Projeto CS2 Data Analysis.

Executa o fluxo de ponta a ponta:
1. Coleta os dados da API para cada equipe (opcional via --skip-collect)
2. Limpa, tipifica e desaninha os dados de partidas e mapas
3. Executa testes de integridade
4. Salva os arquivos processados finais (matches.csv e maps.csv)

Uso:
    python run_pipeline.py                 # Executa Coleta + Limpeza
    python run_pipeline.py --skip-collect  # Executa apenas a Limpeza dos dados locais
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from src.cleaner import (
    compute_player_leaderboard,
    compute_team_map_rankings,
    run_cleaner_pipeline,
)
from src.collector import collect_all_matches_stats, collect_all_teams
from src.config import MATCHES_STATS_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Pipeline")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Executa o pipeline completo de dados de CS2."
    )
    parser.add_argument(
        "--skip-collect",
        action="store_true",
        help="Pula as requisicoes a API e utiliza os arquivos locais existentes.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Quantidade de partidas por equipe a coletar da API (padrao: 20).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.time()

    print("=" * 70)
    print(">> INICIANDO PIPELINE COMPLETO: CS2 DATA ANALYSIS")
    print("=" * 70)

    # Etapa 1: Coleta das Partidas das Equipes
    if not args.skip_collect:
        print("\n[Etapa 1/3] Coletando historico de partidas das equipes na API...")
        try:
            collect_all_teams(output_dir=RAW_DATA_DIR, limit=args.limit)
        except Exception as err:
            logger.error("Erro durante a coleta de equipes: %s", err)
            print("[ERRO] Falha na coleta de equipes. Abortando pipeline.")
            sys.exit(1)
    else:
        print("\n[Etapa 1/3] Pulando coleta de equipes (--skip-collect). Utilizando dados locais.")

    # Etapa 2: Coleta das Estatísticas Individuais de Jogadores
    # Primeiro lemos os IDs de partidas locais para saber o que buscar
    from src.cleaner import load_raw_matches, clean_matches_dataframe
    raw_matches = load_raw_matches(raw_dir=RAW_DATA_DIR)
    temp_matches_df = clean_matches_dataframe(raw_matches=raw_matches)
    match_ids = temp_matches_df["match_id"].tolist()

    if not args.skip_collect:
        print(f"\n[Etapa 2/3] Coletando estatisticas de jogadores para {len(match_ids)} partidas...")
        try:
            collect_all_matches_stats(match_ids=match_ids, output_dir=MATCHES_STATS_DIR, delay=0.03)
        except Exception as err:
            logger.warning("Aviso durante a coleta de stats de jogadores: %s", err)
    else:
        print(f"\n[Etapa 2/3] Pulando download de stats de jogadores (--skip-collect). Usando cache local.")

    # Etapa 3: Limpeza, Modelagem Relacional e Geração dos Datasets
    print("\n[Etapa 3/3] Processando, limpando e modelando datasets relacionais...")
    try:
        matches_df, maps_df, player_df = run_cleaner_pipeline(
            raw_dir=RAW_DATA_DIR,
            matches_stats_dir=MATCHES_STATS_DIR,
            output_dir=PROCESSED_DATA_DIR,
        )
    except Exception as err:
        logger.error("Erro durante a limpeza: %s", err)
        print("[ERRO] Falha na limpeza. Abortando pipeline.")
        sys.exit(1)

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(">> PIPELINE CONCLUIDO COM SUCESSO!")
    print(f"Tempo total de execucao: {elapsed:.2f} segundos")
    print(f"Partidas processadas:       {len(matches_df)} -> {PROCESSED_DATA_DIR / 'matches.csv'}")
    print(f"Mapas individuais:          {len(maps_df)} -> {PROCESSED_DATA_DIR / 'maps.csv'}")
    if player_df is not None and not player_df.empty:
        print(f"Estatisticas de jogadores:  {len(player_df)} -> {PROCESSED_DATA_DIR / 'player_stats.csv'}")
    print("=" * 70)

    # Exibição dos Primeiros Rankings Analíticos
    if player_df is not None and not player_df.empty:
        print("\n" + "-" * 70)
        print(">> TOP 5 JOGADORES POR RATING MEDIO (min. 3 partidas):")
        leaderboard = compute_player_leaderboard(player_df, min_matches=3)
        top_rating = leaderboard.sort_values(by="avg_rating", ascending=False).head(5)
        for rank, (_, row) in enumerate(top_rating.iterrows(), 1):
            print(f"  #{rank} {row['player_name']} ({row['team_name']}): Rating {row['avg_rating']} | K/D {row['overall_kd']} | ADR {row['avg_adr']} | Kills {row['total_kills']}")

        print("\n>> TOP 5 JOGADORES MAIS IMPACTANTES (Impact Swing medio):")
        top_impact = leaderboard.sort_values(by="avg_impact_swing", ascending=False).head(5)
        for rank, (_, row) in enumerate(top_impact.iterrows(), 1):
            print(f"  #{rank} {row['player_name']} ({row['team_name']}): Impact {row['avg_impact_swing']} | Rating {row['avg_rating']} | Partidas {row['matches_played']}")

    if not maps_df.empty:
        print("\n>> RANKING DE EQUIPES POR MAPA (Exemplo: Melhores Winrates na Dust2):")
        map_ranks = compute_team_map_rankings(maps_df)
        dust2_ranks = map_ranks[map_ranks["map_name"] == "Dust2"].head(5)
        for rank, (_, row) in enumerate(dust2_ranks.iterrows(), 1):
            print(f"  #{rank} {row['team_name']}: {row['winrate_pct']}% Winrate ({row['maps_won']}/{row['maps_played']} mapas) | Saldo medio rounds: {row['avg_round_diff']:+0.1f}")
    print("-" * 70 + "\n")


if __name__ == "__main__":
    main()
