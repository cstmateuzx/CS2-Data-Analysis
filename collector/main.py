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
    data = fetch_data("/matches/latest")

    save_json(
        data,
        "data/raw/response.json"
    )


if __name__ == "__main__":
    main()