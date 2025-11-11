"""
Startup script for FastAPI server.
"""

import uvicorn
import os

if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    print(f"Starting Airbnb Smart Search Agent API on {host}:{port}")
    print("Software 3.0: Using llama3.2:3b model (Ollama)")
    print("Make sure Ollama is running with llama3.2:3b model installed")
    print("Install: ollama pull llama3.2:3b")
    print(f"\nAPI will be available at: http://{host}:{port}")
    print(f"API docs at: http://{host}:{port}/docs")
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload
    )

