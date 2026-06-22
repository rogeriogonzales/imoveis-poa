"""
Monta o site 'imoveis-poa': index.html interativo (cruzamento ITBI×IPTU),
copia os scripts + CSVs e gera o pacote .zip para download.

Run: python build_poa_site.py   (após poa_itbi.py + poa_cross.py)
"""
import csv
import json
import shutil
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "poa"
SITE = ROOT / "poa-site"
SCRIPTS = ROOT / "scripts"


def read(name):
    f = DATA / name
    return list(csv.DictReader(f.open(encoding="utf-8-sig"))) if f.exists() else []


def main():
    (SITE / "dados").mkdir(parents=True, exist_ok=True)
    (SITE / "scripts").mkdir(parents=True, exist_ok=True)

    # copia CSVs computados + scripts
    for n in ["poa_cross_bairro.csv", "poa_cross_logradouro.csv",
              "poa_baseline_bairro.csv", "poa_baseline_logradouro.csv"]:
        if (DATA / n).exists():
            shutil.copy(DATA / n, SITE / "dados" / n)
    for n in ["poa_itbi.py", "poa_cross.py", "build_poa_site.py"]:
        if (SCRIPTS / n).exists():
            shutil.copy(SCRIPTS / n, SITE / "scripts" / n)

    bairro = read("poa_cross_bairro.csv")
    log = read("poa_cross_logradouro.csv")

    def num(r, k):
        try:
            return float(r.get(k) or 0)
        except ValueError:
            return 0
    n_vendas = sum(int(num(r, "n_vendas")) for r in bairro)
    n_imoveis = sum(int(num(r, "n_imoveis")) for r in bairro)

    bdata = [{"b": r["bairro"], "venda": int(num(r, "venda_itbi_rs_m2")),
              "venal": int(num(r, "venal_iptu_rs_m2")), "premio": num(r, "premio_mercado"),
              "giro": num(r, "giro_pct"), "iptu": int(num(r, "iptu_anual_mediano"))} for r in bairro]
    ldata = [{"b": r["bairro"], "l": r["logradouro"], "venda": int(num(r, "venda_itbi_rs_m2")),
              "venal": int(num(r, "venal_iptu_rs_m2")), "premio": num(r, "premio_mercado"),
              "nv": int(num(r, "n_vendas"))} for r in log]

    html = TEMPLATE.replace("__BDATA__", json.dumps(bdata, ensure_ascii=False)) \
                   .replace("__LDATA__", json.dumps(ldata, ensure_ascii=False)) \
                   .replace("__NVENDAS__", f"{n_vendas:,}".replace(",", ".")) \
                   .replace("__NIMOVEIS__", f"{n_imoveis:,}".replace(",", ".")) \
                   .replace("__NBAIRROS__", str(len(bdata))) \
                   .replace("__NLOG__", f"{len(ldata):,}".replace(",", ".")) \
                   .replace("__DATA__", date.today().isoformat())
    (SITE / "index.html").write_text(html, encoding="utf-8")

    # pacote zip (scripts + dados + README)
    zpath = SITE / "pacote-poa-itbi-iptu.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in (SITE / "scripts").glob("*.py"):
            z.write(p, f"scripts/{p.name}")
        for p in (SITE / "dados").glob("*.csv"):
            z.write(p, f"dados/{p.name}")
        if (SITE / "README.md").exists():
            z.write(SITE / "README.md", "README.md")
        if (ROOT / "poa-site" / "scripts" / "fetch_dados_poa.py").exists():
            pass  # já incluído no glob acima
    print(f"Site gerado: {SITE / 'index.html'}")
    print(f"  bairros: {len(bdata)} | logradouros: {len(ldata)} | pacote: {zpath.name}")


