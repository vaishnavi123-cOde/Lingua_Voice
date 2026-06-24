#!/usr/bin/env python3
import os

from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting LinguaVoice on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)