# Changes Summary

## Updated for list.csv Dataset and FastAPI + Ollama Integration

### Key Changes:

1. **Data Loader (`data_loader.py`)**
   - Changed default path from `data/listings.csv` to `list.csv`
   - Added chunked reading for large files to handle memory issues
   - Works with standard Airbnb dataset structure

2. **MCP Server (`mcp_server.py`)**
   - Updated to use Ollama with `gemma:2b` model by default
   - Improved JSON parsing from Ollama responses
   - Better error handling and fallback to rule-based parser
   - Supports configurable model name

3. **Query Parser (`query_parser.py`)**
   - Added `llm_model` parameter support
   - Automatically uses Ollama if no API key provided
   - Falls back gracefully to rule-based parsing

4. **Agent (`agent.py`)**
   - Updated default data path to `list.csv`
   - Changed default `use_llm` to `True`
   - Added `llm_model` parameter (default: `gemma:2b`)

5. **FastAPI Application (`api.py`)**
   - New REST API with endpoints:
     - `GET /` - Health check
     - `GET /health` - Health check
     - `POST /search` - Search listings
     - `GET /search` - Search listings (GET method)
     - `GET /listing/{id}` - Get specific listing
   - CORS enabled for frontend integration
   - Automatic agent initialization
   - Environment variable configuration

6. **Requirements (`requirements.txt`)**
   - Added FastAPI
   - Added uvicorn[standard]
   - Added pydantic>=2.0.0

7. **New Files:**
   - `api.py` - FastAPI application
   - `run_api.py` - Startup script for API server
   - `test_api.py` - Test script for agent with CSV

8. **Updated Files:**
   - `main.py` - Uses new defaults and environment variables
   - `README.md` - Updated with FastAPI and Ollama instructions

### Environment Variables:

- `DATA_PATH` - Path to CSV file (default: `list.csv`)
- `USE_LLM` - Enable LLM parsing (default: `true`)
- `LLM_MODEL` - Ollama model name (default: `gemma:2b`)
- `HOST` - API host (default: `0.0.0.0`)
- `PORT` - API port (default: `8000`)

### Usage:

1. **Start API Server:**
   ```bash
   python run_api.py
   ```

2. **Test Agent:**
   ```bash
   python test_api.py
   ```

3. **Use CLI:**
   ```bash
   python main.py
   ```

### Notes:

- Make sure Ollama is installed and running
- Pull the gemma:2b model: `ollama pull llama3.2:3b`
- The system will automatically fallback to rule-based parsing if Ollama is unavailable
- Large CSV files are handled with chunked reading

