# -*- coding: utf-8 -*-
"""
福彩3D 选5胆码 — 生成自包含本地网页
风格复刻 D:\\新版百十个\\index.html（紫渐变移动端480px），适配选5胆码。
数据以 const P = {...} 内嵌 JSON。
"""
import json
import datetime
from datetime import timezone, timedelta
import backtest
from engine import load_data

BJT = timezone(timedelta(hours=8))

CSV_PATH = 'data/fc3d-history.csv'

# 特征名 → 白话说明
FEAT_ZH = {
    'b': '上期百位', 's': '上期十位', 'g': '上期个位',
    'b2': '百位²尾', 's2': '十位²尾', 'g2': '个位²尾',
    'b3': '百位³尾', 's3': '十位³尾', 'g3': '个位³尾',
    'S': '和值', 'S10': '和尾', 'P': '跨度', 'mx': '最大码', 'mn': '最小码', 'md': '中间码',
    'd1': '|百-十|', 'd2': '|百-个|', 'd3': '|十-个|',
    'bs': '百×十尾', 'bg': '百×个尾', 'sg': '十×个尾', 'bsg': '三码积尾',
    'S2': '和值²尾', 'P2': '跨度²尾',
    'sum2': '(百+十)尾', 'sum3': '(十+个)尾', 'sum4': '(百+个)尾',
    'bp': '百^个尾', 'gp': '个^百尾', 'sp': '十^个尾',
    'bo': '百奇偶', 'so': '十奇偶', 'go': '个奇偶', 'So': '和奇偶',
    'd12': '|百-十|×|百-个|尾', 'd13': '|百-十|×|十-个|尾', 'd23': '|百-个|×|十-个|尾',
    'mxmn': '大×小尾', 'mxmd': '大+中', 'mnmd': '小+中',
    'S3': '和值³尾', 'dsum': '三差值和', 'bsg2': '两两积和尾',
    'bL': '前2期百位', 'sL': '前2期十位', 'gL': '前2期个位',
    'SL': '前2期和值', 'S10L': '前2期和尾', 'PL': '前2期跨度',
    'db': '百位较前2期差', 'ds': '十位较前2期差', 'dg': '个位较前2期差',
    'dS': '和值较前2期差',
    'bh': '近2期百位和尾', 'sh': '近2期十位和尾', 'gh': '近2期个位和尾',
    'bpr': '近2期百位积尾', 'spr': '近2期十位积尾', 'gpr': '近2期个位积尾',
}


def explain(formula):
    parts = []
    for seg in formula.split('+'):
        seg = seg.strip()
        if '*' in seg:
            c, f = seg.split('*', 1)
            zh = FEAT_ZH.get(f, f)
            parts.append(zh if c == '1' else f'{c}×{zh}')
        elif seg.isdigit():
            if seg != '0':
                parts.append(seg)
        else:
            parts.append(FEAT_ZH.get(seg, seg))
    return ' + '.join(parts) + '，取个位( mod 10 )'


