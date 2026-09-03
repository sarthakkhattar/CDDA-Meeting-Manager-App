"""
CDDA Meeting Manager - Fabric Lakehouse Backend.
Flask app that manages meeting agendas with data in Fabric.
"""

from flask import Flask, jsonify
import os

server = Flask(__name__, static_folder='static', static_url_path='/static')
app = server

@app.route('/')
def serve_root():
    """Serve the main HTML interface."""
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(app_dir, 'static', 'index.html')
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        return "index.html not found", 404
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/health')
def health():
    """Health check."""
    return jsonify({'status': 'ok', 'message': 'CDDA Meeting Manager running'})

if __name__ == "__main__":
    server.run(debug=True, port=8050)
