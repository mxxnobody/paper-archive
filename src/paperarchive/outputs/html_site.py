"""HTML 브라우징 아카이브 — 누적 JSON 저장 + 단일 페이지 정렬/검색 사이트.

site/data.json 에 모든 엔트리를 누적(key로 dedup)하고, site/index.html을
클라이언트 사이드 정렬·검색·한↔영 토글이 가능한 단일 페이지로 렌더한다.
GitHub Pages로 site/ 디렉토리를 그대로 배포한다.
"""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template

from ..record import Entry
from ..tiers import assign_tiers

DATA_FILE = "data.json"
INDEX_FILE = "index.html"
WEEKLY_DIR = "weekly"


def load_store(site_dir: Path) -> list[dict]:
    f = site_dir / DATA_FILE
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8"))


def merge(store: list[dict], entries: list[Entry]) -> list[dict]:
    """key 기준 dedup 병합 — 신규는 추가, 기존은 갱신."""
    by_key = {}
    for d in store:
        by_key[d.get("_key") or (f"doi:{d.get('doi')}" if d.get("doi") else "title:" + d["title"])] = d
    for e in entries:
        d = e.to_dict()
        d["_key"] = e.paper.key()
        by_key[d["_key"]] = d
    merged = list(by_key.values())
    merged.sort(key=lambda d: (d.get("relevance", 0), d.get("year") or 0), reverse=True)
    return merged


def save_store(site_dir: Path, store: list[dict]) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / DATA_FILE).write_text(
        json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8"
    )


_CSS = r"""
  :root { --bg:#0f1115; --card:#1a1d24; --fg:#e7e9ee; --mut:#9aa3b2; --acc:#5b9dff; --line:#2a2e38; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.6 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif; }
  header { padding:24px 20px; border-bottom:1px solid var(--line); position:sticky; top:0; background:var(--bg); z-index:5; }
  h1 { margin:0 0 4px; font-size:20px; }
  .meta { color:var(--mut); font-size:13px; }
  .meta a { color:var(--acc); }
  .controls { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
  input,select,button { background:var(--card); color:var(--fg); border:1px solid var(--line); border-radius:8px; padding:8px 10px; font-size:14px; }
  input#q { flex:1; min-width:180px; }
  main { padding:16px 20px 60px; max-width:980px; margin:0 auto; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px 18px; margin-bottom:14px; }
  .card h2 { margin:0 0 6px; font-size:16px; }
  .row { color:var(--mut); font-size:13px; margin-bottom:8px; }
  .badge { display:inline-block; background:#243; color:#9f9; border-radius:6px; padding:1px 7px; font-size:12px; margin-left:6px; }
  .canon { background:#432; color:#fc9; }
  .t1 { background:#5a4500; color:#ffd87a; } .t2 { background:#1d3a5f; color:#9cc2ff; } .t3 { background:#2a2e38; color:#9aa3b2; }
  .kv { margin:4px 0; }
  .kv b { color:var(--acc); }
  .caveat { color:#f4b860; } .caveat b { color:#f4b860; }
  .en { display:none; color:var(--mut); font-size:14px; border-left:2px solid var(--line); padding-left:10px; margin-top:8px; }
  body.show-en .en { display:block; }
  a { color:var(--acc); text-decoration:none; }
  .count { color:var(--mut); font-size:13px; margin:6px 0 14px; }
"""

# 카드 렌더 + 공통 헬퍼 (메인·주간 페이지 공유)
_CARD_JS = r"""
function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function tierBadge(d){
  if(d.tier==='F') return '<span class="badge canon">Foundational</span>';
  if(d.tier) return `<span class="badge t${d.tier}">Tier ${d.tier}</span>`;
  return '';
}
function cardHtml(d){
  const su = d.summary||{};
  const authors = (d.authors||[]).slice(0,4).join(', ') + ((d.authors||[]).length>4?' 외':'');
  return `<div class="card">
    <h2>${esc(d.title)} ${tierBadge(d)}<span class="badge">관련도 ${d.relevance||0}</span></h2>
    <div class="row">${esc(d.venue||'NA')} (${d.year||'NA'}) · ${esc(authors)} · 인용 ${d.cited_by||0}${d.doi?` · <a href="${esc(d.url)}" target="_blank">DOI</a>`:''}</div>
    ${su.summary?`<div class="kv">${esc(su.summary)}</div>`:''}
    ${su.key_result?`<div class="kv"><b>핵심 결과</b> ${esc(su.key_result)}</div>`:''}
    ${su.dependent_var?`<div class="kv"><b>종속변수</b> ${esc(su.dependent_var)}</div>`:''}
    ${su.independent_var?`<div class="kv"><b>독립변수</b> ${esc(su.independent_var)}</div>`:''}
    ${su.method?`<div class="kv"><b>방법</b> ${esc(su.method)}</div>`:''}
    ${su.caveats?`<div class="kv caveat"><b>⚠️ 유의점</b> ${esc(su.caveats)}</div>`:''}
    ${d.reason?`<div class="kv" style="color:var(--mut)"><b>선정 이유</b> ${esc(d.reason)}</div>`:''}
    ${d.abstract?`<div class="en"><b>Abstract.</b> ${esc(d.abstract)}</div>`:''}
  </div>`;
}
"""

