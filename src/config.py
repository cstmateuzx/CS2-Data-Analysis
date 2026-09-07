"""
Módulo de configurações e constantes do projeto CS2 Data Analysis.
Centraliza caminhos de arquivos e parâmetros da API para evitar caminhos relativos frágeis.
"""

from pathlib import Path

# Raiz do projeto (CS2 Data Analysis)
BASE_DIR = Path(__file__).resolve().parent.parent

# Diretórios de Dados principais
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
MATCHES_STATS_DIR = RAW_DATA_DIR / "matches_stats"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Diretórios legados (para manter compatibilidade retroativa)
LEGACY_RAW_DIR = BASE_DIR / "collector" / "data" / "raw"
LEGACY_PROCESSED_DIR = BASE_DIR / "collector" / "processed"

# Configurações da API de CS2
BASE_API_URL = "https://api.csapi.de"
REQUEST_TIMEOUT = 15  # segundos

# Mapeamento de Equipes (ID: Nome do arquivo)
TEAMS = {
    7020: "spirit",
    4494: "mouz",
    11283: "falcons",
    13286: "fut",
    9565: "vitality",
    8297: "furia",
}

DEFAULT_MATCH_LIMIT = 20
