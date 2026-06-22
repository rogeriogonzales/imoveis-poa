"""
Baseline de venda real (ITBI) de PORTO ALEGRE — dado aberto da Prefeitura.
Fonte: dadosabertos.poa.br/dataset/itbi (CSV por ano; delimitador ';', decimal '.').

Lê os CSVs em data/poa/, calcula R$/m² = base_de_calculo / area_constr_privativa
para imóveis RESIDENCIAIS, e agrega mediana por bairro e por logradouro.

Saídas: data/poa/poa_baseline_bairro.csv  +  data/poa/poa_baseline_logradouro.csv
Run: python poa_itbi.py
"""
import csv
import glob
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "poa"
ANOS = ["2023", "2024", "2025", "2026"]   # recência (como o 2021+ do Rio)

# finalidade_construcao: moradia (exclui vaga de garagem, comércio, sala)
RESID = ("APARTAMENTO", "CASA", "RESIDENCIA")
EXCLUI = ("ESTACIONAMENTO", "GARAGEM", "COMERCIO", "SALA", "NAO RESIDENCIAL", "LOJA", "BOX")
MIN_AREA = 25
RS_MIN, RS_MAX = 1500, 60000   # R$/m² plausível em POA


def is_resid(fin):
    f = (fin or "").upper()
    if any(x in f for x in EXCLUI):
        return False
    return any(s in f for s in RESID)


def unq(s):
    return (s or "").strip().strip("'").strip()


def load_rows():
    rows = []
    for ano in ANOS:
        f = DATA / f"itbi-{ano}.csv"
        if not f.exists():
            continue
        with f.open(encoding="latin-1", newline="") as fh:
            r = csv.DictReader(fh, delimiter=";")
            for d in r:
                d = {k.strip().strip("'"): unq(v) for k, v in d.items()
                     if k and isinstance(v, str)}
                rows.append(d)
    return rows


def fnum(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def main():
    rows = load_rows()
    print(f"Linhas lidas ({'/'.join(ANOS)}): {len(rows):,}".replace(",", "."))

    fin = Counter(r.get("finalidade_construcao", "") for r in rows)
    print("\nTop finalidades (p/ conferir o filtro residencial):")
    for k, v in fin.most_common(10):
        print(f"  {v:>7,}  {k}".replace(",", "."))

    by_bairro = defaultdict(list)
    by_log = defaultdict(list)
    n_ok = 0
    for r in rows:
        if not is_resid(r.get("finalidade_construcao")):
            continue
        base = fnum(r.get("base_de_calculo"))
        area = fnum(r.get("area_constr_privativa"))
        perc = fnum(r.get("perc_transmitido")) or 100
        if not base or not area or area < MIN_AREA or perc < 100:
            continue
        rs = base / area
        if rs < RS_MIN or rs > RS_MAX:
            continue
        bairro = (r.get("bairro") or "").strip()
        log = (r.get("logradouro") or "").strip()
        by_bairro[bairro].append(rs)
        if log:
            by_log[(bairro, log)].append(rs)
        n_ok += 1
    print(f"\nTransações residenciais válidas: {n_ok:,}".replace(",", "."))

    # bairro
    out_b = DATA / "poa_baseline_bairro.csv"
    with out_b.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["bairro", "n_transacoes", "rs_m2_mediana", "rs_m2_p25", "rs_m2_p75"])
        for b, vals in sorted(by_bairro.items(), key=lambda x: -st.median(x[1])):
            if len(vals) < 5:
                continue
            vals.sort()
            w.writerow([b, len(vals), round(st.median(vals)),
                        round(vals[int(.25*(len(vals)-1))]), round(vals[int(.75*(len(vals)-1))])])
    # logradouro
    out_l = DATA / "poa_baseline_logradouro.csv"
    with out_l.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["bairro", "logradouro", "n_transacoes", "rs_m2_mediana"])
        for (b, lg), vals in sorted(by_log.items()):
            if len(vals) < 3:
                continue
            w.writerow([b, lg, len(vals), round(st.median(vals))])

    print(f"\nGravado: {out_b}\n         {out_l}")
    print("\n=== TOP 15 bairros por R$/m² real (mediana, residencial) ===")
    print(f"{'bairro':28} {'n':>6} {'mediana':>10} {'p25':>9} {'p75':>9}")
    ranked = [(b, v) for b, v in by_bairro.items() if len(v) >= 20]
    for b, vals in sorted(ranked, key=lambda x: -st.median(x[1]))[:15]:
        vals.sort()
        med = round(st.median(vals))
        p25 = round(vals[int(.25*(len(vals)-1))]); p75 = round(vals[int(.75*(len(vals)-1))])
        print(f"{b[:28]:28} {len(vals):>6} {med:>10,} {p25:>9,} {p75:>9,}".replace(",", "."))


if __name__ == "__main__":
    main()
