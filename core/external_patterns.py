import os
import json
import urllib.request
import urllib.error

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)

# A sample URL hosting global patterns. Can be replaced with a live gist or API.
EXTERNAL_URL = "https://raw.githubusercontent.com/antigravity-ai/pdv-market-patterns/main/external_patterns.json"
FALLBACK_PATH = os.path.join(PROJECT_ROOT, "data", "external_patterns_fallback.json")
CACHE_PATH = os.path.join(PROJECT_ROOT, "data", "external_patterns_cache.json")

def fetch_external_patterns(url=EXTERNAL_URL, timeout=3):
    """
    Fetches hardware store shopping patterns from the internet.
    Caches them locally on success. On failure, loads from cache or fallback file.
    
    Returns a list of association rules:
    [
      {
        "antecedents": ["4001", "4003"],
        "consequent": "4002",
        "confidence": 0.90,
        "support": 0.12,
        "lift": 5.4,
        "description": "..."
      },
      ...
    ]
    """
    # 1. Attempt to fetch from internet
    try:
        print(f"Tentando obter padrões de compra externos de: {url}")
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'PdvApp-Portfolio-Client/1.0'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Save to cache
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as cache_file:
                json.dump(data, cache_file, indent=2, ensure_ascii=False)
            
            print("Padrões externos atualizados e cacheados com sucesso.")
            return data
            
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"Aviso: Não foi possível obter padrões externos da internet: {e}")
        
    # 2. Try loading from cache
    if os.path.exists(CACHE_PATH):
        try:
            print("Carregando padrões externos a partir do cache local...")
            with open(CACHE_PATH, "r", encoding="utf-8") as cache_file:
                return json.load(cache_file)
        except Exception as cache_err:
            print(f"Erro ao ler cache de padrões: {cache_err}")
            
    # 3. Fallback to pre-packaged data
    print("Carregando padrões externos a partir do arquivo fallback pré-embalado...")
    try:
        with open(FALLBACK_PATH, "r", encoding="utf-8") as fallback_file:
            return json.load(fallback_file)
    except Exception as fallback_err:
        print(f"Erro crítico: Não foi possível carregar nem o fallback de padrões externos: {fallback_err}")
        return []

if __name__ == "__main__":
    # Test the loader
    rules = fetch_external_patterns(timeout=2)
    print(f"Total de regras externas carregadas: {len(rules)}")
    for r in rules[:2]:
        print(f"Regra: {r.get('antecedents')} -> {r.get('consequent')} (Confiança: {r.get('confidence')})")
