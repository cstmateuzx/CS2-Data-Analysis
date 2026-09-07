"""
CS2 Data Analysis - Dashboard Profissional de eSports
Painel de inteligencia competitiva para analise de desempenho de equipes e jogadores.
"""

from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# CONFIGURACAO DA PAGINA E TEMA ESCURO
# ==============================================================================
st.set_page_config(
    page_title="CS2 Pro Analytics | Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilizacao CSS profissional em Dark Mode
st.markdown(
    """
    <style>
    /* Fundo geral e tipografia */
    .stApp {
        background-color: #0B0F19;
        color: #E2E8F0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Cards de metricas */
    .metric-box {
        background: #151C2C;
        border: 1px solid #253047;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .metric-label {
        color: #94A3B8;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .metric-number {
        color: #F8FAFC;
        font-size: 26px;
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-detail {
        color: #38BDF8;
        font-size: 13px;
        font-weight: 500;
        margin-top: 4px;
    }

    /* Caixa explicativa informativa */
    .info-callout {
        background-color: #131E33;
        border-left: 4px solid #38BDF8;
        border-radius: 4px;
        padding: 12px 16px;
        margin-bottom: 20px;
        color: #CBD5E1;
        font-size: 14px;
    }

    /* Tabelas */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# CONSTANTES E DADOS
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

# As 6 equipes monitoradas no projeto
TOP_6_TEAMS = ["Spirit", "MOUZ", "Falcons", "FUT", "Vitality", "FURIA"]


@st.cache_data
def load_data():
    matches_df = pd.read_csv(DATA_DIR / "matches.csv")
    maps_df = pd.read_csv(DATA_DIR / "maps.csv")
    players_df = pd.read_csv(DATA_DIR / "player_stats.csv")

    matches_df["date"] = pd.to_datetime(matches_df["date"], errors="coerce")
    players_df["date"] = pd.to_datetime(players_df["date"], errors="coerce")

    return matches_df, maps_df, players_df


try:
    matches_df, maps_df, players_df = load_data()
except Exception as err:
    st.error(f"Erro ao carregar dados: {err}")
    st.stop()

# ==============================================================================
# BARRA LATERAL (FILTROS OBJETIVOS)
# ==============================================================================
st.sidebar.markdown("### CS2 Pro Analytics")
st.sidebar.caption("Analise de Desempenho do Top 6 Mundial")

menu = st.sidebar.radio(
    "Secao",
    [
        "Visao Geral e Leaderboard",
        "Analise por Jogador",
        "Desempenho por Mapa",
        "Historico de Partidas",
    ],
)

st.sidebar.divider()
st.sidebar.markdown("**Filtros de Equipe**")

selected_team = st.sidebar.selectbox(
    "Selecionar Equipe:",
    options=["Todas as 6 Equipes"] + TOP_6_TEAMS,
    index=0,
    help="Filtra os dados para uma equipe especifica ou mantem a comparacao entre as 6.",
)

# Filtro de partidas minimas: padrao em 18 jogos (elenco principal das 6 equipes)
min_matches = st.sidebar.slider(
    "Minimo de Jogos (Filtro de Titulares)",
    min_value=14,
    max_value=26,
    value=18,
    step=1,
    help="Define o corte de partidas. O padrao de 18 jogos isola os titulares das 6 equipes principais.",
)

st.sidebar.divider()
st.sidebar.caption("Projeto desenvolvido em Python com Pandas, Streamlit e Plotly.")

# ==============================================================================
# APLICACAO DOS RECORTES DE NEGOCIO (TOP 6 EQUIPES)
# ==============================================================================
# 1. Filtro de mapas: apenas quando a equipe analisada for do Top 6
t1_maps = maps_df[maps_df["team1_name"].isin(TOP_6_TEAMS)].copy()
t1_maps = t1_maps.rename(
    columns={
        "team1_name": "team_name",
        "team1_map_score": "rounds_won",
        "team2_map_score": "rounds_lost",
    }
)

t2_maps = maps_df[maps_df["team2_name"].isin(TOP_6_TEAMS)].copy()
t2_maps = t2_maps.rename(
    columns={
        "team2_name": "team_name",
        "team2_map_score": "rounds_won",
        "team1_map_score": "rounds_lost",
    }
)

team_maps_filtered = pd.concat([t1_maps, t2_maps], ignore_index=True)
team_maps_filtered["is_winner"] = (
    team_maps_filtered["team_name"] == team_maps_filtered["map_winner_name"]
).astype(int)
team_maps_filtered["round_diff"] = (
    team_maps_filtered["rounds_won"] - team_maps_filtered["rounds_lost"]
)

# 2. Filtro de jogadores: apenas dos times do Top 6
top6_players = players_df[
    (players_df["team_name"].isin(TOP_6_TEAMS))
    & (players_df["scope"] == "All")
].copy()

# Consolidacao do Leaderboard dos Jogadores
player_summary = (
    top6_players.groupby(["player_id", "player_name", "team_name"])
    .agg(
        matches_played=("match_id", "nunique"),
        total_kills=("kills", "sum"),
        total_deaths=("deaths", "sum"),
        avg_rating=("rating", "mean"),
        avg_adr=("adr", "mean"),
        avg_kast=("kast", "mean"),
        avg_swing=("impact_swing", "mean"),
    )
    .reset_index()
)

player_summary["overall_kd"] = (
    player_summary["total_kills"] / player_summary["total_deaths"].clip(lower=1)
).round(2)
player_summary["kd_diff"] = player_summary["total_kills"] - player_summary["total_deaths"]
player_summary["avg_rating"] = player_summary["avg_rating"].round(2)
player_summary["avg_adr"] = player_summary["avg_adr"].round(1)
player_summary["avg_kast"] = player_summary["avg_kast"].round(1)
player_summary["avg_swing"] = player_summary["avg_swing"].round(2)

# Corte dos jogadores titulares (>= min_matches)
core_players = player_summary[player_summary["matches_played"] >= min_matches].copy()

# Se uma equipe especifica foi filtrada na barra lateral
if selected_team != "Todas as 6 Equipes":
    core_players = core_players[core_players["team_name"] == selected_team]
    team_maps_filtered = team_maps_filtered[team_maps_filtered["team_name"] == selected_team]

# ==============================================================================
# GUIA DE METRICAS (EXPANDER EXPLICATIVO PARA O RECRUTADOR)
# ==============================================================================
def render_metrics_guide():
    with st.expander("Entenda o significado das metricas exibidas neste painel"):
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown(
                """
                - **Rating (HLTV 2.0 / CS2)**: Indice padrao da industria que mede o desempenho geral do atleta.
                  - *1.00*: Desempenho medio/neutro.
                  - *1.15 ou mais*: Desempenho de alto impacto (nivel estrela).
                - **K/D Ratio**: Razao entre eliminacoes realizadas e mortes sofridas.
                  - *Acima de 1.00*: O jogador elimina mais do que morre.
                """
            )
        with col_g2:
            st.markdown(
                """
                - **ADR (Average Damage per Round)**: Media de dano causado por rodada jogada.
                  - *Acima de 80.0*: Jogador altamente agressivo e participativo nas trocas de dano.
                - **Impact Swing**: Metrica de impacto em rodadas chave (aberturas de rodada e clutches).
                """
            )


# ==============================================================================
# ABA 1: VISAO GERAL E LEADERBOARD
# ==============================================================================
if menu == "Visao Geral e Leaderboard":
    st.title("Visao Geral e Leaderboard de Titulares")
    st.markdown(
        f"Exibindo apenas atletas titulares com **{min_matches} ou mais partidas disputadas** "
        f"pertencentes as 6 equipes do estudo: *{', '.join(TOP_6_TEAMS)}*."
    )

    render_metrics_guide()

    # Cards Principais no Topo
    c1, c2, c3, c4 = st.columns(4)

    best_rating = (
        core_players.sort_values(by="avg_rating", ascending=False).iloc[0]
        if not core_players.empty
        else None
    )
    best_fragger = (
        core_players.sort_values(by="total_kills", ascending=False).iloc[0]
        if not core_players.empty
        else None
    )
    best_kd = (
        core_players.sort_values(by="overall_kd", ascending=False).iloc[0]
        if not core_players.empty
        else None
    )
    best_impact = (
        core_players.sort_values(by="avg_swing", ascending=False).iloc[0]
        if not core_players.empty
        else None
    )

    with c1:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-label">Maior Rating Medio</div>
                <div class="metric-number">{best_rating['player_name'] if best_rating is not None else 'N/A'}</div>
                <div class="metric-detail">{best_rating['avg_rating'] if best_rating is not None else 0} ({best_rating['team_name'] if best_rating is not None else ''})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-label">Mais Eliminacoes (Kills)</div>
                <div class="metric-number">{best_fragger['player_name'] if best_fragger is not None else 'N/A'}</div>
                <div class="metric-detail">{best_fragger['total_kills'] if best_fragger is not None else 0} kills ({best_fragger['team_name'] if best_fragger is not None else ''})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-label">Maior Eficiencia (K/D)</div>
                <div class="metric-number">{best_kd['player_name'] if best_kd is not None else 'N/A'}</div>
                <div class="metric-detail">{best_kd['overall_kd'] if best_kd is not None else 0} K/D ({best_kd['kd_diff']:+d} saldo)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-label">Maior Impacto por Round</div>
                <div class="metric-number">{best_impact['player_name'] if best_impact is not None else 'N/A'}</div>
                <div class="metric-detail">+{best_impact['avg_swing'] if best_impact is not None else 0} Impact Swing</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Graficos Diretos e Simples de Ler
    st.subheader("Comparativo dos Melhores Atletas")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("**Top 10 - Rating 2.0 Medio** (Quanto maior, melhor)")
        top_rating_chart = core_players.sort_values(by="avg_rating", ascending=True).tail(10)
        fig_r = px.bar(
            top_rating_chart,
            x="avg_rating",
            y="player_name",
            color="team_name",
            orientation="h",
            text="avg_rating",
            labels={"avg_rating": "Rating Medio", "player_name": "Jogador", "team_name": "Equipe"},
            template="plotly_dark",
        )
        fig_r.update_traces(textposition="outside", textfont_size=12)
        fig_r.update_layout(
            height=420,
            margin=dict(l=10, r=40, t=20, b=30),
            xaxis=dict(range=[0.8, 1.6], dtick=0.1),
            paper_bgcolor="#151C2C",
            plot_bgcolor="#151C2C",
        )
        st.plotly_chart(fig_r, use_container_width=True)

    with col_chart2:
        st.markdown("**Top 10 - Eficiencia K/D Ratio** (Acima de 1.0 = saldo positivo)")
        top_kd_chart = core_players.sort_values(by="overall_kd", ascending=True).tail(10)
        fig_k = px.bar(
            top_kd_chart,
            x="overall_kd",
            y="player_name",
            color="team_name",
            orientation="h",
            text="overall_kd",
            labels={"overall_kd": "K/D Ratio", "player_name": "Jogador", "team_name": "Equipe"},
            template="plotly_dark",
        )
        fig_k.update_traces(textposition="outside", textfont_size=12)
        fig_k.add_vline(x=1.0, line_dash="dash", line_color="#94A3B8", annotation_text="K/D 1.0")
        fig_k.update_layout(
            height=420,
            margin=dict(l=10, r=40, t=20, b=30),
            xaxis=dict(range=[0.7, 1.6], dtick=0.1),
            paper_bgcolor="#151C2C",
            plot_bgcolor="#151C2C",
        )
        st.plotly_chart(fig_k, use_container_width=True)

    # Tabela com dados consolidados
    st.subheader("Tabela de Desempenho Geral dos Titulares")
    table_cols = [
        "player_name",
        "team_name",
        "matches_played",
        "avg_rating",
        "overall_kd",
        "avg_adr",
        "avg_kast",
        "avg_swing",
        "total_kills",
        "total_deaths",
        "kd_diff",
    ]
    st.dataframe(
        core_players[table_cols]
        .rename(
            columns={
                "player_name": "Jogador",
                "team_name": "Equipe",
                "matches_played": "Partidas",
                "avg_rating": "Rating Medio",
                "overall_kd": "K/D Ratio",
                "avg_adr": "Dano Medio (ADR)",
                "avg_kast": "KAST (%)",
                "avg_swing": "Impact Swing",
                "total_kills": "Abates (K)",
                "total_deaths": "Mortes (D)",
                "kd_diff": "Saldo K-D",
            }
        )
        .sort_values(by="Rating Medio", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

# ==============================================================================
# ABA 2: ANALISE POR JOGADOR
# ==============================================================================
elif menu == "Analise por Jogador":
    st.title("Analise Individual do Atleta")
    st.markdown("Consulte os dados detalhados e a constancia de um jogador especifico do Top 6.")

    available_players = sorted(core_players["player_name"].unique().tolist())
    if not available_players:
        st.warning("Nenhum jogador disponivel com o filtro de partidas selecionado.")
        st.stop()

    selected_player = st.selectbox(
        "Selecione o Atleta:",
        options=available_players,
        index=available_players.index("donk") if "donk" in available_players else 0,
    )

    player_history = top6_players[top6_players["player_name"] == selected_player].sort_values(
        by="date", ascending=True
    )

    # Metricas individuais
    team_name = player_history["team_name"].iloc[-1]
    matches_count = player_history["match_id"].nunique()
    total_k = player_history["kills"].sum()
    total_d = player_history["deaths"].sum()
    kd = round(total_k / max(1, total_d), 2)
    rating = round(player_history["rating"].mean(), 2)
    adr = round(player_history["adr"].mean(), 1)
    kast = round(player_history["kast"].mean(), 1)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Rating Medio", f"{rating}")
    c2.metric("K/D Ratio", f"{kd}", delta=f"{total_k - total_d:+d} saldo")
    c3.metric("Dano Medio (ADR)", f"{adr}")
    c4.metric("Consistencia (KAST)", f"{kast}%")
    c5.metric("Total de Abates", f"{total_k}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Grafico de Linha Simples: Variacao de Rating
    st.subheader(f"Desempenho ao Longo do Tempo: {selected_player} ({team_name})")
    fig_line = px.line(
        player_history,
        x="date",
        y="rating",
        markers=True,
        labels={"date": "Data do Confronto", "rating": "Rating na Partida"},
        template="plotly_dark",
    )
    fig_line.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="#94A3B8",
        annotation_text="Media Neutra (1.00)",
    )
    fig_line.update_traces(line_color="#38BDF8", line_width=3, marker=dict(size=8, color="#FFFFFF"))
    fig_line.update_layout(
        height=380,
        margin=dict(l=10, r=20, t=30, b=30),
        paper_bgcolor="#151C2C",
        plot_bgcolor="#151C2C",
        yaxis=dict(range=[0.4, 2.2]),
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # Tabela com as ultimas partidas
    st.subheader("Ultimos Confrontos Disputados")
    st.dataframe(
        player_history[
            [
                "date",
                "event",
                "team_name",
                "kills",
                "deaths",
                "kd_ratio",
                "kd_diff",
                "rating",
                "adr",
                "kast",
                "impact_swing",
            ]
        ]
        .rename(
            columns={
                "date": "Data",
                "event": "Torneio",
                "team_name": "Equipe",
                "kills": "Kills",
                "deaths": "Deaths",
                "kd_ratio": "K/D",
                "kd_diff": "Saldo K-D",
                "rating": "Rating",
                "adr": "ADR",
                "kast": "KAST (%)",
                "impact_swing": "Impact",
            }
        )
        .sort_values(by="Data", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

# ==============================================================================
# ABA 3: DESEMPENHO POR MAPA (SOMENTE TOP 6)
# ==============================================================================
elif menu == "Desempenho por Mapa":
    st.title("Desempenho das Equipes por Mapa")
    st.markdown(
        f"Comparativo de taxa de vitoria (*Winrate*) e saldo de rodadas "
        f"exclusivamente entre as 6 equipes monitoradas: *{', '.join(TOP_6_TEAMS)}*."
    )

    # Agrupamento das 6 equipes por mapa
    map_stats = (
        team_maps_filtered.groupby(["map_name", "team_name"])
        .agg(
            matches_played=("match_id", "count"),
            matches_won=("is_winner", "sum"),
            avg_round_diff=("round_diff", "mean"),
        )
        .reset_index()
    )
    map_stats["matches_lost"] = map_stats["matches_played"] - map_stats["matches_won"]
    map_stats["winrate_pct"] = (
        (map_stats["matches_won"] / map_stats["matches_played"]) * 100
    ).round(1)
    map_stats["avg_round_diff"] = map_stats["avg_round_diff"].round(1)

    available_maps = sorted(map_stats["map_name"].unique().tolist())
    selected_map = st.selectbox("Selecione o Mapa para Analisar:", options=available_maps)

    # Filtrar mapa escolhido e ordenar por maior taxa de vitoria
    specific_map_df = map_stats[map_stats["map_name"] == selected_map].sort_values(
        by=["winrate_pct", "matches_played"], ascending=[False, False]
    )

    col_map1, col_map2 = st.columns([3, 2])

    with col_map1:
        st.markdown(f"**Taxa de Vitoria (%) no Mapa: {selected_map}**")
        fig_map_bar = px.bar(
            specific_map_df,
            x="team_name",
            y="winrate_pct",
            text="winrate_pct",
            labels={"team_name": "Equipe", "winrate_pct": "Winrate (%)"},
            template="plotly_dark",
            color="winrate_pct",
            color_continuous_scale=["#1E293B", "#38BDF8"],
        )
        fig_map_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_map_bar.update_layout(
            height=400,
            margin=dict(l=10, r=20, t=30, b=30),
            yaxis=dict(range=[0, 115]),
            paper_bgcolor="#151C2C",
            plot_bgcolor="#151C2C",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_map_bar, use_container_width=True)

    with col_map2:
        st.markdown(f"**Tabela do Mapa: {selected_map}**")
        st.dataframe(
            specific_map_df[
                ["team_name", "matches_played", "matches_won", "matches_lost", "winrate_pct", "avg_round_diff"]
            ].rename(
                columns={
                    "team_name": "Equipe",
                    "matches_played": "Jogos",
                    "matches_won": "Vitorias",
                    "matches_lost": "Derrotas",
                    "winrate_pct": "Winrate (%)",
                    "avg_round_diff": "Saldo Rounds/Jogo",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Matriz Geral de Winrate das 6 Equipes
    st.subheader("Matriz Geral de Winrate (%) em Todos os Mapas")
    st.caption("Visao panoramica para identificar mapas fortes e fracos de cada equipe.")
    pivot_maps = map_stats.pivot(index="team_name", columns="map_name", values="winrate_pct").fillna(0)

    fig_heatmap = px.imshow(
        pivot_maps,
        text_auto=".0f",
        color_continuous_scale="Blues",
        labels=dict(x="Mapa", y="Equipe", color="Winrate (%)"),
        template="plotly_dark",
    )
    fig_heatmap.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=30),
        paper_bgcolor="#151C2C",
        plot_bgcolor="#151C2C",
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

# ==============================================================================
# ABA 4: HISTORICO DE PARTIDAS
# ==============================================================================
elif menu == "Historico de Partidas":
    st.title("Historico de Partidas")
    st.markdown("Registro completo das series disputadas no dataset.")

    matches_display = matches_df.copy()
    if selected_team != "Todas as 6 Equipes":
        matches_display = matches_display[
            (matches_display["team1_name"] == selected_team)
            | (matches_display["team2_name"] == selected_team)
        ]

    st.dataframe(
        matches_display[
            [
                "date",
                "event",
                "best_of",
                "team1_name",
                "team1_score",
                "team2_score",
                "team2_name",
                "winner_name",
                "score_difference",
            ]
        ]
        .rename(
            columns={
                "date": "Data",
                "event": "Torneio",
                "best_of": "Formato",
                "team1_name": "Equipe 1",
                "team1_score": "Placar 1",
                "team2_score": "Placar 2",
                "team2_name": "Equipe 2",
                "winner_name": "Vencedor",
                "score_difference": "Margem",
            }
        )
        .sort_values(by="Data", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
