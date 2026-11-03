import json
import time
from pathlib import Path
import requests


API_KEY = "w7IiUkBZqpzEACRemhuhS4JqzbmI3s0FzFc0fHrd"
URL = "https://api.nasa.gov/neo/rest/v1/neo/browse"
RAW_DIR = Path("data/raw")


def fetch_all(start=0, end=5): #teste inicial para os primeiros 5, mudar em fetch_all no fundo da pagina
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for page in range(start, end):
        path = RAW_DIR / f"page_{page:04d}.json" # gerar nome de pagina page com 0000 e auto numera

        if path.exists(): # se a pagina ja existe, passa a frente ate onde pode continuar a ir buscar os dados
            continue

        for attempt in range(5):
            try:
                r = requests.get(URL, params={"api_key": API_KEY, "page": page}, timeout=30) # construir url e espera por pedido antes de retrt
                r.raise_for_status()
                break
            except requests.RequestException as e:
                rate_limited = (
                    isinstance(e, requests.HTTPError) and e.response.status_code == 429 # api atingiu limite entao espera regenerar pedidos
                )
                wait = 3600 if rate_limited else 10
                print(f"page {page} failed ({e}), waiting {wait}s")
                time.sleep(wait)
        else:
            print(f"pagina falhou: {page}") # avisa que pedir pagina x falhou
            continue

        path.write_text(json.dumps(r.json())) # escrever o ficheiro num json dict

        remaining = int(r.headers.get("X-RateLimit-Remaining", 9999)) # mantem conta do limite de pedidos, feature da api
        print(f"page {page}/{end - 1} saved, {remaining} requests left")

        if remaining < 50: # para quando chega a menos de 50
            print("api limit, wait 1 hour")
            time.sleep(3600)

        time.sleep(0.1)


if __name__ == "__main__":
    fetch_all(0, 3150)