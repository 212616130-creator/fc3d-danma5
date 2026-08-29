# -*- coding: utf-8 -*-
"""
福彩3D 选5胆码 — 云端全自动更新入口（GitHub Actions 定时运行）
=============================================
流程：多源降级抓取最新开奖 → 追加到CSV（自动补新期） → 暴力穷举选5胆
      → 200期回测 → 每日预测跟踪(回填昨日/记录今日) → 生成 static/index.html
幂等设计：数据与5胆组均无变化时**不重写页面**（含时间戳），
         workflow 的 git diff 检测不到任何变化即跳过提交与部署，零无效更新。
"""
import sys, io, os, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)  # 保证 data/ static/ 相对路径正确

OUT_HTML = 'static/index.html'
ROOT_HTML = 'index.html'  # GitHub Pages legacy 来源 = main 分支根目录，必须同步
COMBO_JSON = 'best_formula.json'
TRACK_PATH = 'data/predictions.jsonl'


def main():
    t0 = time.time()
    print("=" * 46)
    print("  福彩3D 选5胆码 · 云端全自动更新")
    print(f"  时间(北京): {datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 46)

    print("\n[1/5] 多源降级抓取 + 追加CSV")
    added = 0
    try:
        import fetch
        _, added = fetch.sync_data()
    except Exception as e:
        print(f"  ⚠ 数据同步异常，沿用现有CSV: {str(e)[:80]}")

    print("\n[2/5] 暴力穷举（最新200期，905万公式选5胆）")
    import bruteforce
    from engine import load_data
    issues, hh, tt, oo = load_data()
    best, pool_size = bruteforce.search_best(hh, tt, oo, bruteforce.WINDOW)
    # chosen 可能是 list（方案A）或 dict（方案B含members），统一归一化为成员列表
    new_combo = best['chosen'] if isinstance(best['chosen'], list) else best['chosen']['members']
    new_chosen_sig = [(m['digit'], m['formula']) for m in new_combo]

    # 判断5胆组是否变化（对比旧 best_formula.json）
    old_chosen_sig = None
    try:
        with open(COMBO_JSON, 'r', encoding='utf-8') as f:
            old_chosen_sig = [(m['digit'], m['formula']) for m in json.load(f).get('chosen', [])]
    except Exception:
        pass
    combo_changed = (old_chosen_sig != new_chosen_sig)

    # 下期预测（开奖前落盘用）
    import backtest
    pred = backtest.predict_next('data/fc3d-history.csv', new_combo)

    print("\n[3/5] 每日预测跟踪（回填昨日 + 记录今日）")
    import tracker
    # 1) 回填：已记录的预测，若对应期已开奖，补真实开奖与命中
    issues_map = {iss: [b, s, g] for iss, b, s, g in zip(issues, hh, tt, oo)}
    filled = tracker.backfill(issues_map, TRACK_PATH)
    if filled:
        print(f"  ✓ 已回填 {filled} 期预测结果")
    # 2) 记录：下期预测落盘（同 issue 已存在则跳过，幂等）
    recorded = tracker.record_prediction(pred['next_issue'], pred['danma'], TRACK_PATH)
    if recorded:
        print(f"  ✓ 已记录预测 {pred['next_issue']}: {pred['danma']}")
    else:
        print(f"  - 预测 {pred['next_issue']} 已存在，跳过（幂等）")
    track_summary = tracker.summary(TRACK_PATH)

    # 页面是否需要重建：数据新增 / 5胆组变化 / 回填或新记录发生
    track_changed = (filled > 0 or recorded)
    force_rebuild = os.environ.get('FORCE_REBUILD', '0') == '1'
    if force_rebuild:
        print("\n[4/5] FORCE_REBUILD=1，强制重建页面")
    elif added == 0 and not combo_changed and not track_changed:
        print("\n[4/5] 数据/5胆组/预测跟踪均无变化，跳过页面生成（零无效更新）")
    else:
        print("\n[4/5] 200期回测 + 生成网页")
        result = {
            'window': bruteforce.WINDOW,
            'data_info': {'n_issues': len(issues), 'first': issues[0], 'last': issues[-1]},
            'pool_size': pool_size,
            'chosen': new_combo,
            'chosen_rate': round(best['chosen_rate'] * 100, 2),
            'chosen_hits': best['chosen_hits'],
            'cand_digits': best.get('cand_digits', []),
            'cand_hits': best.get('cand_hits', {}),
            'digit_best': best.get('digit_best', {}),
        }
        with open(COMBO_JSON, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  已写入 {COMBO_JSON}（5胆组变化: {combo_changed}, 新增数据: {added}期）")
        os.makedirs('static', exist_ok=True)
        import gen_site
        gen_site.main(out_path=OUT_HTML)
        # 同步根目录 index.html：GitHub Pages legacy 来源是 main 分支根目录，不同步则线上 404/0字节
        import shutil
        shutil.copy(OUT_HTML, ROOT_HTML)

    print("\n[5/5] 完成")
    print(f"  预测跟踪: 累计 {track_summary['total']} 期已开奖, 真实命中 {track_summary['hits']} 期 = {track_summary['rate']}%")
    print(f"  总耗时 {time.time()-t0:.1f} 秒")


if __name__ == '__main__':
    main()
