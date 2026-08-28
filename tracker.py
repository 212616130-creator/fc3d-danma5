# -*- coding: utf-8 -*-
"""
福彩3D 选5胆码 — 每日预测跟踪（真正的样本外记录）
=============================================
核心思想：预测必须在开奖前落盘（防止事后编造），开奖后自动回填结果。
数据文件 predictions.jsonl，每行一条：

  {"issue":"2026230","danma":[1,5,6,7,9],"predicted_at":"2026-08-28 22:00",
   "draw":[8,2,8],"filled_at":"2026-08-29 01:00","hit":true}

- 记录时机：云端 auto_update 每次运行时，把「下期预测」写入（已存在同 issue 则跳过，幂等）
- 回填时机：下次运行时，对已记录但未回填的预测，用最新开奖数据补 draw/hit
- 页面展示：累计真实命中率 + 近30期明细（近期→远期）
"""
import json
import os

TRACK_PATH = 'data/predictions.jsonl'


def load_track(path=TRACK_PATH):
    """读取全部跟踪记录，按期号升序返回列表"""
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def save_track(rows, path=TRACK_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for r in sorted(rows, key=lambda x: x['issue']):
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def backfill(issues_map, path=TRACK_PATH):
    """回填：用最新开奖数据补全已记录但未回填的预测。返回回填条数。
    issues_map: {issue_str: [b,s,g]}，只含已开奖期"""
    rows = load_track(path)
    filled = 0
    for r in rows:
        if 'draw' in r and 'hit' in r:
            continue  # 已回填
        draw = issues_map.get(r['issue'])
        if draw is None:
            continue  # 还没开奖
        r['draw'] = draw
        r['hit'] = bool(set(draw) & set(r['danma']))  # 开奖3码 ∩ 5胆 ≠ ∅
        r['filled_at'] = __import__('datetime').datetime.now(
            __import__('datetime').timezone(__import__('datetime').timedelta(hours=8))
        ).strftime('%Y-%m-%d %H:%M')
        filled += 1
    if filled:
        save_track(rows, path)
    return filled


def record_prediction(issue, danma, path=TRACK_PATH):
    """记录一期预测（开奖前落盘）。已存在同 issue 则跳过（幂等）。返回是否新增"""
    rows = load_track(path)
    existing = {r['issue'] for r in rows}
    if issue in existing:
        return False
    from datetime import datetime, timezone, timedelta
    rows.append({
        'issue': issue,
        'danma': sorted(danma),
        'predicted_at': datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M'),
    })
    save_track(rows, path)
    return True


def summary(path=TRACK_PATH):
    """汇总：已回填的真实命中统计（只算有开奖结果的）"""
    rows = [r for r in load_track(path) if 'hit' in r]
    if not rows:
        return {'total': 0, 'hits': 0, 'rate': 0.0, 'max_streak': 0, 'recent': []}
    hits = sum(1 for r in rows if r['hit'])
    mx = cur = 0
    for r in rows:
        if r['hit']:
            cur = 0
        else:
            cur += 1
            mx = max(mx, cur)
    recent = sorted(rows, key=lambda x: x['issue'], reverse=True)[:30]  # 近期→远期
    recent = [{
        'issue': r['issue'], 'danma': r['danma'],
        'draw': r.get('draw'), 'hit': r.get('hit'),
        'predicted_at': r.get('predicted_at', ''),
    } for r in recent]
    return {
        'total': len(rows), 'hits': hits,
        'rate': round(hits / len(rows) * 100, 2),
        'max_streak': mx, 'recent': recent,
    }
