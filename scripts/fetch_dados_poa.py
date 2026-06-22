"""
Baixa os dados abertos oficiais de Porto Alegre (ITBI + IPTU) para data/poa/.
Fonte: https://dadosabertos.poa.br  (API CKAN — sem chave, dado público).

Uso:  python fetch_dados_poa.py
Depois rode:  python poa_itbi.py   e   python poa_cross.py
"""
import urllib.request
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "poa"
DATA.mkdir(parents=True, exist_ok=True)
CKAN = "https://dadosabertos.poa.br/api/3/action/package_show?id="

# o que baixar: ITBI dos anos recentes + IPTU do ano mais recente (cadastro)
ITBI_ANOS = ["2023", "2024", "2025", "2026"]
IPTU_ANOS = ["2026"]   # cadastro atual (~220 MB); acrescente anos se quiser


def resources(dataset):
    with urllib.request.urlopen(CKAN + dataset, timeout=60) as r:
        return json.loads(r.read())["result"]["resources"]


def baixa(url, destino):
    if destino.exists():
        print(f"  (já existe) {destino.name}")
        return
    print(f"  baixando {destino.name} ...")
    urllib.request.urlretrieve(url, destino)
    mb = destino.stat().st_size / 1e6
    print(f"    ok ({mb:.1f} MB)")


def main():
    print("ITBI (transações reais):")
    for res in resources("itbi"):
        for ano in ITBI_ANOS:
            if res["format"] == "CSV" and ano in res["name"]:
                baixa(res["url"], DATA / f"itbi-{ano}.csv")
    print("IPTU (cadastro + valor venal):")
    for res in resources("iptu"):
        for ano in IPTU_ANOS:
            if res["format"] == "CSV" and ano in res["name"]:
                baixa(res["url"], DATA / f"iptu-{ano}.csv")
    print("\nPronto. Agora rode:  python poa_itbi.py   e   python poa_cross.py")


if __name__ == "__main__":
    main()
