from collections import defaultdict, Counter
from itertools import accumulate, groupby
from pathlib import Path
import csv,json,re

ROOT = Path(__file__).resolve().parent
def loadfile(path):
    return json.loads(path.read_text(encoding='utf-8'))
def write(out,name,rows,fields=None):
    cols=fields or list(dict.fromkeys(k for r in rows for k in r))
    with (out/(name+'.csv')).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def period(label):
    match = re.fullmatch(r'(Q|X|EQ)([1-9]\d*)', label.upper())
    if not match:
        raise ValueError(f'알 수 없는 쿼터 코드 ({label})')
    return int(match[2]) + (0 if match[1] == 'Q' else 4)
def norm(v):return ''.join((v or '').split())
def minutes(quarter):return 600 if quarter<=4 else 300
def day(s):return s[:4]+'-'+s[4:6]+'-'+s[6:8]
labels=loadfile(ROOT/'codebook.json')

def load_profiles(raw):
    heights = {}
    registration = loadfile(raw / 'registration.json') if (raw / 'registration.json').exists() else {}
    registered = {str(player['playerNo']): player for player in registration.get('players', [])}
    for file in sorted(raw.glob('profile_*.json')):
        for player in loadfile(file).get('playerInfo', []):
            height = str(player.get('pHeight') or '')
            if re.fullmatch(r'\d+(?:\.\d+)?', height):
                heights[str(player['playerNo'])] = (
                    float(height), None, 'kbl_public_player_profile'
                )
    for pid, player in registered.items():
        height = str(player.get('pHeight') or '')
        if re.fullmatch(r'\d+(?:\.\d+)?', height):
            year = str(player.get('yearNo') or '').strip()
            heights[pid] = (
                float(height), int(year) if re.fullmatch(r'\d{4}', year) else None,
                'kbl_public_registration',
            )
    for file in sorted(raw.glob('draft_*.json')):
        pid = file.stem.split('_')[-1]
        years = {str(row.get('yearNo') or '').strip() for row in loadfile(file)}
        years = {int(year) for year in years if re.fullmatch(r'\d{4}', year)}
        if len(years) == 1:
            height, known_year, source = heights.get(pid, (None, None, None))
            heights[pid] = (height, known_year or years.pop(), source)
    return heights, registered, registration.get('date')

def rookie_flag(previous_seasons,pid,draft,category,season_year):
    if category!='국내':return None
    if draft:return int(draft==season_year)
    if previous_seasons.get(pid,9999)<season_year:return 0
    return None
def roster_moves(players,gm,as_of):
    names=defaultdict(set)
    for pid,r in players.items():
        names[norm(r['player_name'])].add(pid)
    if '291626' in players:
        names[norm('재로드 존스')].add('291626')
    result=[]
    f=ROOT/'roster_moves_evidence.tsv'
    if not f.exists():return result
    for i,row in enumerate(csv.reader(f.read_text(encoding='utf-8').splitlines(),delimiter='\t'),1):
        dt,kind,name,old,new,replaced,date_basis,link=row
        if dt > as_of.isoformat():
            continue
        ids=names[norm(name)]
        if len(ids)!=1:
            print('Roster player needs identification',name,ids)
            continue
        matches=names[norm(replaced)]
        game=next((g['game_id'] for g in gm if g['date']==dt and (new or old) in [g['home_team_id'],g['away_team_id']]),None) if date_basis in {'game_date','first_game'} else None
        result.append(dict(move_id=i,date=dt,date_basis=date_basis,event_type=kind,game_id=game,player_id=next(iter(ids)),player_name=name,from_team_id=old,to_team_id=new,related_player_id=next(iter(matches)) if len(matches)==1 else None,related_player_name=replaced,source_url=link))
    return result
