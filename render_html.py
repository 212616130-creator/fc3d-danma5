import pandas as pd
import os

# 读取数据文件（fc3d-danma5项目默认生成 history.csv）
csv_path = "history.csv"
if not os.path.exists(csv_path):
    print("警告：找不到history.csv文件")
else:
    df = pd.read_csv(csv_path)
    latest = df.iloc[-1]
    # 网页代码，深色风格，和你之前kill6界面一致
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>福彩3D选5胆码</title>
    <style>
        * {{margin:0;padding:0;box-sizing:border-box;}}
        body {{background:#0b1020;color:#fff;font-family:system-ui;padding:40px 20px;}}
        .container {{max-width:1200px;margin:0 auto;}}
        .title {{font-size:34px;margin-bottom:30px;}}
        .card {{background:#161c34;border-radius:14px;padding:28px;margin:16px 0;}}
        .danma-text {{font-size:44px;color:#4cd964;font-weight:bold;margin-top:12px;}}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">福彩3D 选5胆码参考</h1>
        <div class="card">
            <h3>最新期号：{latest['issue']}</h3>
            <div class="danma-text">胆码：{latest['danma']}</div>
        </div>
    </div>
</body>
</html>
"""
    # 生成index.html网页
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ index.html 生成成功")
