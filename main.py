import uvicorn
from trading_bot_backend.app.main import app

if __name__ == "__main__":
    # Start the FastAPI server on port 8000
    # This will also trigger the startup_event which starts workers and demo engine
    uvicorn.run(app, host="0.0.0.0", port=8000)
