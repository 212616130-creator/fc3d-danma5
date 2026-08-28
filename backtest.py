# -*- coding: utf-8 -*-
"""
福彩3D 选5胆码 — 回测引擎（固定5胆组回看）
=============================================
固定5条公式（对应5个不同胆码数字），应用到过去N期，逐期真实预测记录。
第 i 期预测仅用第 i-1/i-2 期数据，不偷看未来。结果排序近期→远期。
命中判定：当期开奖 百/十/个 3 码 ∩ 5胆组 ≠ ∅。
【去重兜底】5条公式输出可能撞车（不足5个不同数字），按 digit_best 池
（Top50归并出的全量数字最优公式）命中率降序补足到5个不同数字，回测与预测口径一致。
"""
import json
from engine import load_data, get_next_issue
from formulas import make_predictor


def load_combo(path='best_formula.json'):
    with open(path, 'r', encoding='utf-8') as f:
        d = json.load(f)
    return d['chosen']


def _compile(members):
    return [make_predictor(m['formula']) for m in members]


def _load_digit_best(path='best_formula.json'):
    """Top50归并出的全量数字最优公式池 {digit_str: {'formula','hits'}}，去重兜底用"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d.get('digit_best', {})
    except Exception:
        return {}


def _dedup5(outputs, digit_best):
    """把公式输出列表去重补足为恰好5个不同数字（升序）。
    不足时按 digit_best 池单码命中率降序补足；仍不足（极端）用 0-9 递增补足。"""
    danma = sorted(set(outputs))
    if len(danma) >= 5:
        return danma[:5]
    used = set(danma)
    # 按命中率降序补足（并列按数字升序）
    pool = sorted(digit_best.items(), key=lambda kv: (-kv[1]['hits'], int(kv[0])))
    for digit, info in pool:
        d = int(digit)
        if d not in used:
            danma.append(d)
            used.add(d)
        if len(danma) >= 5:
            break
    d = 0
    while len(danma) < 5:
        if d not in used:
            danma.append(d)
        d += 1
    return sorted(danma)


def run_backtest(csv_path, members, n=200):
    """固定5胆组，逐期回看 n 期。返回 {results(近期→远期), summary}"""
    issues, hh, tt, oo = load_data(csv_path)
    N = len(issues)
    start = max(1, N - n)
    fns = _compile(members)
    digit_best = _load_digit_best()
    results = []
    for i in range(start, N):
        pb, ps, pg = hh[i-1], tt[i-1], oo[i-1]
        # 跨期特征：前2期数据（第i期预测只用第i-1期及更早，不偷看未来）
        prev = (hh[i-2], tt[i-2], oo[i-2]) if i >= 2 else None
        ah, at, ao = hh[i], tt[i], oo[i]
        outputs = [fn(pb, ps, pg, prev) for fn in fns]
        danma = _dedup5(outputs, digit_best)                     # 恰好5个不同数字
        draw = {ah, at, ao}
        hit = bool(draw & set(danma))                                # 开奖3码 ∩ 5胆 ≠ ∅
        results.append({
            'issue': issues[i], 'draw': [ah, at, ao], 'prev_draw': [pb, ps, pg],
            'danma': danma, 'hit': hit,
        })

    total = len(results)
    hits = sum(1 for r in results if r['hit'])
    mx_streak = cur = 0
    for r in results:
        if r['hit']:
            cur = 0
        else:
            cur += 1
            mx_streak = max(mx_streak, cur)
    summary = {
        'hit_rate': round(hits/total*100, 2) if total else 0,
        'total_periods': total, 'hits': hits,
        'max_streak': mx_streak, 'window': f"最近{total}期",
    }
    results.reverse()  # 近期→远期
    return {'results': results, 'summary': summary}


def predict_next(csv_path, members):
    """用最新一期（及前2期）数据预测下一期5胆（去重补足为恰好5个不同数字）"""
    issues, hh, tt, oo = load_data(csv_path)
    latest = issues[-1]
    pb, ps, pg = hh[-1], tt[-1], oo[-1]
    fns = _compile(members)
    prev = (hh[-2], tt[-2], oo[-2]) if len(issues) >= 2 else None
    outputs = [fn(pb, ps, pg, prev) for fn in fns]
    danma = _dedup5(outputs, _load_digit_best())
    return {
        'next_issue': get_next_issue(latest),
        'last_issue': latest,
        'last_draw': [pb, ps, pg],
        'danma': danma,
    }
