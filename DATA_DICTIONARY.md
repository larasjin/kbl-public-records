# KBL 데이터 사전

CSV는 UTF-8이며, 빈 칸은 미제공 또는 해당 없음이다. 날짜는 한국시간 기준 `YYYY-MM-DD`다. `game_id`, `team_id`, `player_id` 및 코드 값은 문자열로 읽는다. 수원 KT의 팀 코드는 `06`이다.

## 파일과 행 단위

아래 CSV 파일은 모두 `data/`에 있다.

| 파일 | 한 행 | 키 |
|---|---|---|
| `games.csv` | 정규리그 종료 경기 | `game_id` |
| `pbp_2025-2026_part1.csv` | 25–26시즌 경기번호 1–135의 문자중계 이벤트 | `game_id, seq` |
| `pbp_2025-2026_part2.csv` | 25–26시즌 경기번호 136–270의 문자중계 이벤트 | `game_id, seq` |
| `pbp_2026-2027.csv` | 26–27시즌 문자중계 이벤트 | `game_id, seq` |
| `quarter_starters.csv` | 쿼터 시작 시 실제 코트 위 선수 | `game_id, quarter, team_id, player_id` |
| `players.csv` | 선수 최신 등록 정보 또는 마지막 경기 시점의 정보 | `player_id` |
| `player_teams.csv` | 시즌과 구단별 해당 선수의 경기 엔트리 관측 | `season, team_id, player_id` |
| `boxscores.csv` | 경기별 선수 엔트리와 공식 개인 기록 | `game_id, team_id, player_id` |
| `roster_moves.csv` | 날짜와 출처를 확인한 로스터 이동·결장 사례 | `move_id` |
| `stints.csv` | 양 팀 코트 위 선수가 동일한 쿼터 내 구간 | `game_id, stint_id` |
| `stint_players.csv` | 구간 내 코트 위 선수 | `game_id, stint_id, side, player_id` |
| `quality.csv` | 경기 단위의 수집 검증 | `game_id` |
| `quality_review.csv` | 라인업 또는 최종 점수 검토가 필요한 경기 | `game_id` |

## 공통 식별자와 경기

| 필드 | 설명 |
|---|---|
| `game_id` | KBL 공식 경기 키. 예를 들어 `S49G01N1`은 시즌 코드 49, 경기 유형 01, 번호 1이다. |
| `player_id` | KBL의 선수 고유번호 `pcode`. 시즌이나 소속팀이 바뀌어도 동일한 번호다. |
| `team_id`, `home_team_id`, `away_team_id` | KBL 구단 코드 |
| `season` | 시작년–종료년. CSV에는 `2025-2026`처럼 기록 |
| `date` | 경기일 또는 로스터 이동의 기준일 |
| `home_team`, `away_team` | 경기 당시 홈·원정 팀명 |
| `home_score`, `away_score` | 경기 마스터는 공식 최종 점수. PBP는 이벤트 직후 성공 득점을 누적한 점수 |
| `overtimes` | 문자중계에서 확인한 연장 횟수 |
| `game_type` | 공식 경기 유형 이름 `정규시즌` |

## 플레이바이플레이

| 필드 | 설명 |
|---|---|
| `seq`, `source_seq` | 수집한 원본 행 순서대로 부여한 경기 내 1부터의 순번, KBL 원본 이벤트 번호 |
| `quarter`, `clock_seconds` | 정규 쿼터 1–4, 첫 연장 5부터. 잔여시간은 원본 분·초를 초로 환산 |
| `player_name`, `actor_type` | 원본 이름과 행위자 유형. `player`, `non_player`, `unmatched`, `team`, `game` |
| `event_type` | 이벤트의 정규화된 범주 |
| `action_code`, `action_ko` | 원본 액션 코드와 KBL 공개 문자중계의 한국어 표시명 |
| `points` | 해당 행에서 추가된 득점. 2점슛·덩크 2, 자유투 1, 3점슛 3 |
| `foul_type` | 공식 표기명을 찾을 경우 파울명, 그 외 원본 세부 코드 또는 공개 중계의 파울 범주 |
| `ft_attempt`, `ft_total`, `ft_source` | 해당 자유투 순번과 같은 시퀀스 전체 시도 수. 공개 피드에 원래 순번은 없다. 파울 이후 이어지는 같은 선수의 시도가 1–3개일 때 추정 표시 `inferred_from_foul_sequence`를 붙인다. 나머지 자유투는 `unknown` |
| `in_player_id`, `out_player_id` | 교체 IN 행은 IN 선수, OUT 행은 OUT 선수. 원본의 각 IN·OUT 액션을 각각 한 행으로 유지 |
| `raw_text` | 선수명, KBL 화면의 액션명·표시 가능한 부가 라벨을 결합한 한국어 중계 문구 |
| `raw_event` | 공개 문자중계가 반환한 해당 이벤트의 JSON 객체. 각 키와 값을 보존한다. |

