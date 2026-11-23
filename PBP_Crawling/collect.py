"""Collect the requests used by the public KBL schedule and box score pages."""

import json
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

KBL = "https://api.kbl.or.kr"
SPORTS2I = "https://kbl-api.sports2i.com/api/v1"
SEASONS = {"S47G01", "S49G01"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, payload):
    temporary = path.with_suffix(".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)


class PublicRecords:
    def __init__(self):
        self.next_request = 0.0

    def get(self, base, path, params=None):
        url = base + path
        if params:
            url += "?" + urlencode(params, safe=",")
        headers = {"Accept": "application/json", "Origin": "https://www.kbl.or.kr"}
        if base == KBL:
            headers.update({"Channel": "WEB", "TeamCode": "XX", "Referer": "https://www.kbl.or.kr/"})
        else:
            headers["Referer"] = "https://www.kbl.or.kr/player/player"
        for attempt in range(3):
            time.sleep(max(0, self.next_request - time.monotonic()))
            self.next_request = time.monotonic() + 1.3
            try:
                with urlopen(Request(url, headers=headers), timeout=35) as response:
                    return json.load(response)
            except HTTPError as error:
                if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise
                retry_after = error.headers.get("Retry-After", "")
                if retry_after.isdigit() and int(retry_after) > 120:
                    raise
                delay = int(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1)
            except (URLError, TimeoutError, json.JSONDecodeError):
                if attempt == 2:
                    raise
                delay = 2 ** (attempt + 1)
            self.next_request = max(self.next_request, time.monotonic() + delay)


def regular_finals(rows, as_of):
    finals = {}
    cutoff = as_of.strftime("%Y%m%d")
    for row in rows:
        if (
            row.get("glkey") in SEASONS
            and str(row.get("seasonGrade")) == "1"
            and str(row.get("isEnded")) == "1"
            and row["gameDate"] <= cutoff
        ):
            finals[row["gmkey"]] = row
    return sorted(finals.values(), key=lambda row: (row["gameDate"], int(row["gameNo"])))


def schedule(client, cache, as_of, offline):
    if offline:
        return regular_finals(read_json(cache / "schedule.json"), as_of)
    rows = []
    for year in range(2025, min(as_of.year, 2027) + 1):
        first = date(year, 9, 1) if year == 2025 else date(year, 1, 1)
        last = min(as_of, date(year, 12, 31))
        if first > last:
            continue
        payload = client.get(KBL, "/match/list", {
            "fromDate": first.strftime("%Y%m%d"), "toDate": last.strftime("%Y%m%d")
        })
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"일정 응답이 비어 있거나 형식이 다릅니다 ({year})")
        rows.extend(payload)
    games = regular_finals(rows, as_of)
    if as_of >= date(2026, 4, 9) and sum(row["glkey"] == "S47G01" for row in games) != 270:
        raise ValueError("공개 일정에서 2025–26 종료 경기 270건을 확인하지 못했습니다.")
    previous = cache / "schedule.json"
    if previous.exists():
        prior_ids = {row["gmkey"] for row in regular_finals(read_json(previous), as_of)}
        if missing := prior_ids - {row["gmkey"] for row in games}:
            raise ValueError(f"공개 일정에서 기존 종료 경기가 사라졌습니다 ({', '.join(sorted(missing))})")
    return games


def download_games(client, cache, games, refresh, offline):
    errors = []
    for game in games:
        game_id = game["gmkey"]
        for route in ("text-cast", "player-stat"):
            path = cache / f"{game_id}_{route}.json"
            try:
                if offline or (path.exists() and game_id not in refresh):
                    payload = read_json(path)
                else:
                    params = {"quarterList": "Q1,Q2,Q3,Q4,EQ1,EQ2,EQ3,EQ4"} if route == "text-cast" else None
                    payload = client.get(KBL, f"/match/{game_id}/{route}", params)
                if not isinstance(payload, list) or not payload:
                    raise ValueError("빈 응답 또는 응답 형식 변경")
                if route == "text-cast" and not {"Q1", "Q2", "Q3", "Q4"}.issubset(
                    {row["q"] for row in payload}
                ):
                    raise ValueError("정규 쿼터가 모두 존재하지 않습니다.")
                if route == "player-stat" and {row["player"]["tcode"] for row in payload} != {
                    game["tcodeH"], game["tcodeA"]
                }:
                    raise ValueError("박스스코어 구단이 경기 일정과 다릅니다.")
                if not offline and (not path.exists() or game_id in refresh):
                    save_json(path, payload)
                    print(f"{game_id} {route}", flush=True)
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as error:
                errors.append(f"{game_id} {route}: {error}")
    if errors:
        raise ValueError("미수집 경기 기록\n" + "\n".join(errors))


def download_profiles(client, cache, games, as_of):
    registered = {}
    size = 20
    page = 1
    while True:
        payload = client.get(SPORTS2I, "/players", {"regSc": "Y", "pageNo": page, "listCn": size})
        total = int(payload["totalCn"])
        entries = payload["playerList"]
        if not entries or total < 1:
            raise ValueError("공개 선수 등록 목록에서 빈 페이지를 받았습니다.")
        registered.update((str(x["playerNo"]), x) for x in entries)
        if page * size >= total:
            break
        page += 1
    if len(registered) != total:
        raise ValueError("등록 목록 집계와 고유 선수 수가 다릅니다. 잠시 후 다시 실행하세요.")

    players = {}
    for game in reversed(games):
        for row in read_json(cache / f"{game['gmkey']}_player-stat.json"):
            p = row["player"]
            players.setdefault(str(p["pcode"]), p)

    for player_id, player in players.items():
        team = player["tcode"]
        if player_id not in registered and not any(cache.glob(f"profile_{player_id}_*.json")):
            path = cache / f"profile_{player_id}_{team}.json"
            try:
                profile = client.get(SPORTS2I, f"/players/profile/{team}/{player_id}")
                if profile.get("playerInfo"):
                    save_json(path, profile)
            except HTTPError as error:
                if error.code != 404:
                    raise
        known_year = str(registered.get(player_id, {}).get("yearNo") or "").strip()
        draft_path = cache / f"draft_{player_id}.json"
        if str(player.get("playerFlag")) == "0" and not known_year.isdigit() and not draft_path.exists():
            payload = client.get(SPORTS2I, "/players", {
                "regSc": "N", "playerNm": player["pname"], "pageNo": 1, "listCn": 20
            })
            matched = [row for row in payload["playerList"] if str(row["playerNo"]) == player_id]
            save_json(draft_path, matched)

    save_json(cache / "registration.json", {"date": as_of.isoformat(), "players": list(registered.values())})