_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paper Archive — VC/창업금융</title>
<style>""" + _CSS + r"""</style>
</head><body>
<header>
  <h1>📚 Paper Archive — VC·창업금융 큐레이션</h1>
  <div class="meta">갱신: {{ generated_at }} · 총 {{ store|length }}편 · <a href="weekly/">주간 모음</a></div>
  <div class="controls">
    <input id="q" placeholder="제목·저널·요약·키워드 검색…">
    <select id="tier">
      <option value="">전체 티어</option>
      <option value="1">Tier 1 (최우선)</option>
      <option value="2">Tier 2</option>
      <option value="3">Tier 3</option>
      <option value="F">Foundational</option>
    </select>
    <select id="sort">
      <option value="relevance">관련도순</option>
      <option value="year">최신순</option>
      <option value="cited">인용순</option>
    </select>
    <button id="toggle-en">EN 초록 보기</button>
  </div>
</header>
<main><div class="count" id="count"></div><div id="list"></div></main>
<script>
const DATA = {{ store_json }};
""" + _CARD_JS + r"""
const list=document.getElementById('list'), q=document.getElementById('q'),
      sortSel=document.getElementById('sort'), tierSel=document.getElementById('tier'),
      countEl=document.getElementById('count');
function render(){
  const term=q.value.toLowerCase().trim(), tf=tierSel.value;
  let rows=DATA.slice();
  if(tf) rows=rows.filter(d=>String(d.tier)===tf);
  if(term) rows=rows.filter(d=>[d.title,d.venue,(d.summary&&d.summary.summary),(d.concepts||[]).join(' '),(d.authors||[]).join(' ')].join(' ').toLowerCase().includes(term));
  const s=sortSel.value;
  rows.sort((a,b)=> s==='year'?(b.year||0)-(a.year||0) : s==='cited'?(b.cited_by||0)-(a.cited_by||0) : (b.relevance||0)-(a.relevance||0));
  countEl.textContent=rows.length+'편 표시';
  list.innerHTML=rows.map(cardHtml).join('')||'<p style="color:var(--mut)">조건에 맞는 논문이 없습니다.</p>';
}
q.oninput=render; sortSel.onchange=render; tierSel.onchange=render;
document.getElementById('toggle-en').onclick=(e)=>{document.body.classList.toggle('show-en');e.target.textContent=document.body.classList.contains('show-en')?'EN 초록 숨기기':'EN 초록 보기';};
render();
</script>
</body></html>""")

_WEEKLY_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>주간 {{ date_tag }} — Paper Archive</title>
<style>""" + _CSS + r"""</style>
</head><body>
<header>
  <h1>📬 이번 주 신규 — {{ date_tag }}</h1>
  <div class="meta">{{ store|length }}편 · <a href="../">전체 아카이브</a> · <a href="./">주간 모음</a></div>
</header>
<main><div id="list"></div></main>
<script>
const DATA = {{ store_json }};
""" + _CARD_JS + r"""
DATA.sort((a,b)=>(b.relevance||0)-(a.relevance||0));
document.getElementById('list').innerHTML=DATA.map(cardHtml).join('')||'<p style="color:var(--mut)">이번 주 신규 논문이 없습니다.</p>';
</script>
</body></html>""")

_WEEKLY_INDEX = Template(r"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>주간 모음 — Paper Archive</title>
<style>""" + _CSS + r"""</style>
</head><body>
<header><h1>📬 주간 모음</h1><div class="meta"><a href="../">전체 아카이브</a></div></header>
<main>{% for w in weeks %}<div class="card"><a href="{{ w }}.html">📅 {{ w }}</a></div>{% endfor %}
{% if not weeks %}<p style="color:var(--mut)">아직 주간 페이지가 없습니다.</p>{% endif %}</main>
</body></html>""")


def render(site_dir: Path, store: list[dict], generated_at: str) -> Path:
    site_dir.mkdir(parents=True, exist_ok=True)
    html = _TEMPLATE.render(
        store=store, store_json=json.dumps(store, ensure_ascii=False),
        generated_at=generated_at,
    )
    out = site_dir / INDEX_FILE
    out.write_text(html, encoding="utf-8")
    return out


def render_weekly(site_dir: Path, entries: list[Entry], date_tag: str) -> Path:
    """그 주 논문만 담은 site/weekly/<date>.html 생성 + weekly/index.html 갱신."""
    wdir = site_dir / WEEKLY_DIR
    wdir.mkdir(parents=True, exist_ok=True)
    rows = [e.to_dict() for e in entries]
    html = _WEEKLY_TEMPLATE.render(
        store=rows, store_json=json.dumps(rows, ensure_ascii=False), date_tag=date_tag,
    )
    out = wdir / f"{date_tag}.html"
    out.write_text(html, encoding="utf-8")
    weeks = sorted((p.stem for p in wdir.glob("*.html") if p.stem != "index"), reverse=True)
    (wdir / INDEX_FILE).write_text(_WEEKLY_INDEX.render(weeks=weeks), encoding="utf-8")
    return out


def update_site(site_dir: Path, entries: list[Entry], generated_at: str,
                tier1: int = 25, tier2: int = 75) -> list[dict]:
    """누적 저장 + 티어 부여 + 렌더. 갱신된 전체 store 반환."""
    store = merge(load_store(site_dir), entries)
    assign_tiers(store, tier1, tier2)
    save_store(site_dir, store)
    render(site_dir, store, generated_at)
    return store
