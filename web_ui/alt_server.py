from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Alt Server Test</title></head>
    <body>
        <h1>Alternative Server Test</h1>
        <p>If you see this, the server is working on port 5001!</p>
        <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        <p>Try the main server at: <a href="http://localhost:5000">http://localhost:5000</a></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)