공개 피드의 야투·자유투 시도 코드는 성공과 별개다. 정규화된 CSV에는 성공과 실패를 구분하고, 덩크를 별도 유형으로 기록한다. 세부 바이올레이션과 점프볼의 독립 이벤트는 공개 피드에서 확인되지 않았다. 파울 종류나 시도 번호에서 원본으로 확인할 수 없는 값은 빈 칸 또는 원본 코드로 보존한다.

## 쿼터 시작과 라인업 구간

| 필드 | 설명 |
|---|---|
| `verified_five` | 쿼터 시작 잔여시간의 교체를 반영한 후 해당 팀 코트 위 선수 5명이 확인되면 1 |
| `stint_id` | 경기 내 시간순 구간 번호 |
| `start_seq`, `end_seq` | 구간을 생성하고 마지막으로 갱신한 이벤트 순서. 동일 초에 여러 이벤트가 있을 때 순서를 확인하는 데 사용 |
| `start_clock_seconds`, `end_clock_seconds` | 구간의 시작·종료 쿼터 잔여시간 |
| `start_elapsed_seconds`, `end_elapsed_seconds`, `duration_seconds` | 경기 시작 후 누적 경기시간 기준 시작·종료 초, 구간 길이 |
| `home_players`, `away_players` | 홈·원정 선수 번호를 각각 파이프로 이어 붙인 값 |
| `home_points`, `away_points`, `point_diff` | 구간 홈 득점, 원정 득점, 홈 득점에서 원정 득점을 뺀 값 |
| `lineup_5v5` | 양 팀 5인씩 확인되면 1 |
| `side` | 구간 선수 표의 `home` 또는 `away` |

쿼터마다 초기 IN 행부터 코트 상태를 새로 추적한다. 구간 계산은 정규 600초, 연장 300초 범위에서 직전 유효 잔여시간보다 커지지 않도록 제한한다. PBP의 원본 시각은 그대로 유지한다. 쿼터 시작 잔여시간에 기록된 교체가 있으면 첫 유효 경기 구간의 선수를 선발로 기록한다. 득점은 해당 행 직전의 코트 상태에 귀속한다. 같은 초 안에서 교체와 득점이 발생하면 길이 0초 구간이 생길 수 있다. 이 구간에 득점이 있으면 경기 득점을 보존하기 위해 포함한다.

## 선수

| 필드 | 설명 |
|---|---|
| `player_name` | KBL 선수 표기명 |
| `team_name` | 선수 행의 구단명 |
| `position` | KBL 포지션 코드. `GD` 가드, `FD` 포워드, `C` 센터, `GF` 가드·포워드, `FC` 포워드·센터 |
| `height_cm` | KBL 공개 선수 정보의 신장(cm) |
| `profile_source` | `kbl_public_registration`은 공개 등록선수 목록, `kbl_public_player_profile`은 공개 개별 선수 프로필 |
| `draft_year` | 확인된 KBL 국내 드래프트 또는 연고선수 등록 연도 |
| `player_category` | 국내, 외국, 아시아쿼터 |
| `rookie` | 시즌 시작연도와 국내 드래프트·연고선수 연도가 같으면 1, 확인된 이전 연도 또는 이전 시즌 KBL 출장이 있으면 0. 증거 부족 또는 국내 신인 분류 비대상은 빈 칸 |
| `as_of_season`, `as_of_date` | 선수 마스터 기준 시즌과 날짜 |
| `team_basis` | 최신 등록 구단 `current_registration` 또는 수집 범위 마지막 박스스코어 구단 `latest_boxscore` |
| `first_game_id`, `last_game_id` | 해당 시즌·구단 엔트리에 관측된 첫·마지막 경기 |

## 선수별 박스스코어

원본 제공 단위와 필드명을 보존했다. 경기 최초 선발은 `started` 1, 출전시간 환산값은 `minutes_seconds`다.

| KBL 필드 | 설명 |
|---|---|
| `score`, `ast`, `stl`, `bs`, `to` | 득점, 어시스트, 스틸, 블록, 턴오버 |
| `rb`, `offr`, `defr` | 총·공격·수비 리바운드 |
| `fg`, `fgA` | 2점슛 성공·시도 |
| `threep`, `threepA` | 3점슛 성공·시도 |
| `fgt`, `fgtA` | 전체 야투 성공·시도 |
| `ft`, `ftA` | 자유투 성공·시도 |
| `dk`, `dkA` | 덩크 성공·시도 |
| `foul`, `wft`, `woft`, `tf`, `fo` | 개인 파울, 자유투를 수반한·수반하지 않은 파울, 테크니컬 파울, 파울아웃 관련 원본 필드 |
| `playMin`, `playSec`, `marginCn` | 출전시간의 분·초 성분, 플러스마이너스 |
| `pp`, `ppA`, `sast`, `dfl`, `gd`, `fb` | 페인트존슛 성공·시도, 스크린 어시스트, 디플렉션, 굿디펜스, 속공 |
| `ef`, `idf`, `inout`, `inout1`, `pscore` | 세부 원본 카운터. 공식 계산 정의 미확인 |
| `offrtg`, `defrtg`, `netrtg` | 공격, 수비, 순 효율 |
| `efgRt`, `tsRt`, `per`, `pie` | 유효 야투율, 트루슈팅률, 선수 효율 지수, 선수 기여 지수 |
| `astRt`, `astTo`, `astRatio` | 어시스트율, 어시스트 대 턴오버 비율, 어시스트 비율 |
| `orebRt`, `drebRt`, `rebRt` | 공격·수비·전체 리바운드율 |
| `usgRt`, `toRatio`, `tovRt` | 사용률 및 원본의 턴오버 비율 지표 |
| `pace`, `poss` | 경기 속도 및 원본 포제션 지표 |

