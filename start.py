#!/usr/bin/env python3
"""
Startup script for Cloud Run deployment
Reads PORT from environment and starts uvicorn server
"""
import os
import uvicorn
from server_multiship import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