points={'201':2,'203':1,'205':3,'207':2}
kinds=dict(zip('001 002 003 009 010 101 102 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 217 218 219 221 223 224 225 226 227 228 229'.split(),'period_start suspension timeout period_end clock_adjustment sub_in sub_out fg2_made fg2_missed ft_made ft_missed fg3_made fg3_missed dunk_made dunk_missed offensive_rebound defensive_rebound assist steal block turnover shooting_or_bonus_foul non_ft_foul fast_break team_rebound illegal_defense good_defense team_turnover other_foul team_foul screen_assist deflection video_review coach_challenge'.split()))
def free_throws(rows):
    # Only assign an inferred trip after a single explicit triggering foul.
    pending=[]; foul=False
    def finish():
        if foul and 1<=len(pending)<=3 and len({r['player_id'] for r in pending})==1 and pending[0]['player_id']:
            for j,r in enumerate(pending,1):r.update(ft_attempt=j,ft_total=len(pending),ft_source='inferred_from_foul_sequence')
    for r in rows:
        k=r['action_code']
        if k in {'203','204'}:
            pending.append(r)
        elif k in {'101','102','003','225','228','229','002','010'}: continue
        elif k in {'215','224'}:
            finish();pending=[];foul=True
        else:
            finish();pending=[];foul=False
    finish()
def lineup_signature(rows, clocks, home, away, initial_time):
    """Compare the interval boundaries, players and scoring under two clock treatments."""
    lineup = {home: set(), away: set()}
    remaining = initial_time
    intervals = []

    def add_interval(end, home_points=0, away_points=0):
        nonlocal remaining
        if remaining == end and not (home_points or away_points):
            return
        players = tuple(tuple(sorted(lineup[team])) for team in (home, away))
        if not intervals or intervals[-1][0] != players:
            intervals.append([players, remaining, end, 0, 0])
        intervals[-1][2] = end
        intervals[-1][3] += home_points
        intervals[-1][4] += away_points
        remaining = end

    for row, clock in zip(rows, clocks, strict=True):
        team, points, player = row['team_id'], row['points'], row['player_id']
        add_interval(clock, points if team == home else 0, points if team == away else 0)
        if team not in lineup or not player:
            continue
        if row['event_type'] == 'sub_in':
            lineup[team].add(player)
        elif row['event_type'] == 'sub_out':
            lineup[team].discard(player)
    add_interval(0)
    return intervals