TEMPLATE = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Imóveis POA — avaliação por ITBI × IPTU</title>
<style>
:root{--bg:#0f1115;--card:#191c23;--mut:#8a93a6;--line:#262b36;--pos:#34d399;--acc:#60a5fa;--warn:#f4a460}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#e6e9ef;font:15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:0 20px}
header{padding:46px 0 24px;border-bottom:1px solid var(--line)}
h1{font-size:28px;margin:0 0 8px;letter-spacing:-.02em}
.sub{color:var(--mut);font-size:16px;margin:0;max-width:720px}
.kpis{display:flex;gap:26px;margin-top:18px;flex-wrap:wrap}.kpi b{font-size:24px;color:var(--acc);display:block}.kpi span{color:var(--mut);font-size:12px}
section{padding:30px 0;border-bottom:1px solid var(--line)}h2{font-size:20px;margin:0 0 12px}h3{font-size:15px;margin:0 0 4px}
p{color:#d6dbe4;margin:0 0 12px}.mut{color:var(--mut)}
.callout{background:linear-gradient(180deg,#16261f,#12151c);border:1px solid #234436;border-radius:12px;padding:16px 18px;margin:6px 0}.callout b{color:var(--pos)}
.tools{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
input,select{background:var(--card);border:1px solid var(--line);color:#e6e9ef;border-radius:8px;padding:8px 10px;font-size:14px}
input{min-width:240px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:right;padding:7px 10px;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}th{color:var(--mut);font-weight:600;cursor:pointer;user-select:none;white-space:nowrap}
th:hover{color:#e6e9ef}.premio{color:var(--pos);font-weight:700}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:680px){.cards{grid-template-columns:1fr}}
.box{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}.box .k{color:var(--acc);font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
ul{margin:6px 0 12px;padding-left:20px}li{margin:5px 0;color:#d6dbe4}
.dl{display:flex;gap:12px;flex-wrap:wrap}
.btn{background:#1a2230;border:1px solid var(--acc);color:var(--acc);padding:10px 14px;border-radius:9px;text-decoration:none;font-size:14px;font-weight:600}
.btn.big{background:var(--acc);color:#06131f}
.foot{padding:26px 0 60px;color:var(--mut);font-size:13px}a{color:var(--acc)}
.scroll{overflow-x:auto}
</style></head><body><div class="wrap">

<header>
  <h1>Imóveis POA — avaliação por ITBI × IPTU</h1>
  <p class="sub">Avaliação de imóveis em Porto Alegre a partir de <b>dados oficiais abertos</b>: cruza o preço de <b>venda real</b> (ITBI) com o <b>cadastro completo</b> da cidade (IPTU) — para qualquer imóvel, vendido ou não.</p>
  <div class="kpis">
    <div class="kpi"><b>__NVENDAS__</b><span>vendas reais (ITBI 2023-26)</span></div>
    <div class="kpi"><b>__NIMOVEIS__</b><span>imóveis no cadastro (IPTU)</span></div>
    <div class="kpi"><b>__NBAIRROS__</b><span>bairros</span></div>
    <div class="kpi"><b>__NLOG__</b><span>logradouros cruzados</span></div>
  </div>
</header>

<section>
  <h2>O que faz</h2>
  <p>O <b>ITBI</b> mostra por quanto imóveis foram <i>de fato vendidos</i> — mas só dos que venderam. O <b>IPTU</b> tem o <i>valor venal e as características de todos os imóveis</i> da cidade. Cruzando os dois, para cada bairro e rua sai:</p>
  <div class="callout"><b>Prêmio de mercado</b> = venda real ÷ valor venal. É o multiplicador que transforma o valor venal de <b>qualquer</b> imóvel (que está no carnê do IPTU) em <b>valor de mercado estimado</b>. Mais o <b>giro</b> (liquidez) e o <b>IPTU/ano</b> (custo de carrego).</div>
</section>

<section>
  <h2>Cruzamento por bairro</h2>
  <div class="tools">
    <input id="fb" placeholder="filtrar bairro...">
    <span class="mut" id="bcount"></span>
  </div>
  <div class="scroll"><table id="tb">
    <thead><tr>
      <th data-k="b">Bairro</th><th data-k="venda">Venda real R$/m²</th><th data-k="venal">Venal R$/m²</th>
      <th data-k="premio">Prêmio</th><th data-k="giro">Giro %</th><th data-k="iptu">IPTU/ano</th>
    </tr></thead><tbody></tbody>
  </table></div>
  <p class="mut" style="margin-top:8px;font-size:13px">Clique no cabeçalho para ordenar. O prêmio é mais confiável dentro de áreas de padrão parecido — em bairros muito periféricos o venal defasado infla o número.</p>
</section>

<section>
  <h2>Buscar por rua (comparável fino)</h2>
  <div class="tools"><input id="fl" placeholder="digite uma rua (ex.: Felix da Cunha)..."><span class="mut" id="lcount"></span></div>
  <div class="scroll"><table id="tl">
    <thead><tr><th>Bairro</th><th>Logradouro</th><th>Venda R$/m²</th><th>Venal R$/m²</th><th>Prêmio</th><th>Vendas</th></tr></thead>
    <tbody></tbody>
  </table></div>
</section>

<section>
  <h2>Como usar</h2>
  <div class="cards">
    <div class="box"><div class="k">Avaliar um imóvel</div><p class="mut" style="margin:6px 0 0">Pegue o valor venal (carnê do IPTU) e multiplique pelo <b>prêmio</b> do bairro. Ex.: venal R$ 600 mil em Moinhos (prêmio 1,71×) → <b>~R$ 1,03 mi</b>.</p></div>
    <div class="box"><div class="k">Conferir um anúncio</div><p class="mut" style="margin:6px 0 0">Compare o R$/m² pedido com a <b>venda real</b> da rua/bairro. Acima = caro; abaixo = oportunidade.</p></div>
    <div class="box"><div class="k">Negociar</div><p class="mut" style="margin:6px 0 0">Prêmio e giro são argumento objetivo: "nesta rua o mercado paga X e gira Y% ao ano".</p></div>
    <div class="box"><div class="k">Rodar você mesmo</div><p class="mut" style="margin:6px 0 0">Baixe o pacote abaixo e rode os 3 scripts Python — atualiza com dado novo quando quiser.</p></div>
  </div>
</section>

<section>
  <h2>O valor que gera</h2>
  <ul>
    <li><b>Avaliação ancorada em transação real + cadastro oficial</b> — não em opinião de portal.</li>
    <li><b>Garimpo de subavaliados</b> — quem está abaixo da venda real da região.</li>
    <li><b>Validação de anúncio</b> — área/uso/ano oficiais do IPTU pegam metragem inflada.</li>
    <li><b>Liquidez e custo de carrego</b> entram na conta da decisão.</li>
  </ul>
</section>

<section>
  <h2>Baixar para mexer na sua máquina</h2>
  <p class="mut">Pacote com os scripts (Python) + os dados já processados + instruções. Requer Python 3. Passo a passo no README.</p>
  <div class="dl">
    <a class="btn big" href="pacote-poa-itbi-iptu.zip" download>⬇ Baixar pacote completo (.zip)</a>
    <a class="btn" href="dados/poa_cross_bairro.csv" download>CSV por bairro</a>
    <a class="btn" href="dados/poa_cross_logradouro.csv" download>CSV por logradouro</a>
    <a class="btn" href="README.md" target="_blank">README</a>
  </div>
</section>

<div class="foot">
  <p>Atualizado __DATA__ · Fontes: <a href="https://dadosabertos.poa.br/dataset/itbi" target="_blank">ITBI</a> e <a href="https://dadosabertos.poa.br/dataset/iptu" target="_blank">IPTU</a> — dados abertos da Prefeitura de Porto Alegre.</p>
  <p class="mut">Bases fiscais (ITBI/IPTU) tendem a ser piso conservador do mercado; o prêmio corrige por região.</p>
</div>

</div>
<script>
const BD=__BDATA__, LD=__LDATA__;
const fmt=n=>n?n.toLocaleString('pt-BR'):'—';
let bsort={k:'venda',dir:-1};
function renderB(){
  const q=document.getElementById('fb').value.toLowerCase();
  let rows=BD.filter(r=>r.b.toLowerCase().includes(q));
  rows.sort((a,b)=>{const x=a[bsort.k],y=b[bsort.k];return (x>y?1:x<y?-1:0)*bsort.dir});
  document.querySelector('#tb tbody').innerHTML=rows.map(r=>
    `<tr><td>${r.b}</td><td>${fmt(r.venda)}</td><td>${fmt(r.venal)}</td><td class="premio">${r.premio.toFixed(2)}×</td><td>${r.giro}%</td><td>${fmt(r.iptu)}</td></tr>`).join('');
  document.getElementById('bcount').textContent=rows.length+' bairros';
}
document.querySelectorAll('#tb th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;bsort.dir=(bsort.k===k)?-bsort.dir:-1;bsort.k=k;renderB();});
document.getElementById('fb').oninput=renderB;
function renderL(){
  const q=document.getElementById('fl').value.toLowerCase();
  if(q.length<2){document.querySelector('#tl tbody').innerHTML='';document.getElementById('lcount').textContent='digite ao menos 2 letras';return;}
  let rows=LD.filter(r=>r.l.toLowerCase().includes(q)||r.b.toLowerCase().includes(q)).slice(0,80);
  document.querySelector('#tl tbody').innerHTML=rows.map(r=>
    `<tr><td>${r.b}</td><td>${r.l}</td><td>${fmt(r.venda)}</td><td>${fmt(r.venal)}</td><td class="premio">${r.premio.toFixed(2)}×</td><td>${r.nv}</td></tr>`).join('');
  document.getElementById('lcount').textContent=rows.length+(rows.length>=80?'+ (refine)':'')+' ruas';
}
document.getElementById('fl').oninput=renderL;
renderB();renderL();
</script>
</body></html>"""


if __name__ == "__main__":
    main()
