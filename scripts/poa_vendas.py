"""
Vendas individuais ENRIQUECIDAS por logradouro (para o popup do site).

ITBI (cada venda) + JOIN com IPTU por endereço (logradouro+número+unidade):
  ITBI -> número, unidade, complemento, tipo, ano, área, valor, R$/m², data, matrícula, CEP
  IPTU -> pavimento, uso, valor venal, IPTU/ano  (+ prêmio = valor/venal da unidade)

Saída: data/poa/poa_vendas_logradouro.json  (consumido por build_poa_site.py)
Run: python poa_vendas.py   (lê ITBI 2023-2026 + IPTU 2026 em streaming)
"""
import csv
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "poa"


def slug(b):
    return re.sub(r"[^a-z0-9]+", "-", b.lower()).strip("-")
ITBI_ANOS = ["2023", "2024", "2025", "2026"]
IPTU = DATA / "iptu-2026.csv"

# IPTU índices de coluna
P_LOG, P_NUM, P_UNI, P_PAV, P_USO, P_AREA, P_VENAL, P_IMP = 7, 10, 12, 13, 16, 22, 26, 28

RESID = ("APARTAMENTO", "CASA", "RESIDENCIA")
EXCLUI = ("ESTACIONAMENTO", "GARAGEM", "COMERCIO", "SERVI", "SALA", "LOJA", "BOX", "NAO RESID")
MIN_AREA, RS_MIN, RS_MAX = 25, 1500, 60000


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode().upper()
    return " ".join(s.replace("'", "").split())


def unq(s):
    return (s or "").strip().strip("'").strip()


def fnum(s):
    try:
        return float(unq(s))
    except ValueError:
        return None


def is_resid(final):
    f = norm(final)
    if any(x in f for x in EXCLUI):
        return False
    return any(x in f for x in RESID)


def build_iptu_index():
    """(log_norm, numero, unidade) -> [pavimento, uso, venal, imposto]."""
    idx = {}
    n = 0
    with IPTU.open(encoding="latin-1", newline="") as fh:
        r = csv.reader(fh, delimiter=";")
        next(r, None)
        for row in r:
            if len(row) <= P_IMP:
                continue
            key = (norm(row[P_LOG]), unq(row[P_NUM]), unq(row[P_UNI]))
            venal = fnum(row[P_VENAL]); imp = fnum(row[P_IMP])
            idx[key] = [unq(row[P_PAV]) or None, unq(row[P_USO]) or None,
                        round(venal) if venal else None, round(imp) if imp else None]
            n += 1
    print(f"IPTU indexado: {n:,} imóveis".replace(",", "."))
    return idx


def main():
    print("Indexando IPTU 2026 (streaming)...")
    iptu = build_iptu_index()

    vendas = defaultdict(list)
    n = 0
    for ano in ITBI_ANOS:
        f = DATA / f"itbi-{ano}.csv"
        if not f.exists():
            continue
        with f.open(encoding="latin-1", newline="") as fh:
            for d in csv.DictReader(fh, delimiter=";"):
                d = {k.strip().strip("'"): unq(v) for k, v in d.items() if k and isinstance(v, str)}
                if not is_resid(d.get("finalidade_construcao")):
                    continue
                base = fnum(d.get("base_de_calculo")); area = fnum(d.get("area_constr_privativa"))
                perc = fnum(d.get("perc_transmitido")) or 100
                if not base or not area or area < MIN_AREA or perc < 100:
                    continue
                rs = base / area
                if rs < RS_MIN or rs > RS_MAX:
                    continue
                log = d.get("logradouro", ""); num = d.get("n_endereco", ""); uni = d.get("n_unidade", "")
                lg = norm(log)
                # join IPTU: tenta (log,num,unidade) e cai p/ (log,num,'')
                hit = iptu.get((lg, num, uni)) or iptu.get((lg, num, "")) or [None, None, None, None]
                pav, uso, venal, imp = hit
                premio = round(base / venal, 2) if venal else None
                rec = [num, uni, d.get("complemento_endereco", ""), d.get("finalidade_construcao", ""),
                       d.get("ano_construcao", ""), round(area), round(base), round(rs),
                       d.get("data_pagamento", "")[:10], d.get("n_matricula_reg_imoveis", ""),
                       d.get("cep", ""), pav, uso, venal, imp, premio]
                vendas[(norm(d.get("bairro", "")), lg)].append(rec)
                n += 1
    print(f"Vendas enriquecidas: {n:,}".replace(",", "."))
    matched = sum(1 for arr in vendas.values() for r in arr if r[13])  # tem venal
    print(f"  com match no IPTU (venal/pavimento): {matched:,} ({round(100*matched/n)}%)".replace(",", "."))

    # fatia por bairro: data/poa/vendas/<slug>.json = {logradouro_norm: [vendas]}
    outdir = DATA / "vendas"
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    by_bairro = defaultdict(dict)
    for (bairro, lg), arr in vendas.items():
        if len(arr) >= 3:
            by_bairro[bairro][lg] = arr
    for bairro, logs in by_bairro.items():
        if not slug(bairro):   # bairro em branco -> ignora
            continue
        (outdir / f"{slug(bairro)}.json").write_text(
            json.dumps(logs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tot = sum(p.stat().st_size for p in outdir.glob("*.json"))
    print(f"Gravado: {outdir} ({len(by_bairro)} bairros, total {round(tot/1e6,1)} MB)")


if __name__ == "__main__":
    main()
