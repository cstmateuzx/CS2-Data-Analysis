import json
import requests


BASE_URL = "https://api.csapi.de"


def fetch_data(endpoint):
    url = f"{BASE_URL}{endpoint}"

    response = requests.get(url)
    response.raise_for_status()

    return response.json()


def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def main():
    team_id = 7020
    data = fetch_data(f"/teams/{team_id}/matchhistory?limit=20")

    save_json(
        data,
        "data/teams_json/teams.json"
    )


if __name__ == "__main__":
    main()