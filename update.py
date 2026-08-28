# -*- coding: utf-8 -*-
"""
福彩3D 选5胆码 — 一键更新（本地版，行为与云端 auto_update.py 对齐）
=============================================
流程：联网补抓最新开奖(多源降级+CSV兜底) → 暴力穷举选5胆 → 200期回测
      → 每日预测跟踪(回填/记录) → 生成网页
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

if __name__ == '__main__':
    t0 = time.time()
    print("=" * 46)
    print("  福彩3D 选5胆码 · 一键更新")
    print(f"  时间(北京): {datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 46)

    print("\n[1/4] 同步最新数据（联网补抓 + CSV兜底）")
    try:
        import fetch
        fetch.sync_data()
    except Exception as e:
        print(f"  ⚠ 数据同步异常，沿用现有CSV: {str(e)[:80]}")

    print("\n[2/4] 暴力穷举（最新200期，905万公式选5胆）")
    import bruteforce
    bruteforce.main()

    print("\n[3/4] 每日预测跟踪（回填昨日 + 记录今日，与云端一致）")
    import json, tracker, backtest
    from engine import load_data
    issues, hh, tt, oo = load_data()
    with open('best_formula.json', 'r', encoding='utf-8') as f:
        bf = json.load(f)
    members = bf['chosen']
    pred = backtest.predict_next('data/fc3d-history.csv', members)
    issues_map = {iss: [b, s, g] for iss, b, s, g in zip(issues, hh, tt, oo)}
    filled = tracker.backfill(issues_map)
    recorded = tracker.record_prediction(pred['next_issue'], pred['danma'])
    print(f"  {'✓ 已回填 ' + str(filled) + ' 期' if filled else '  - 无待回填'}")
    print(f"  {'✓ 已记录 ' + pred['next_issue'] + ': ' + str(pred['danma']) if recorded else '  - 预测已存在（幂等）'}")

    print("\n[4/4] 生成网页（200期回测 + 预测跟踪）")
    import os, shutil, gen_site
    os.makedirs('static', exist_ok=True)
    gen_site.main(out_path='static/index.html')  # 与云端auto_update.py输出路径统一
    shutil.copy('static/index.html', 'index.html')  # 同步根目录，两个预览地址都是最新

    print(f"\n完成 ✓  总耗时 {time.time()-t0:.1f} 秒")
    print(f"本地预览: http://127.0.0.1:8899/index.html  (或 /static/index.html)")
