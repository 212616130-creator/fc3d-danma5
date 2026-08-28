# -*- coding: utf-8 -*-
"""
福彩3D 选5胆码 — 暴力穷举 + 5胆组合搜索（最新200期）
=============================================
公式池：59特征 × 单/双/三特征线性组合 ≈ 905万规格。
numpy 向量化计算 200 期输出，流式更新（不存池、不去重、内存O(1)）。

【命中定义（与杀一码的核心差异）】
- 单公式胆码命中：公式输出数字 v，命中 = v ∈ 当期开奖3码（百/十/个任一）
- 5胆组命中：选出的 5 条公式输出去重为 5 个不同数字 S，命中 = 开奖3码 ∩ S ≠ ∅

【选胆策略（按优先级）】
1. Top公式单码榜：905万公式逐条算 200期单码胆中命中率，流式维护 Top-50
2. 按数字归并：Top-50 按输出数字分组，每组保留命中率最高者 → 候选数字及最优公式
3. 5胆组合搜索：
   方案A（贪心·推荐）：候选数字按单码命中率降序取前5个不同数字；不足5个用Top榜剩余公式补足
   方案B（穷举·更严）：取 Top-30 公式（输出去重≥6个数字时）穷举 C(30,5) 组合，
                        每组算200期5胆组命中率取最高；并列裁决：组命中率→单码命中率之和→字典序

⚠️ 回测区间与选公式区间重叠，属历史拟合，样本外会回落（页面如实标注）。
"""
import json
import itertools
import numpy as np
from engine import load_data
from formulas import feat_list, iter_specs, formula_name

CSV = 'data/fc3d-history.csv'
WINDOW = 200
TOP_N = 50          # Top榜公式数
COMBO_TOP = 30      # 方案B穷举用 Top-30 公式
NEED_DISTINCT = 6   # 方案B触发条件：Top-30 输出去重 ≥6 个数字


def _eval_out(F, terms, const):
    """向量化计算一组公式在窗口上的输出 (window,) int64"""
    cols = np.array([idx for _, idx in terms], dtype=np.int64)
    coeffs = np.array([c for c, _ in terms], dtype=np.int64)
    out = (F[:, cols] * coeffs).sum(axis=1) + const
    return out % 10


