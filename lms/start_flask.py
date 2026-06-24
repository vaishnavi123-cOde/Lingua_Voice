import os, sys
os.environ["FLASK_SECRET_KEY"] = "dev-secret-key-123"
os.environ["PORT"] = "5000"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