def build_data():
    with open('best_formula.json', 'r', encoding='utf-8') as f:
        bf = json.load(f)
    members = bf['chosen']
    issues, hh, tt, oo = load_data(CSV_PATH)
    latest = issues[-1]
    last_draw = ''.join(map(str, [hh[-1], tt[-1], oo[-1]]))

    bt200 = backtest.run_backtest(CSV_PATH, members, n=200)
    pred = backtest.predict_next(CSV_PATH, members)
    s200 = bt200['summary']
    rows = [{
        'issue': r['issue'], 'draw': ''.join(map(str, r['draw'])),
        'danma': r['danma'], 'hit': r['hit'],
    } for r in bt200['results']]

    return {
        'data_info': {'n_issues': len(issues), 'first': issues[0], 'last': issues[-1]},
        'next_issue': pred['next_issue'],
        'last_issue': pred['last_issue'],
        'last_draw': last_draw,
        'updated': datetime.datetime.now(BJT).strftime('%Y-%m-%d %H:%M'),
        'pool_size': bf.get('pool_size'),
        'danma': pred['danma'],
        'members': [{'digit': m['digit'], 'formula': m['formula'], 'hits': m['hits'],
                     'rate': round(m['hits'] / 200 * 100, 2), 'explain': explain(m['formula'])}
                    for m in members],
        's200': {'hit_rate': s200['hit_rate'], 'total': s200['total_periods'],
                 'hits': s200['hits']},
        'max_streak': s200['max_streak'],
        'baseline': 91.67,   # 5胆命中随机基线 1 - C(5,3)/C(10,3)
        'rows': rows,
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>福彩3D 选5胆码 · 暴力穷举200期</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; color: #333; }
.container { max-width: 480px; margin: 0 auto; padding: 10px; }
.header { background: linear-gradient(135deg, #5b3cc4 0%, #7b5fe0 100%); color: #fff; padding: 14px 16px; border-radius: 10px; margin-bottom: 10px; }
.header h1 { font-size: 1.1rem; }
.header .sub { font-size: .72rem; opacity: .85; margin-top: 2px; line-height: 1.5; }
.banner { background: #fff8e1; border: 1.5px solid #ffc107; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 8px; }
.banner .issue { font-size: 1.4rem; font-weight: 700; color: #e65100; }
.banner .last { font-size: .75rem; color: #856404; margin-top: 2px; }
.banner .time { font-size: .65rem; color: #999; }
.danma-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-bottom: 8px; }
.danma-card { background: #fff; border-radius: 8px; padding: 10px 4px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.danma-card .pos-label { font-size: .68rem; color: #888; }
.danma-card .num { width: 44px; height: 44px; border-radius: 10px; display: inline-flex; align-items: center; justify-content: center; font-size: 1.45rem; font-weight: 700; background: #e8eaf6; color: #3f51b5; margin-top: 6px; }
.danma-card .rate { font-size: .58rem; color: #999; margin-top: 4px; }
.stats { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 4px; margin-bottom: 8px; }
.stat { background: #fff; border-radius: 6px; padding: 8px 4px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,.05); }
.stat .val { font-size: 1.1rem; font-weight: 700; }
.stat .val.g { color: #2e7d32; }
.stat .val.o { color: #e65100; }
.stat .lbl { font-size: .62rem; color: #999; margin-top: 1px; }
.stat-main { background: #e8f5e9; }
.stat-main .val { font-size: 1.25rem; }
.table-wrap { background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.06); margin-bottom: 8px; }
.table-wrap h3 { font-size: .85rem; padding: 8px 12px; border-bottom: 1px solid #eee; }
.scroll { max-height: 440px; overflow: auto; -webkit-overflow-scrolling: touch; }
.tbl { width: 100%; border-collapse: collapse; font-size: .7rem; }
.tbl th { background: #fafafa; position: sticky; top: 0; padding: 6px 4px; font-size: .64rem; color: #666; white-space: nowrap; }
.tbl td { padding: 5px 3px; text-align: center; border-bottom: 1px solid #f0f0f0; }
.tbl td.danma { font-weight: 700; color: #3f51b5; }
.tr-hit { border-left: 3px solid #4caf50; }
.tr-miss { border-left: 3px solid #f44336; }
.badge-y { color: #2e7d32; font-weight: 700; }
.badge-n { color: #c62828; font-weight: 700; }
.info { background: #fff; border-radius: 8px; padding: 12px; box-shadow: 0 1px 4px rgba(0,0,0,.06); margin-bottom: 8px; }
.info h3 { font-size: .85rem; margin-bottom: 6px; }
.algo { font-size: .68rem; padding: 6px 8px; background: #f5f5f5; border-radius: 4px; line-height: 1.6; margin-bottom: 5px; }
.algo b { color: #5b3cc4; }
.algo .f { color: #333; }
.algo .zh { color: #999; font-size: .64rem; display: block; margin-top: 2px; }
.foot { text-align: center; font-size: .65rem; color: #bbb; padding: 10px 0; line-height: 1.6; }
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>福彩3D 选5胆码</h1>
  <div class="sub">暴力穷举 · 只参考最新200期 · 905万公式选5胆 · 纯本地网页</div>
</div>
<div class="banner">
  <div class="issue" id="predIssue">-</div>
  <div class="last" id="lastInfo"></div>
  <div class="time" id="updateTime"></div>
</div>
<div class="danma-grid" id="danmaGrid"></div>
<div class="stats">
  <div class="stat stat-main"><div class="val g" id="sRate">-</div><div class="lbl">★5胆命中(近200)</div></div>
  <div class="stat"><div class="val o" id="sBaseline">-</div><div class="lbl">随机基线</div></div>
  <div class="stat"><div class="val" id="sStreak">-</div><div class="lbl">最大连错</div></div>
  <div class="stat"><div class="val" id="sTotal">-</div><div class="lbl">回测期数</div></div>
</div>
<div class="stats">
  <div class="stat"><div class="val" id="sPool">-</div><div class="lbl">穷举公式数</div></div>
  <div class="stat"><div class="val">200</div><div class="lbl">窗口</div></div>
  <div class="stat"><div class="val" id="sHits">-</div><div class="lbl">命中期数</div></div>
  <div class="stat"><div class="val" id="sAvg">-</div><div class="lbl">单码胆中均值</div></div>
</div>
<div class="table-wrap">
  <h3>近200期回测 <span style="font-size:.65rem;color:#999">(逐期真实预测 · 最新在前)</span> <span style="font-size:.65rem;color:#999;float:right">✓中 ✗错</span></h3>
  <div class="scroll">
    <table class="tbl">
      <thead><tr><th>期号</th><th>开奖</th><th>5胆</th><th>结果</th></tr></thead>
      <tbody id="btBody"></tbody>
    </table>
  </div>
</div>
<div class="info">
  <h3>5个胆码对应的公式（暴力穷举·最新200期单码命中率最高）</h3>
  <div id="algoList"></div>
  <div style="font-size:.68rem;color:#888;margin-top:8px;line-height:1.6">
    5胆命中随机基线 91.67%（5/10 数字覆盖3码开奖）。本套近200期 5胆命中 <b id="rateVal">-</b>。
  </div>
</div>
<div class="foot">
  仅供研究参考 · 不构成投注建议 · 近200期为暴力穷举最优结果，属历史拟合，样本外会回落<br>
  数据截止 <span id="dataInfo"></span> 期
</div>
</div>
<script>
const P = __DATA__;
// 5胆数字块（升序排列）
const grid = document.getElementById('danmaGrid');
P.danma.forEach(function(d) {
  const card = document.createElement('div');
  card.className = 'danma-card';
  card.innerHTML = '<div class="num">' + d + '</div>';
  grid.appendChild(card);
});
document.getElementById('sRate').textContent = P.s200.hit_rate + '%';
document.getElementById('sBaseline').textContent = P.baseline + '%';
document.getElementById('sStreak').textContent = P.max_streak + '期';
document.getElementById('sTotal').textContent = P.s200.total + '期';
document.getElementById('sPool').textContent = P.pool_size >= 10000 ? (P.pool_size/10000).toFixed(1) + '万' : P.pool_size;
document.getElementById('sHits').textContent = P.s200.hits + '期';
var sumRate = 0;
P.members.forEach(function(m) { sumRate += m.rate; });
document.getElementById('sAvg').textContent = (sumRate / P.members.length).toFixed(1) + '%';
document.getElementById('rateVal').textContent = P.s200.hit_rate + '%';
document.getElementById('algoList').innerHTML = P.members.map(function(m) {
  return '<div class="algo"><b>胆码 ' + m.digit + '</b> <span class="f">' + m.formula + '</span>' +
         '<span class="zh">' + m.explain + ' ｜ 单码胆中 ' + m.rate + '% (' + m.hits + '/200)</span></div>';
}).join('');
const tbody = document.getElementById('btBody');
P.rows.forEach(function(r) {
  const tr = document.createElement('tr');
  tr.className = r.hit ? 'tr-hit' : 'tr-miss';
  tr.innerHTML =
    '<td>' + r.issue + '</td><td><b>' + r.draw + '</b></td>' +
    '<td class="danma">' + r.danma.join(' ') + '</td>' +
    '<td class="' + (r.hit?'badge-y':'badge-n') + '">' + (r.hit?'✓':'✗') + '</td>';
  tbody.appendChild(tr);
});
document.getElementById('predIssue').textContent = P.next_issue;
document.getElementById('lastInfo').textContent = '上期 ' + P.last_issue + ' = ' + P.last_draw;
document.getElementById('updateTime').textContent = '更新 ' + P.updated;
document.getElementById('dataInfo').textContent = P.data_info.last;
</script>
</body>
</html>
"""


def main(out_path='index.html'):
    data = build_data()
    data_json = json.dumps(data, ensure_ascii=False)
    html = HTML_TEMPLATE.replace('__DATA__', data_json)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ 已生成 {out_path} ({len(html)} 字节)")
    print(f"预测期号: {data['next_issue']} | 上期 {data['last_issue']}={data['last_draw']}")
    print(f"  5胆: {data['danma']}")
    print(f"  近200: 5胆命中{data['s200']['hit_rate']}% | 连错{data['max_streak']}期 | 基线{data['baseline']}%")


if __name__ == '__main__':
    main()
