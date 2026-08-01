import os
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Interfață simplă de test pentru GroundTube
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GroundTube</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #121212; color: #fff; text-align: center; padding: 50px; }
        h1 { color: #ff0000; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 8px; display: inline-block; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>🚀 GroundTube Server</h1>
    <div class="card">
        <p>Backend-ul tău Python / Flask rulează cu succes pe <b>Render</b>!</p>
        <p>Status: <span style="color: #00ff00;">ONLINE 24/7</span></p>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def status():
    return jsonify({"status": "success", "message": "GroundTube API is active"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
