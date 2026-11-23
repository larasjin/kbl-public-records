# KBL 공개 기록실 정규리그 데이터

2026년 11월 23일 한국시간 기준 KBL 10개 구단의 종료된 정규리그 경기를 담았다. 2026–27시즌의 최신 종료 경기는 11월 19일 경기다. 연장전을 포함하며 플레이오프, 시범경기, 컵대회, 국제대회, 올스타전, D리그를 제외했다. [KBL 일정 및 결과](https://www.kbl.or.kr/match/schedule)

| 시즌 | 수록 경기일 | 종료 경기 | 연장 경기 | 라인업 검증 통과 |
|---|---|---:|---:|---:|
| 2025–26 | 2025-10-03~2026-04-08 | 270 | 13 | 249 |
| 2026–27 | 2026-10-03~2026-11-19 | 77 | 1 | 77 |
| 합계 | | 347 | 14 | 326 |

## 파일

| 파일 | 내용 |
|---|---|
| [games.csv](data/games.csv) | 경기일, 홈·원정 팀, 최종 점수, 연장 횟수, 경기 유형 |
| [2025–26 PBP 1–135경기](data/pbp_2025-2026_part1.csv), [2025–26 PBP 136–270경기](data/pbp_2025-2026_part2.csv), [2026–27 PBP](data/pbp_2026-2027.csv) | 공개 문자중계 이벤트 211,266행. 선수, 팀, 쿼터, 시간, 유형, 교체, 누적 점수, 원본 데이터 |
| [quarter_starters.csv](data/quarter_starters.csv) | 정규 쿼터와 연장 양 팀 개시 5인, 총 14,050행 |
| [players.csv](data/players.csv), [player_teams.csv](data/player_teams.csv) | 선수 241명의 포지션, 신장, 선수 구분, 신인 여부, 최신 등록과 경기 엔트리 기준 구단 |
| [boxscores.csv](data/boxscores.csv) | 공식 선수별 경기 기록 8,328행 |
| [roster_moves.csv](data/roster_moves.csv) | 공개 공지 또는 보도에서 날짜와 선수 ID를 확인한 사례 17건 |
| [stints.csv](data/stints.csv), [stint_players.csv](data/stint_players.csv) | 라인업별 구간 9,630행, 구간의 코트 위 선수, 시작·종료 시각 및 득실 |
| [quality.csv](data/quality.csv), [quality_review.csv](data/quality_review.csv) | 전체 경기 검증, 추가 검토 21경기 |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | 파일별 키와 필드 설명 |
| [update.py](update.py), [PBP_Crawling/](PBP_Crawling/) | 공개 기록 수집, CSV 생성, 이벤트 코드와 로스터 근거 목록 |
| [source_cache.zip](source_cache.zip) | 공개 응답으로 같은 CSV를 재생성할 때 사용하는 캐시. CSV 제작에 쓰지 않는 생년월일 필드는 제외했다 |

CSV는 UTF-8이다. `game_id`와 `player_id`는 KBL 공식 코드를 사용한다. `team_id`를 포함한 ID 컬럼은 문자열로 읽는다. 수원 KT의 코드는 `06`이다. 구간과 구간별 선수는 `game_id, stint_id`로 연결한다.

## 공개 기록 누락과 라인업 검증

- 모든 경기 PBP는 공개 경기 페이지의 문자중계 응답을 사용했다. `raw_event`에 이벤트 JSON 원본을, `raw_text`에 이름과 KBL 표시 라벨을 결합한 문구를 담았다. `S47G01N2`의 공개 중계 누적 점수는 삼성 79–85 KCC이며 공식 최종 점수는 82–89다. 원본에서 순번을 건너뛴 경기와 득점 차이는 `quality.csv`에서 확인할 수 있다.
- 점프볼과 세부 바이올레이션의 독립 이벤트, 자유투 회차의 공식 값은 공개 피드에서 확인되지 않았다. 자유투 회차를 복원할 수 있는 경우 `ft_source=inferred_from_foul_sequence`로 표시했다. 나머지는 빈 칸으로 두었다.
- 라인업 분석에는 `stints.csv`의 `game_verified=1`을 사용한다. 공식 점수, 코트 위 5인, 선발, 교체, 선수별 공식 출전시간을 대조했다. 시계가 역행한 쿼터는 이벤트 순서를 고정하고 현재 행까지 최소 잔여시간을 적용한 방법과 이후 최대 잔여시간을 적용한 방법의 구간 경계, 구성, 득실을 비교했다. 결과가 다르거나 원본 시각이 쿼터 길이를 벗어난 경기에는 검토 표시를 붙였다.
- `S47G01N112`에서 네이던 나이트의 5반칙 OUT과 후속 실격 OUT을 원본대로 보존했다. 후속 실격은 해당 선수가 이미 나간 시각에 기록되어 라인업에는 처음 OUT을 반영했다.
- 로스터 이동은 출처를 확인한 사례만 담았다. 공개 경기 엔트리에서 빠졌다는 사실로 부상 결장을 추정하지 않는다. 전체 부상 결장과 가승인 신청일은 확인되지 않았다. 등록일, 발표일, 첫 경기일은 `date_basis`로 구분한다.

## 경기 추가와 재생성

macOS 또는 Linux, Python 3.10 이상에서 압축을 푼 폴더로 이동한 후 실행한다. 인터넷 연결 없이 동봉 시점을 재생성하려면 첫 번째 명령을, 새로운 종료 경기를 추가하려면 두 번째 명령을 사용한다.

```bash
python3 update.py --offline --as-of 2026-11-23
python3 update.py
```

온라인 실행은 공개 일정에서 종료 경기 ID를 확인한다. 새 경기의 문자중계와 박스스코어를 받아 캐시하고, 기존 경기는 캐시를 재사용한다. 구단 등록 명단을 갱신하고 필요할 때 새 선수의 공개 프로필을 조회한다. 규격에 맞는 원본이 모두 확보되면 `data/`의 CSV를 다시 생성한다. 다운로드 중 실패하면 기존 CSV가 남고, 성공한 원본은 재시도에 재사용한다.

공개 기록이 수정된 경기만 다시 받으려면 `python3 update.py --refresh-game S47G01N2`를 실행한다. 선수 등록 목록을 갱신하지 않고 경기 기록만 갱신할 때는 `--skip-profiles`를 사용할 수 있다. 로스터 이동 사례는 [근거 목록](PBP_Crawling/roster_moves_evidence.tsv)에 확인한 날짜, 유형, 선수, 양 구단 코드, 대체 대상, 날짜의 기준, 출처 URL을 탭으로 구분해 추가한 후 위 명령으로 반영한다.

`data/`에 CSV, `PBP_Crawling/`에 수집·전처리 코드와 로스터 근거를 둔다. `source_cache.zip`을 함께 두면 받은 사람이 과거 경기 원본을 재사용할 수 있다. 폴더별 역할과 파일 설명 방식은 [TPBL 분석 저장소](https://github.com/parkeunji8/25-26-TPBL-McC)를 참고했다.

## 출처

- [KBL 공개 기록실](https://www.kbl.or.kr/record/seasonLeader)과 [KBL 일정 및 결과](https://www.kbl.or.kr/match/schedule)
- [KBL 공개 선수 등록 및 프로필](https://www.kbl.or.kr/player/player)
- 공개 경기 요청은 KBL 웹사이트가 사용하는 일정, 문자중계, 선수 경기 기록 응답을 읽는다. [KBL 응답 경로 참고](https://py.sportsdataverse.org/docs/kbl/reference/kbl/other)
