"""
Cruzamento ITBI × IPTU de Porto Alegre — camada de avaliação (AVM v1).

ITBI  = preço de venda real (só dos vendidos)   -> poa_baseline_*.csv
IPTU  = cadastro completo: valor venal + área + imposto (todos os imóveis)

Por bairro e por logradouro calcula:
  - venda real R$/m² (ITBI)  ·  venal R$/m² (IPTU)
  - PRÊMIO de mercado = venda / venal  (quanto o mercado paga acima do venal)
  - GIRO = nº vendas (ITBI) / nº imóveis (IPTU)  (liquidez)
  - IPTU mediano (custo de carrego)

Saídas: data/poa/poa_cross_bairro.csv + poa_cross_logradouro.csv
Run: python poa_cross.py   (lê iptu-2026.csv em streaming, ~220 MB)
"""
import csv
import statistics as st
import unicodedata
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "poa"
IPTU = DATA / "iptu-2026.csv"

# índices das colunas do IPTU (ver header: 32 colunas)
I_BAIRRO, I_LOGR, I_USO, I_FINAL, I_AREA, I_VENAL, I_IMPOSTO = 2, 7, 16, 17, 22, 26, 28

RESID = ("APARTAMENTO", "CASA", "RESIDENCIA")
EXCLUI = ("ESTACIONAMENTO", "GARAGEM", "COMERCIO", "SERVI", "SALA", "LOJA", "BOX", "NAO RESID")


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode().upper()
    return " ".join(s.replace("'", "").split())


def is_resid(final, uso):
    f = norm(final)
    if any(x in f for x in EXCLUI):
        return False
    if any(x in f for x in RESID):
        return True
    return norm(uso) == "EXCLUSIVAMENTE RESIDENCIAL"


def fnum(s):
    try:
        return float((s or "").replace("'", ""))
    except ValueError:
        return None


def load_iptu():
    venal_b, imp_b = defaultdict(list), defaultdict(list)
    venal_l = defaultdict(list)
    n = 0
    with IPTU.open(encoding="latin-1", newline="") as fh:
        r = csv.reader(fh, delimiter=";")
        next(r, None)
        for row in r:
            if len(row) <= I_IMPOSTO:
                continue
            if not is_resid(row[I_FINAL], row[I_USO]):
                continue
            area = fnum(row[I_AREA]); venal = fnum(row[I_VENAL]); imp = fnum(row[I_IMPOSTO])
            if not area or not venal or area < 25:
                continue
            rs = venal / area
            if rs < 500 or rs > 40000:
                continue
            b = norm(row[I_BAIRRO]); lg = row[I_LOGR].strip().strip("'")
            venal_b[b].append(rs)
            if imp:
                imp_b[b].append(imp)
            if lg:
                venal_l[(b, norm(lg))].append(rs)
            n += 1
    print(f"IPTU residencial processado: {n:,} imóveis".replace(",", "."))
    return venal_b, imp_b, venal_l


def load_itbi_bairro():
    d = {}
    f = DATA / "poa_baseline_bairro.csv"
    for r in csv.DictReader(f.open(encoding="utf-8-sig")):
        d[norm(r["bairro"])] = (int(r["rs_m2_mediana"]), int(r["n_transacoes"]))
    return d


def load_itbi_log():
    d = {}
    f = DATA / "poa_baseline_logradouro.csv"
    for r in csv.DictReader(f.open(encoding="utf-8-sig")):
        d[(norm(r["bairro"]), norm(r["logradouro"]))] = (int(r["rs_m2_mediana"]), int(r["n_transacoes"]))
    return d


def main():
    print("Lendo IPTU 2026 (streaming)...")
    venal_b, imp_b, venal_l = load_iptu()
    itbi_b = load_itbi_bairro()
    itbi_l = load_itbi_log()

    # bairro
    rows = []
    for b, vvals in venal_b.items():
        if len(vvals) < 30 or b not in itbi_b:
            continue
        venal_med = round(st.median(vvals))
        sale_med, n_vendas = itbi_b[b]
        n_imoveis = len(vvals)
        premio = round(sale_med / venal_med, 2) if venal_med else None
        giro = round(100 * n_vendas / n_imoveis, 1)
        iptu_med = round(st.median(imp_b[b])) if imp_b.get(b) else None
        rows.append({"bairro": b, "venda_itbi_rs_m2": sale_med, "venal_iptu_rs_m2": venal_med,
                     "premio_mercado": premio, "n_vendas": n_vendas, "n_imoveis": n_imoveis,
                     "giro_pct": giro, "iptu_anual_mediano": iptu_med})
    rows.sort(key=lambda x: -x["venda_itbi_rs_m2"])
    out_b = DATA / "poa_cross_bairro.csv"
    with out_b.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # logradouro (onde há ITBI e IPTU)
    lrows = []
    for key, vvals in venal_l.items():
        if len(vvals) < 5 or key not in itbi_l:
            continue
        venal_med = round(st.median(vvals)); sale_med, nv = itbi_l[key]
        lrows.append({"bairro": key[0], "logradouro": key[1], "venda_itbi_rs_m2": sale_med,
                      "venal_iptu_rs_m2": venal_med,
                      "premio_mercado": round(sale_med / venal_med, 2) if venal_med else None,
                      "n_vendas": nv, "n_imoveis_iptu": len(vvals)})
    lrows.sort(key=lambda x: (x["bairro"], -x["venda_itbi_rs_m2"]))
    out_l = DATA / "poa_cross_logradouro.csv"
    with out_l.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(lrows[0].keys()))
        w.writeheader()
        w.writerows(lrows)

    print(f"\nGravado: {out_b}\n         {out_l} ({len(lrows)} logradouros cruzados)")
    print("\n=== ITBI × IPTU por bairro (top por venda real) ===")
    print(f"{'bairro':22}{'venda/m²':>10}{'venal/m²':>10}{'prêmio':>8}{'giro%':>7}{'IPTU/ano':>10}")
    for r in rows[:18]:
        print(f"{r['bairro'][:22]:22}{r['venda_itbi_rs_m2']:>10,}{r['venal_iptu_rs_m2']:>10,}"
              f"{r['premio_mercado']:>8}{r['giro_pct']:>7}{(r['iptu_anual_mediano'] or 0):>10,}".replace(",", "."))


if __name__ == "__main__":
    main()
