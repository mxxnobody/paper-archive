# Paper Archive — VC·창업금융 논문 자동 큐레이션

OpenAlex(+Semantic Scholar)에서 모험자본·창업금융 논문을 자동 수집 →
**가중 키워드 휴리스틱**으로 관련도 랭킹 → abstract·TLDR 정리 + 키워드 기반 DV/IV/방법 태깅 →
**Zotero 자동 적재 + HTML 브라우징 아카이브 + 텔레그램 주간 알림**으로 전달합니다.

> **LLM 미사용** — Anthropic 등 유료 API 키가 필요 없습니다. 관련도·태깅은 모두 키워드·인용·최신성 규칙으로 계산합니다.

## 동작 방식

| 모드 | 트리거 | 출력 |
|---|---|---|
| **백필**(시작판) | 수동 1회 (`backfill.yml`) | 2013~현재 + 고전 canon → HTML·Zotero·RIS |
| **주간** | 매주 월 09:00 KST | 신규 논문 → 텔레그램 + HTML·Zotero·RIS 누적 |
| **월간** | 매월 1일 09:00 KST | 최근 1년 보강 → HTML·Zotero·RIS (텔레그램 없음) |

관련도·키워드·임계값은 모두 `config/profile.yaml` 한 곳에서 조정합니다.
고전 canon 목록은 `config/canon.yaml`.

## 준비물 (한 번만)

1. **텔레그램 봇**: [@BotFather](https://t.me/BotFather)에서 `/newbot` → **봇 토큰**. 봇과 대화를 한 번 시작한 뒤
   `https://api.telegram.org/bot<토큰>/getUpdates` 를 열어 `chat.id`(**chat_id**) 확보.
2. **Zotero**: [API 키 발급](https://www.zotero.org/settings/keys)에서 *read/write* 키 생성 → **API 키** + **userID**(같은 페이지). 적재할 **컬렉션 키**(컬렉션 URL 끝 8자리).
3. **GitHub repo** push 후 **Settings → Pages → Source: GitHub Actions** 활성화.

### Secrets / Variables 등록
**Settings → Secrets and variables → Actions**

Secrets:
```
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
ZOTERO_API_KEY, ZOTERO_USER_ID, ZOTERO_COLLECTION_KEY,
OPENALEX_MAILTO (= 이메일, polite pool 용),
SEMANTIC_SCHOLAR_API_KEY (선택)
```
Variables:
```
SITE_URL = https://<github아이디>.github.io/<repo>/   (텔레그램에 넣을 사이트 링크, 선택)
```

## 첫 실행 (시작판 백필)

1. **축소 점검**(선택): Actions → *Backfill* → `limit=20` 으로 실행해 수집·HTML·Zotero·RIS 경로 확인.
2. 정상이면 `limit` 비우고 **전체 백필**. (LLM을 안 쓰므로 빠르고 무료.)
3. 이후 주간/월간은 cron으로 자동 실행됩니다.

## 로컬 실행 / 개발

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
set -a; source secrets.env; set +a    # 로컬 비밀값 로드 (secrets.env는 gitignore됨)
# 축소 dry-run
.venv/bin/python entrypoints/backfill.py --limit 20
# 실제
.venv/bin/python entrypoints/weekly.py

# 테스트
.venv/bin/python -m pytest -q
```

## 산출물 위치

- `site/index.html` — 브라우징 아카이브(정렬·검색·관련도 필터·EN 초록 토글). GitHub Pages로 배포.
- `site/data.json` — 누적 데이터 저장소.
- `exports/*.ris` — 기간별 Zotero 백업 서지.
- `state/seen.json` — 처리 이력(중복 방지). 워크플로가 매 실행 후 커밋.

## 커스터마이징

- 키워드·핵심 키워드·저널 allowlist·연도·임계값 → `config/profile.yaml`
- 고전 canon DOI → `config/canon.yaml` (틀린 DOI는 경고 후 건너뜀, 백필 로그 확인)
- 관련도 가중치 규칙 → `src/paperarchive/rank.py`
- DV/IV/방법 탐지 용어 사전 → `src/paperarchive/summarize.py`
