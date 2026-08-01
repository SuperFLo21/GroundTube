import os
from flask import Flask, render_template_string, request

app = Flask(__name__)

HTML_CODE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GroundTube</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f0f0f; color: #fff; }
        header { display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; background-color: #212121; border-bottom: 1px solid #383838; }
        .logo { font-size: 24px; font-weight: bold; color: #ff0000; letter-spacing: -1px; }
        .logo span { color: #fff; }
        .search-bar { display: flex; width: 40%; }
        .search-bar input { width: 100%; padding: 10px; background: #121212; border: 1px solid #303030; color: white; border-radius: 20px 0 0 20px; outline: none; }
        .search-bar button { padding: 10px 20px; background: #303030; border: 1px solid #303030; color: white; border-radius: 0 20px 20px 0; cursor: pointer; }
        .container { padding: 30px; display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
        .card { background: #181818; border-radius: 10px; overflow: hidden; border: 1px solid #272727; }
        .thumbnail { width: 100%; height: 160px; background: #282828; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 40px; }
        .info { padding: 15px; }
        .title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
        .author { font-size: 14px; color: #aaaaaa; }
        .status-badge { background: #22c55e; color: black; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <header>
        <div class="logo">Ground<span>Tube</span></div>
        <form class="search-bar" action="/" method="GET">
            <input type="text" name="q" placeholder="Caută pe GroundTube..." value="{{ query }}">
            <button type="submit">🔍</button>
        </form>
        <div><span class="status-badge">ONLINE</span></div>
    </header>

    <div class="container">
        {% for i in range(1, 7) %}
        <div class="card">
            <div class="thumbnail">▶</div>
            <div class="info">
                <div class="title">GroundTube Video #{{ i }}</div>
                <div class="author">Canal Official • 10K vizionări</div>
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    query = request.args.get('q', '')
    return render_template_string(HTML_CODE, query=query)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