def search_best(hh, tt, oo, window=WINDOW, verbose=True):
    """穷举 905万公式池，返回 dict: 5胆选择全部信息"""
    N = len(hh)
    if N < window + 1:
        raise ValueError(
            f"数据量不足：仅 {N} 期，至少需要 {window+1} 期（{window}期被预测 + 1期上期）。"
            f"请检查 data/fc3d-history.csv 是否被截断或损坏。")
    start = N - window
    if verbose:
        print(f"穷举窗口: 第 {start+1}..{N} 条数据，共 {window} 期")

    # 特征矩阵 (window, NF)
    rows = [
        feat_list(
            hh[start + k - 1], tt[start + k - 1], oo[start + k - 1],
            prev=(hh[start + k - 2], tt[start + k - 2], oo[start + k - 2]) if start + k - 2 >= 0 else None
        )
        for k in range(window)
    ]
    F = np.array(rows, dtype=np.int64)
    # 当期开奖3码（命中判定目标）
    ah = np.array(hh[start:start + window], dtype=np.int64)
    at = np.array(tt[start:start + window], dtype=np.int64)
    ao = np.array(oo[start:start + window], dtype=np.int64)
    # 开奖3码集合：每期命中判定 = 输出 v ∈ {ah,at,ao}
    draw3 = np.stack([ah, at, ao], axis=1)  # (window, 3)

    # ============ 1. Top公式单码榜（流式，不存池）============
    top = []  # 存 (hits, name, digit, neg_len) 按 (hits, -neg_len, name) 排序
    total = 0
    for terms, const in iter_specs():
        out = _eval_out(F, terms, const)
        # 单码胆中：输出 v 出现在当期开奖3码任一
        hits = int((out[:, None] == draw3).any(axis=1).sum())
        total += 1
        if len(top) < TOP_N:
            name = formula_name(terms, const)
            top.append((hits, name, int(out[-1]), -len(name)))
            if len(top) == TOP_N:
                top.sort(key=lambda x: (x[0], x[3], x[1]), reverse=True)
        else:
            # 惰性比较：仅当命中数 ≥ 当前第50名时才拼 name
            if hits > top[-1][0]:
                name = formula_name(terms, const)
                top[-1] = (hits, name, int(out[-1]), -len(name))
                top.sort(key=lambda x: (x[0], x[3], x[1]), reverse=True)

    if verbose:
        print(f"  遍历公式规格: {total:,} 条")
        print(f"  Top-{TOP_N} 榜：单码命中率 {top[0][0]}/{window} ~ {top[-1][0]}/{window}")

    # ============ 2. 按数字归并（Top榜按输出数字分组，每组保留最优公式）============
    best_by_digit = {}   # digit -> (hits, name)
    for hits, name, digit, _neg_len in top:
        if digit not in best_by_digit or hits > best_by_digit[digit][0]:
            best_by_digit[digit] = (hits, name)
    cand_digits = sorted(best_by_digit.keys())          # 候选数字
    cand_hits = {d: best_by_digit[d][0] for d in cand_digits}
    if verbose:
        print(f"  Top榜输出去重 {len(cand_digits)} 个数字: {sorted(cand_digits)}")
    # 全量数字最优公式（补足池，供预测/回测去重兜底：输出不足5个不同数字时按命中率降序补足）
    digit_best = {str(d): {'formula': best_by_digit[d][1], 'hits': best_by_digit[d][0]}
                  for d in cand_digits}

    # ============ 3. 5胆组合搜索 ============
    # 方案A（贪心）：候选数字按单码命中率降序取前5个不同数字
    greedy_digits = sorted(cand_digits, key=lambda d: (-cand_hits[d], d))[:5]
    greedy = [{'digit': d, 'formula': best_by_digit[d][1], 'hits': best_by_digit[d][0]}
              for d in greedy_digits]

    # 方案B（穷举）：Top-30 公式输出去重 ≥6 个数字时，穷举 C(30,5) 组合
    # 硬约束：5 胆必须为 5 个不同数字（Top-30 中重复数字的公式只取数字内命中率最高1条）
    combo_b = None
    if len(cand_digits) >= NEED_DISTINCT:
        top30 = top[:COMBO_TOP]
        # 按数字去重：每个数字只保留 Top-30 内单码命中率最高的一条公式
        best30_by_digit = {}
        for hits, name, digit, _neg in top30:
            if digit not in best30_by_digit or hits > best30_by_digit[digit][0]:
                best30_by_digit[digit] = (hits, name)
        if len(best30_by_digit) >= NEED_DISTINCT:
            combo_b = _exhaustive(F, draw3, best30_by_digit, window, verbose)

    if verbose:
        print(f"  方案A(贪心): {[g['digit'] for g in greedy]}")
        if combo_b:
            print(f"  方案B(穷举): {combo_b['digits']}  5胆组命中 {combo_b['group_hits']}/{window} = {combo_b['group_rate']*100:.2f}%")

    # 最终选择：B 优先（更严，组命中率更高才替换），否则 A
    chosen = combo_b if combo_b and combo_b['group_hits'] > _group_hits(greedy, F, draw3) else greedy
    chosen_rate = _group_hits(chosen, F, draw3) / window

    return {
        'window': window,
        'top50': [{'hits': h, 'name': n, 'digit': d} for h, n, d, _ in top],
        'cand_digits': cand_digits,
        'cand_hits': {str(d): best_by_digit[d][0] for d in cand_digits},
        'digit_best': digit_best,
        'greedy': greedy,
        'combo_b': combo_b,
        'chosen': chosen,
        'chosen_rate': chosen_rate,
        'chosen_hits': int(round(chosen_rate * window)),
        'pool_size': total,
    }, total