## 로스터 이동과 품질 검증

| 필드 | 설명 |
|---|---|
| `move_id`, `event_type` | 사례 번호, 트레이드·대체 외국선수·일시 대체 외국선수·부상 결장 등의 사건 구분 |
| `date_basis` | 구단 발표일 `announcement`, 등록일 `registration`, 첫 경기일 `first_game`, 결장 보도일 `public_absence_report`, 특정 경기일 `game_date` |
| `from_team_id`, `to_team_id` | 출발 또는 해당 팀, 이동 후 팀. 해당하는 경우 값 기재 |
| `related_player_id`, `related_player_name` | 교체 대상 등 연관된 선수 번호 및 이름 |
| `source_url` | 등록·이동·결장 날짜를 확인한 기사 또는 구단 공지 |
| `event_count`, `quarter_count`, `starter_rows` | 원본 이벤트 수, 정규·연장 쿼터 수, 선발 선수 행 수 |
| `non_player_fouls` | 경기 선수 엔트리에 연결되지 않은 벤치·비선수 파울 기록 수 |
| `unresolved_player_events`, `substitution_issues` | 선수 ID 매칭 실패 이벤트 수, 원문 검토 후 남은 IN·OUT 상태 불일치 또는 교체 ID 미확인 건수 |
| `score_ok` | 누적 득점과 공식 최종 점수가 일치하면 1 |
| `non_5v5_stints` | 양 팀 5인 구성 검증을 통과하지 못한 구간 수 |
| `clock_corrections` | 원본에서 잔여시간이 증가한 쿼터 목록. 경기시계의 공식 조정 여부와 별개인 원본 이벤트 시각 지표 |
| `max_box_seconds_difference` | 구간 선수별 시간 합과 공식 박스스코어 시간의 최대 절대 차이(초) |
| `game_verified` | 공식 최종 점수, 쿼터 시작·종료, 양 팀 선발과 코트 위 5인, 선수 및 교체 연결, 잔여시간 범위, 시계 처리 방식에 따른 구간 일치, 선수별 공식 출전시간을 확인해 모두 통과하면 1. 구간 표에도 동일한 값 포함 |
| `max_clock_increase_seconds` | 쿼터마다 그때까지 가장 작았던 잔여시간 대비 원본 잔여시간이 늘어난 값 중 경기 내 최댓값(초). 증가가 없으면 0 |
| `post_foul_out_disqualification_events` | 5반칙 퇴장으로 이미 코트를 떠난 선수에게 별도로 선언된 실격 판정 수. PBP에서 OUT으로 기록되었으며 이미 반영된 라인업에는 다시 적용하지 않음 |
| `clock_sensitive_stint_quarters` | 남은 시간을 현재 행까지의 최소값으로 처리한 결과와 현재 행 이후의 최대값으로 처리한 결과에서 구간 경계, 코트 위 선수 또는 득실이 달라진 쿼터. 해당 없으면 공란 |
| `period_markers_ok`, `q1_starters_ok` | 모든 쿼터의 시작·종료 행 및 1쿼터 선발과 공식 박스스코어의 일치 여부 |
| `out_of_range_clock_events` | 정규 쿼터 0–600초 또는 연장 0–300초 범위를 벗어난 원본 행 수 |
| `source_seq_gaps` | 인접한 두 원본 이벤트 번호 사이에 건너뛴 번호를 합산. 독립된 원문 확인이 없으면 빠진 내용이나 원인을 판정할 수 없음 |
| `pbp_home_score`, `pbp_away_score` | 공개 문자중계의 득점 이벤트를 합산한 경기 최종 점수 |
| `review_reason` | 추가 검토 사유. 복수 사유는 파이프로 연결한다. `score_mismatch`는 공식 점수 불일치, `period_markers_missing`은 쿼터 표식 누락, `clock_out_of_range`는 초 범위 초과, `starter_mismatch`는 선발 불일치, `non_5v5_lineup`은 코트 인원 불일치, `unresolved_player`는 선수 ID 미연결, `substitution_unresolved`는 교체 불일치, `clock_sensitive_stints`는 시계 처리 방식에 따른 구간 차이, `box_minutes_mismatch`는 공식 출전시간 불일치 |

### quality_review.csv

추가 검토 경기의 ID, 경기일, 구단명, 공식 최종 점수와 문자중계 합산 점수, 건너뛴 원본 순번 수, 최대 시계 역행, 복원 결과가 달라진 쿼터, 출전시간 차이, 검토 사유를 담는다.
