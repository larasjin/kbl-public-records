"""Rebuild the KBL CSV snapshot from the public feed and a local cache."""

import argparse
import fcntl
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from zipfile import ZipFile

from PBP_Crawling.build import process
from PBP_Crawling.collect import PublicRecords, download_games, download_profiles, save_json, schedule

ROOT = Path(__file__).resolve().parent
GENERATED_FILES = {
    'boxscores.csv', 'games.csv', 'pbp_2025-2026_part1.csv', 'pbp_2025-2026_part2.csv',
    'pbp_2026-2027.csv', 'player_teams.csv', 'players.csv', 'quality.csv',
    'quality_review.csv', 'quarter_starters.csv', 'roster_moves.csv', 'stint_players.csv',
    'stints.csv',
}


def update(args):
    cache = args.cache.resolve()
    output = args.output.resolve()
    if output == cache or output.is_relative_to(cache) or cache.is_relative_to(output):
        raise ValueError("캐시와 CSV 저장 위치는 서로 다른 디렉터리여야 합니다.")
    if output.exists() and (
        not output.is_dir() or any(
            not entry.is_file() or entry.name not in GENERATED_FILES for entry in output.iterdir()
        )
    ):
        raise ValueError("CSV 전용 디렉터리를 지정하세요.")
    cache.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo("Asia/Seoul")).date()
    as_of = args.as_of or now
    if as_of > now:
        raise ValueError("조회 종료일은 오늘 이후로 지정할 수 없습니다.")
    with (output.parent / f".{output.name}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        seed = ROOT / "source_cache.zip"
        if not (cache / "schedule.json").exists() and seed.exists():
            with ZipFile(seed) as archive:
                for item in archive.infolist():
                    if item.is_dir() or Path(item.filename).name != item.filename or not item.filename.endswith(".json"):
                        raise ValueError("원본 캐시 ZIP의 파일 구조가 올바르지 않습니다.")
                    destination = cache / item.filename
                    if not destination.exists():
                        destination.write_bytes(archive.read(item))

        client = PublicRecords()
        games = schedule(client, cache, as_of, offline=args.offline)
        if not games:
            raise ValueError("지정한 기간에 종료 경기 데이터가 없습니다.")
        refresh = set(args.refresh_game)
        if unknown := refresh - {game["gmkey"] for game in games}:
            raise ValueError(f"조회 기간의 종료 경기가 아닙니다 ({', '.join(sorted(unknown))})")
        download_games(client, cache, games, refresh, offline=args.offline)
        if not args.offline and not args.skip_profiles and as_of == now:
            download_profiles(client, cache, games, as_of)
        with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as temporary:
            stage = Path(temporary) / "incoming"
            stage.mkdir()
            process(games, cache, stage, as_of)
            backup = Path(temporary) / "previous"
            if output.exists():
                output.rename(backup)
            try:
                stage.rename(output)
            except OSError:
                if backup.exists():
                    backup.rename(output)
                raise
            if not args.offline:
                save_json(cache / "schedule.json", games)
    print(f"CSV 저장 위치: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="동봉한 공개 원본으로 CSV 재생성")
    parser.add_argument("--as-of", type=date.fromisoformat, help="종료 경기 조회 기준일 (한국시간)")
    parser.add_argument("--refresh-game", action="append", default=[], metavar="GAME_ID", help="지정한 경기를 다시 수집")
    parser.add_argument("--skip-profiles", action="store_true", help="선수 프로필 조회를 생략하고 캐시 사용")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache")
    parser.add_argument("--output", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    if args.offline and args.refresh_game:
        parser.error("--refresh-game은 온라인 수집에서 사용할 수 있습니다.")
    try:
        update(args)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"갱신 실패: {error}\n")


if __name__ == "__main__":
    main()