def _group_hits(members, F, draw3):
    """给定 5 条公式成员，算 200期 5胆组命中数（开奖3码 ∩ 5胆 ≠ ∅）。
    注：成员必须为 5 个不同数字（选胆硬约束），此处不做校验（由上层保证）。
    兼容传入 dict（方案B的combo_b结构）或 list（方案A的greedy结构）。"""
    if isinstance(members, dict):
        members = members['members']
    out_mat = np.stack([
        _eval_out(F, _parse_terms(m['formula']), _parse_const(m['formula']))
        for m in members
    ], axis=1)                      # (window, 5)
    return int((out_mat[:, :, None] == draw3[:, None, :]).any(axis=(1, 2)).sum())


def _parse_terms(name):
    from formulas import parse_linear
    terms, _ = parse_linear(name)
    return terms


def _parse_const(name):
    from formulas import parse_linear
    _, const = parse_linear(name)
    return const


def _exhaustive(F, draw3, best30_by_digit, window, verbose):
    """方案B：每个数字保留1条最优公式后，穷举 C(D,5) 组合（D=去重后数字数≥6），
    取200期5胆组命中率最高者。并列裁决：组命中率 → 单码命中率之和 → 胆码字典序。
    硬约束：5 胆为 5 个不同数字。"""
    items = [(hits, name, digit) for digit, (hits, name) in sorted(best30_by_digit.items())]
    D = len(items)
    outs = [(hits, name, digit, _eval_out(F, _parse_terms(name), _parse_const(name)))
            for hits, name, digit in items]
    best_combo = None  # (group_hits, sum_single_hits, digits_tuple)
    for combo in itertools.combinations(range(D), 5):
        out_mat = np.stack([outs[i][3] for i in combo], axis=1)  # (window,5)
        gh = int((out_mat[:, :, None] == draw3[:, None, :]).any(axis=(1, 2)).sum())
        sum_single = sum(outs[i][0] for i in combo)
        digits = tuple(sorted(outs[i][2] for i in combo))
        key = (gh, sum_single, digits)
        if best_combo is None or key > best_combo[0]:
            best_combo = (key, combo)
    (gh, ss, digits), combo = best_combo
    return {
        'digits': list(digits),
        'group_hits': gh,
        'group_rate': gh / window,
        'sum_single_hits': ss,
        'members': [{'digit': outs[i][2], 'formula': outs[i][1], 'hits': outs[i][0]} for i in combo],
    }


def main():
    issues, hh, tt, oo = load_data(CSV)
    N = len(issues)
    print(f"数据 {N} 期：{issues[0]} ~ {issues[-1]}")
    best, pool_size = search_best(hh, tt, oo, WINDOW)

    result = {
        'window': WINDOW,
        'data_info': {'n_issues': N, 'first': issues[0], 'last': issues[-1]},
        'pool_size': pool_size,
        'chosen': best['chosen'] if isinstance(best['chosen'], list) else best['chosen']['members'],
        'chosen_rate': round(best['chosen_rate'] * 100, 2),
        'chosen_hits': best['chosen_hits'],
        'cand_digits': best['cand_digits'],
        'cand_hits': best['cand_hits'],
        'digit_best': best['digit_best'],
    }
    with open('best_formula.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n已写入 best_formula.json")
    chosen_members = result['chosen']
    print(f"5胆: {sorted(m['digit'] for m in chosen_members)}  "
          f"5胆组命中 {best['chosen_hits']}/{WINDOW} = {best['chosen_rate']*100:.2f}%"
          f" (随机基线 91.67%)")
    for m in chosen_members:
        print(f"  {m['digit']} <- {m['formula']}  单码胆中 {m['hits']}/{WINDOW} = {m['hits']/WINDOW*100:.2f}%")


if __name__ == '__main__':
    main()