def process(games, raw, out, as_of):
    heights, registered, registration_date = load_profiles(raw)
    previous_seasons = {}
    if (raw / 'prev24.json').exists():
        previous_seasons = {
            str(row['player']['pcode']): 2024 for row in loadfile(raw / 'prev24.json')
            if row.get('gameCount', 0) > 0
        }
    gm=[]; events=defaultdict(list);box=[]; starters=[];stints=[]; players={};members={}; audit=[]
    for g in games:
        key=g['gmkey']; season=g['seasonName1'];h=g['tcodeH'];a=g['tcodeA']
        eventfile=raw/(key+'_text-cast.json');boxfile=raw/(key+'_player-stat.json')
        es=loadfile(eventfile) if eventfile.exists() else []
        periods=sorted(set(period(v['q']) for v in es))
        complete=bool(boxfile.exists() and periods[:4]==[1,2,3,4])
        gm.append(dict(game_id=key,season=season,date=day(g['gameDate']),home_team_id=h,home_team=g['tnameH'],away_team_id=a,away_team=g['tnameA'],home_score=g['scoreH'],away_score=g['scoreA'],overtimes=max(periods)-4 if complete else None,game_type=g['seasonCategoryName']))
        if not complete:
            raise ValueError(f'{key}: 경기 원본이 불완전합니다.')
        mapping=defaultdict(set); btimes={}; official_starters=set()
        for v in loadfile(boxfile):
            p=v['player'];pid=str(p['pcode']);t=p['tcode'];name=p['pname'];rec=v.get('records') or {}
            for val in [name,p.get('ename')]:
                if val:mapping[t,norm(val)].add(pid)
            sec=60*(rec.get('playMin') or 0)+(rec.get('playSec') or 0)
            btimes[pid]=sec
            if str(v.get('startFlag')) == '1':
                official_starters.add((t, pid))
            box.append(dict(game_id=key,team_id=t,player_id=pid,player_name=name,started=v.get('startFlag'),minutes_seconds=sec if rec else None,**rec))
            height,draft,profile_source=heights.get(pid,(None,None,None))
            if sec>0:
                previous_seasons[pid]=min(previous_seasons.get(pid,9999),int(season[:4]))
            category={'0':'국내','1':'외국','2':'아시아쿼터'}.get(str(p.get('playerFlag')))
            rookie=rookie_flag(previous_seasons,pid,draft,category,int(season[:4]))
            meta=dict(player_id=pid,player_name=name,team_id=t,team_name=p['tname'],position=p.get('pos'),height_cm=height,profile_source=profile_source,draft_year=draft,player_category=category,rookie=rookie)
            players[pid]=dict(**meta,as_of_season=season,as_of_date=day(g['gameDate']))
            mem=members.setdefault((season,pid,t),dict(**meta,season=season,first_game_id=key,last_game_id=key));mem['last_game_id']=key
        sc={h:0,a:0};seq=0; game_st=[]; qerrors=[]; n_missing=0; bench_staff=0; game_start=len(starters); tsec=Counter(); issue_sub=0
        clock_sensitive = []
        max_clock_increase = 0
        dismissal_followups = 0
        invalid_clocks = 0
        markers_ok = periods == list(range(1, max(periods) + 1))
        for q,pg in groupby(es,lambda v:period(v['q'])):
            lineup={h:set(),a:set()};remaining=minutes(q); qr=[];qst=[];start_captured=False; clock_error=False
            dismissed_at = {}
            markers = Counter()
            def capture():
                nonlocal start_captured
                for t in [h,a]:
                    for pid in sorted(lineup[t]):
                        starters.append(dict(game_id=key,quarter=q,team_id=t,player_id=pid,verified_five=int(len(lineup[t])==5)))
                start_captured=True
            def segment(end,delta_h=0,delta_a=0):
                nonlocal remaining
                if end>remaining:
                    return
                if remaining==end and not (delta_h or delta_a):return
                line=tuple(tuple(sorted(lineup[t])) for t in [h,a])
                if not qst or line!=qst[-1][0]:
                    qst.append([line,remaining,end,0,0,seq,seq])
                qst[-1][2]=end;qst[-1][3]+=delta_h;qst[-1][4]+=delta_a;qst[-1][6]=seq;remaining=end
            for v in pg:
                seq+=1;k=v['a'];t=v['t'];p=v.get('p'); matches=mapping[t,norm(p)]
                if len(matches)>1 and v.get('e'):matches=matches & mapping[t,norm(v['e'])]
                if not matches and v.get('e'):matches=mapping[t,norm(v['e'])]
                pid=next(iter(matches)) if len(matches)==1 else None
                staff=bool(k=='224' and p and not pid)
                bench_staff+=int(staff)
                n_missing+=int(bool(p and not pid and not staff))
                clock=v['m']*60+v['s'];dt=points.get(k,0)
                invalid_clocks += int(not 0 <= clock <= minutes(q))
                max_clock_increase = max(max_clock_increase, clock - remaining)
                if clock > remaining:
                    clock_error = True
                if k in {'001', '009'}:
                    markers[k] += 1
                if not start_captured and (clock<minutes(q) or dt):capture()
                segment(max(0,min(clock,remaining)),dt if t==h else 0,dt if t==a else 0)
                if t in sc:sc[t]+=dt
                if k in {'101','102'} and t in lineup:
                    if not pid:issue_sub+=1
                    elif k=='101':
                        if pid in lineup[t]:issue_sub+=1
                        lineup[t].add(pid)
                    else:
                        if pid not in lineup[t]:
                            if v.get('c') == '106_2' and dismissed_at.get((t, pid)) == clock:
                                dismissal_followups += 1
                            else:
                                issue_sub += 1
                        elif v.get('c') == '106_1':
                            dismissed_at[t, pid] = clock
                        lineup[t].discard(pid)
                act=labels['action'].get(k,'')
                foul=labels['foul'].get(v.get('f'),v.get('f',''))
                change=labels['sub'].get(v.get('c'),'')
                text=' '.join(x for x in [p,act,labels['foul'].get(v.get('f')),change] if x)
                qr.append(dict(game_id=key,seq=seq,source_seq=v['n'],quarter=q,clock_seconds=clock,team_id=t,player_id=pid,player_name=p,actor_type='non_player' if staff else ('player' if pid else ('unmatched' if p else ('team' if t else 'game'))),event_type=kinds.get(k,'unmapped'),action_code=k,action_ko=act,points=dt,foul_type=foul or (act if k in {'215','216','224','225'} else ''),ft_attempt=None,ft_total=None,ft_source='unknown' if k in {'203','204'} else '',in_player_id=pid if k=='101' else None,out_player_id=pid if k=='102' else None,home_score=sc[h],away_score=sc[a],raw_text=text,raw_event=json.dumps(v,ensure_ascii=False,separators=(',',':'))))
            if not start_captured:capture()
            segment(0)
            markers_ok = markers_ok and markers == {'001': 1, '009': 1}
            if clock_error:
                qerrors.append(q)
                clocks = [max(0, min(minutes(q), row['clock_seconds'])) for row in qr]
                forward = list(accumulate(clocks, min))
                backward = list(reversed(list(accumulate(reversed(clocks), max))))
                if lineup_signature(qr, forward, h, a, minutes(q)) != lineup_signature(
                    qr, backward, h, a, minutes(q)
                ):
                    clock_sensitive.append(q)
            free_throws(qr);events[season].extend(qr)
            offset=600*min(q-1,4)+max(q-5,0)*300
            for line,u,v,dh,da,start_seq,end_seq in qst:
                lh,la=line
                for pid in lh+la:tsec[pid]+=u-v
                game_st.append(dict(game_id=key,stint_id=len(game_st)+1,quarter=q,start_seq=start_seq,end_seq=end_seq,start_clock_seconds=u,end_clock_seconds=v,start_elapsed_seconds=offset+minutes(q)-u,end_elapsed_seconds=offset+minutes(q)-v,duration_seconds=u-v,home_players='|'.join(lh),away_players='|'.join(la),home_points=dh,away_points=da,point_diff=dh-da,lineup_5v5=int(len(lh)==len(la)==5)))
        maxdiff = max((abs(tsec[p] - sec) for p, sec in btimes.items()), default=0)
        score_ok = int(sc[h] == g['scoreH'] and sc[a] == g['scoreA'])
        game_starters = starters[game_start:]
        q1_ok = {
            (row['team_id'], row['player_id']) for row in game_starters if row['quarter'] == 1
        } == official_starters
        starters_ok = len(game_starters) == len(periods) * 10 and all(
            row['verified_five'] for row in game_starters
        )
        non_5v5 = sum(1 - row['lineup_5v5'] for row in game_st)
        source_numbers = [int(row['n']) for row in es]
        source_gaps = sum(max(0, second - first - 1) for first, second in zip(source_numbers, source_numbers[1:]))
        reasons = [
            reason for check, reason in [
                (not score_ok, 'score_mismatch'),
                (not markers_ok, 'period_markers_missing'),
                (invalid_clocks, 'clock_out_of_range'),
                (not starters_ok or not q1_ok, 'starter_mismatch'),
                (non_5v5, 'non_5v5_lineup'),
                (n_missing, 'unresolved_player'),
                (issue_sub, 'substitution_unresolved'),
                (clock_sensitive, 'clock_sensitive_stints'),
                (maxdiff != 0, 'box_minutes_mismatch'),
            ] if check
        ]
        ok = int(not reasons)
        for segment_row in game_st:
            segment_row['game_verified'] = ok
        stints.extend(game_st)
        audit.append(dict(
            game_id=key,event_count=seq,quarter_count=len(periods),non_player_fouls=bench_staff,
            unresolved_player_events=n_missing,score_ok=score_ok,non_5v5_stints=non_5v5,
            clock_corrections='|'.join(map(str,qerrors)),substitution_issues=issue_sub,
            starter_rows=len(game_starters),max_box_seconds_difference=maxdiff,game_verified=ok,
            max_clock_increase_seconds=max_clock_increase,
            post_foul_out_disqualification_events=dismissal_followups,
            clock_sensitive_stint_quarters='|'.join(map(str,clock_sensitive)),
            period_markers_ok=int(markers_ok),q1_starters_ok=int(q1_ok),
            out_of_range_clock_events=invalid_clocks,
            source_seq_gaps=source_gaps, pbp_home_score=sc[h],pbp_away_score=sc[a],
            review_reason='|'.join(reasons),
        ))
    teams={g[f'{side}_team_id']:g[f'{side}_team'] for g in gm for side in ['home','away']}
    if registration_date and registration_date > as_of.isoformat():
        registered = {}
    registration_season = '2026-2027' if registration_date and registration_date >= '2026-10-03' else '2025-2026'
    for pid,p in registered.items():
        h,draft,source=heights.get(pid,(None,None,None))
        t=p['teamCode']
        flag={'0':'국내','1':'외국','2':'아시아쿼터'}.get(str(p.get('playerFlagCode2')))
        if pid not in players:
            players[pid]=dict(player_id=pid,player_name=p['kname'],team_id=t,team_name=teams.get(t),
                              position=p.get('pos'),height_cm=h,profile_source=source,draft_year=draft,
                              player_category=flag,rookie=rookie_flag(previous_seasons,pid,draft,flag,int(registration_season[:4])),
                              as_of_season=registration_season,as_of_date=registration_date,team_basis='current_registration')
        else:
            players[pid].update(team_id=t,team_name=teams.get(t),position=p.get('pos'),player_category=flag or players[pid]['player_category'],team_basis='current_registration',
                                as_of_season=registration_season,as_of_date=registration_date,rookie=rookie_flag(previous_seasons,pid,draft,flag,int(registration_season[:4])))
    for player in players.values():
        player.setdefault('team_basis','latest_boxscore')
    write(out,'games',gm)
    for season,ev in events.items():
        if season=='2025-2026':
            for half,test in [(1,lambda n:n<=135),(2,lambda n:n>135)]:
                write(out,f'pbp_{season}_part{half}',[r for r in ev if test(int(r['game_id'].split('N')[-1]))])
        else:
            write(out,'pbp_'+season,ev)
    write(out,'boxscores',box);write(out,'quarter_starters',starters);write(out,'stints',stints);write(out,'players',list(players.values()));write(out,'player_teams',list(members.values()));write(out,'quality',audit)
    write(out,'roster_moves',roster_moves(players,gm,as_of))
    game_map = {row['game_id']: row for row in gm}
    review_fields = ['game_id', 'date', 'home_team', 'away_team', 'home_score', 'away_score',
                     'pbp_home_score', 'pbp_away_score', 'source_seq_gaps', 'max_clock_increase_seconds',
                     'clock_sensitive_stint_quarters', 'max_box_seconds_difference', 'review_reason']
    write(out,'quality_review', [
        {field: (row | game_map[row['game_id']])[field] for field in review_fields}
        for row in audit if row['review_reason']
    ], review_fields)
    write(out,'stint_players',[dict(game_id=r['game_id'],stint_id=r['stint_id'],side=k,player_id=p) for r in stints for k in ['home','away'] for p in r[k+'_players'].split('|') if p])
    print(len(gm),len(audit),sum(len(v) for v in events.values()),len(stints),Counter(r['game_verified'] for r in audit),Counter(r['score_ok'] for r in audit),flush=True)

