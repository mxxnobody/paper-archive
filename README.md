# Paper Archive — VC·창업금융 논문 자동 큐레이션

OpenAlex(+Semantic Scholar)에서 모험자본·창업금융 논문을 자동 수집 →
키워드 1차 + Claude 2차 관련도 랭킹 → **한국어 구조화 요약** →
**Zotero 자동 적재 + HTML 브라우징 아카이브 + 텔레그램 주간 알림**으로 전달합니다.

## 동작 방식

| 모드 | 트리거 | 출력 |
|---|---|---|
| **백필**(시작판) | 수동 1회 (`backfill.yml`) | 2013~현재 + 고전 canon → HTML·Zotero·RIS |
| **주간** | 매주 월 09:00 KST | 신규 논문 → 텔레그램 + HTML·Zotero·RIS 누적 |
| **월간** | 매월 1일 09:00 KST | 최근 1년 보강 → HTML·Zotero·RIS (텔레그램 없음) |

관련도·요약·키워드는 모두 `config/profile.yaml` 한 곳에서 조정합니다.
고전 canon 목록은 `config/canon.yaml`.

## 준비물 (한 번만)

1. **텔레그램 봇**: [@BotFather](https://t.me/BotFather)에서 `/newbot` → **봇 토큰**. 봇과 대화를 한 번 시작한 뒤
   `https://api.telegram.org/bot<토큰>/getUpdates` 를 열어 `chat.id`(**chat_id**) 확보.
2. **Zotero**: [API 키 발급](https://www.zotero.org/settings/keys)에서 *read/write* 키 생성 → **API 키** + **userID**(같은 페이지). 적재할 **컬렉션 키**(컬렉션 URL 끝 8자리).
3. **Anthropic API 키**: <https://console.anthropic.com>.
4. **GitHub repo** 생성 후 이 디렉토리를 push. **Settings → Pages → Source: GitHub Actions** 활성화.

### Secrets / Variables 등록
**Settings → Secrets and variables → Actions**

Secrets:
```
ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
ZOTERO_API_KEY, ZOTERO_USER_ID, ZOTERO_COLLECTION_KEY,
OPENALEX_MAILTO (= 이메일, polite pool 용),
SEMANTIC_SCHOLAR_API_KEY (선택)
```
Variables:
```
SITE_URL = https://<github아이디>.github.io/<repo>/   (텔레그램에 넣을 사이트 링크, 선택)
```

## 첫 실행 (시작판 백필)

1. 먼저 **무료 검증**: Actions → *Backfill* → `limit=20`, `skip_llm=true` 로 실행.
   Claude 호출 없이 수집·HTML·Zotero·RIS 경로를 점검합니다.
2. 결과 사이트/Zotero가 정상이면, `limit` 비우고 `skip_llm=false` 로 **전체 백필**.
   (백필은 Claude 호출이 많아 비용이 일시적으로 큽니다 — 의도된 동작.)
3. 이후 주간/월간은 cron으로 자동 실행됩니다.

## 로컬 실행 / 개발

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # 필요한 키들 export
# 무료 dry-run
.venv/bin/python entrypoints/backfill.py --limit 20 --skip-llm
# 실제
.venv/bin/python entrypoints/weekly.py

# 테스트
.venv/bin/python -m pytest -q
```

## 산출물 위치

- `site/index.html` — 브라우징 아카이브(정렬·검색·한↔영 토글). GitHub Pages로 배포.
- `site/data.json` — 누적 데이터 저장소.
- `exports/*.ris` — 기간별 Zotero 백업 서지.
- `state/seen.json` — 처리 이력(중복 방지). 워크플로가 매 실행 후 커밋.

## 커스터마이징

- 키워드·종속/독립변수·저널 allowlist·연도·임계값 → `config/profile.yaml`
- 고전 canon DOI → `config/canon.yaml` (틀린 DOI는 경고 후 건너뜀, 백필 로그 확인)
- 요약 톤/필드 → `src/paperarchive/summarize.py`
- 랭킹 기준 프롬프트 → `src/paperarchive/rank.py`
