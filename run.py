"""Entry point: start FastAPI backend (+ Telegram bot as background task)."""

import os
import uvicorn

if __name__ == "__main__":
    is_dev = not os.getenv("RENDER") and os.getenv("ENV", "dev") == "dev"
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=is_dev,
    )
