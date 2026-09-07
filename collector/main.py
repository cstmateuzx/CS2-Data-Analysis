import json
import requests


BASE_URL = "https://api.csapi.de"
teams = {
    7020: "spirit",
    4494: "mouz",
    11283: "falcons",
    13286: "fut",
    9565: "vitality",
    8297: "furia"
}

def fetch_data(endpoint):
    url = f"{BASE_URL}{endpoint}"

    response = requests.get(url)
    response.raise_for_status()

    return response.json()


def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def main():
    for team_id, team_name in teams.items():

        data = fetch_data(
            f"/teams/{team_id}/matchhistory?limit=20"
        )

        save_json(
            data,
            f"data/raw/{team_name}.json"
        )

if __name__ == "__main__":
    main()
