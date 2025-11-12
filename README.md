# Airbnb Smart Search Agent

An intelligent agent that helps travelers and digital nomads find Airbnb listings based on specific needs like quiet workspace, Wi-Fi quality, proximity to metro/bus, and grocery access.

## Problem Statement

Searching Airbnb manually for specific needs (quiet workspace, Wi-Fi quality, near metro/bus, grocery access) is tedious. Travelers and digital nomads often spend hours filtering Airbnb listings to find homes with specific needs. Airbnb's built-in filters don't support these niche criteria. This intelligent agent automates this by ranking listings using custom user preferences.

## Features

- **Natural Language Query Processing**: Accept queries in plain English
- **Workspace Quality Scoring**: Calculates composite scores based on user criteria
- **Proximity Calculations**: Distance to metro stations and grocery stores using geopy
- **Wi-Fi Quality Assessment**: Evaluates internet connectivity features
- **Ranked Results**: Returns listings sorted by workspace score
- **LLM Integration**: Optional MCP-based LLM parsing for better query understanding

## Pictures
<img width="1920" height="1200" alt="Screenshot (675)" src="https://github.com/user-attachments/assets/a7bfa2cf-034d-4653-94de-c102cf4919d4" /><img width="1920" height="1200" alt="Screenshot (667)" src="https://github.com/user-attachments/assets/8ac993c0-9bc1-4d7a-80ba-cd153c1252fe" />

<img width="569" height="738" alt="Screenshot 2025-11-07 222432" src="https://github.com/user-attachments/assets/3ac47d40-fbb8-49de-b76c-f21768743e58" />

<img width="1894" height="941" alt="Screenshot 2025-11-08 155500" src="https://github.com/user-attachments/assets/30ba5129-c256-4911-aa12-ce768e2089ca" />

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up Ollama (for LLM query parsing):**
```bash
# Install Ollama from https://ollama.ai
# Pull the llama3.2:3b model
ollama pull llama3.2:3b

# Make sure Ollama is running
ollama serve
```

3. **Prepare your dataset:**
   - Place your Airbnb `list.csv` file in the project root
   - The file should include columns: `id`, `latitude`, `longitude`, `amenities`, `property_type`, `room_type`, `price`
   - Default path: `list.csv` (can be changed via `DATA_PATH` environment variable)

4. **Optional - Environment variables:**
```bash
# Create .env file (optional)
DATA_PATH=list.csv          # Path to your CSV file
USE_LLM=true                # Enable LLM parsing (default: true)
LLM_MODEL=llama3.2:3b       # Ollama model to use
HOST=0.0.0.0                # API host
PORT=8000                   # API port
```

## Usage

### FastAPI Server with Web UI (Recommended)

Start the API server:
```bash
python run_api.py
# or
uvicorn api:app --host 0.0.0.0 --port 8000
```

The server will be available at:
- **Web UI**: http://localhost:8000 (Beautiful interactive interface!)
- **API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

**Example API calls:**

```bash
# POST request
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "Find apartments with quiet workspace and Wi-Fi", "top_k": 10}'

# GET request
curl "http://localhost:8000/search?query=Find%20apartments%20with%20Wi-Fi&top_k=5"
```

### Interactive CLI

```bash
python main.py
```

Example queries:
```
Find apartments in London with a quiet workspace, stable Wi-Fi, and grocery stores within 1 km
I need a place with good Wi-Fi and near metro station in London
Looking for quiet workspace in Islington
```

### Test Script

```bash
python test_agent.py
```

### Programmatic Usage

```python
from agent import AirbnbSearchAgent

# Initialize agent (uses Ollama llama3.2:3b by default)
agent = AirbnbSearchAgent(data_path="list.csv", use_llm=True, llm_model="llama3.2:3b")
agent.initialize()

# Search
results_df = agent.search(
    "Find apartments with quiet workspace and Wi-Fi",
    top_k=10
)

# Format results
formatted = agent.format_results(results_df)
for result in formatted:
    print(f"{result['name']}: Score {result['workspace_score']:.3f}")
```

## How It Works

1. **Query Parsing**: Extracts criteria, location, and constraints from natural language
   - Rule-based parser (default)
   - LLM-based parser (optional, via MCP)

2. **Data Loading**: Loads and preprocesses Airbnb listings
   - Parses amenities
   - Extracts workspace-related features
   - Validates coordinates

3. **Proximity Calculation**: Computes distances to points of interest
   - Metro stations
   - Grocery stores
   - Configurable distance thresholds

4. **Scoring**: Calculates composite workspace score based on:
   - Quiet workspace quality (property type, room type, amenities)
   - Wi-Fi availability and quality
   - Metro proximity score
   - Grocery proximity score

5. **Ranking**: Sorts listings by workspace score and returns top results

## Workspace Scoring Details

The agent converts your natural‑language needs into weighted criteria and computes a `workspace_score` between 0 and 1 for each listing, then returns the top results. Distances to metro and grocery are also computed and included.

- **Inputs (from your query)**
  - `quiet_workspace`, `wifi_quality`, `metro_proximity`, `grocery_proximity` (weights 0–1)

- **Final score**
  - Weighted average of the component scores, normalized and clipped to [0, 1].
  - Components: Quiet workspace, Wi‑Fi, Metro proximity, Grocery proximity.

- **Quiet workspace score (0–1)**
  - Base 0.5
  - Room type: Entire home/apt +0.3; Private room +0.1
  - Property type: House +0.15; Apartment/Condo +0.1
  - Amenities: contains “quiet” +0.1; contains “soundproof” +0.15
  - Capped at 1.0

- **Wi‑Fi score (0–1)**
  - Has Wi‑Fi: base 0.7
  - Mentions “high speed”/“fast”: +0.2; “ethernet”/“wired”: +0.1
  - Capped at 1.0

- **Metro/Grocery proximity scores (0–1)**
  - Find nearest metro and grocery, compute distance in km.
  - Score = max(0, 1 − d / max_dist)
    - Metro: `max_dist = 2.0 km`
    - Grocery: `max_dist = 1.0 km`
  - If farther than the max distance → score 0
  - Response includes: `nearest_metro`, `metro_distance_km`, `nearest_grocery`, `grocery_distance_km`

- **Quick mode behavior**
  - To maximize speed, distance calculations are skipped
  - Proximity scores default to 0.5 (neutral) so they neither help nor hurt

- **No explicit criteria?**
  - Fallback heuristic: base 0.3, +0.3 if Wi‑Fi, +0.2 if workspace, +0.2 if entire home/apt (capped at 1.0)

### Shortlist API

- `GET /shortlist?query=...&top_k=10&quick_mode=false`
- Returns a concise, ranked list with `workspace_score`, metro/grocery distances and names, plus key listing attributes.

## Project Structure

- `main.py` - Main entry point and CLI interface
- `agent.py` - Core search agent orchestrating all components
- `data_loader.py` - Airbnb dataset loading and preprocessing
- `query_parser.py` - Query interpretation (rule-based + LLM)
- `scorer.py` - Workspace scoring and ranking logic
- `distance_calculator.py` - Proximity calculations using geopy
- `mcp_server.py` - MCP server for LLM integration
- `test_agent.py` - Test script with sample queries

## Consolidated Guide (Quick Start + UI + API + Troubleshooting)

### Quick Start (Windows)

- Install deps
  - `pip install -r requirements.txt`
- Sample dataset (fast):
  - `set DATA_PATH=list_sample.csv`
  - `set USE_LLM=false`
- Start server
  - `python run_api.py`
- Open
  - Web UI: http://localhost:8000
  - Docs: http://localhost:8000/docs
  - Health: http://localhost:8000/health

### Web UI usage

- Where: dataset‑driven suggestions (type to filter)
- Filters: Quiet workspace, Reliable Wi‑Fi, Near metro/tube, Grocery within 1 km
- Toggles:
  - Shortlist: returns compact ranked results with workspace score + distances
  - Quick mode: speed up by skipping distance calculations
- Results cards show:
  - Score NN%, Wi‑Fi/Workspace badges
  - Nearest metro/grocery name + distance

### API cheatsheet

- Search (GET)
  - `/search?query=...&top_k=10&quick_mode=true`
- Shortlist (GET)
  - `/shortlist?query=...&top_k=10&quick_mode=false`
  - Returns `workspace_score`, `nearest_metro/grocery` and distances, plus key attributes
- Locations (GET)
  - `/locations?q=cam&limit=8` → dataset‑driven suggestions

### Troubleshooting

- Port in use (Windows)
  - `netstat -ano | findstr :8000`
  - `taskkill /PID <PID> /F`
- Restart server
  - Stop the Python process and run `python run_api.py` again
- Slow initial load
  - Use `list_sample.csv` and enable quick mode

### Performance tips

- Use sample dataset for development
- Enable quick mode for faster responses (skips distance calculation)
- Narrow searches by location keywords (e.g., neighborhood names)

## Example Scenario

**Input:**
```
Find apartments in London with a quiet workspace, stable Wi-Fi, and grocery stores within 1 km.
```

**Output:**
- Ranked listings with workspace scores
- Distance to nearest metro and grocery
- Wi-Fi availability status
- Property details and coordinates

## Tech Stack

- **Python 3.8+**
- **FastAPI** - REST API framework
- **pandas** - Data manipulation
- **geopy** - Geospatial distance calculations
- **Ollama** - Local LLM (llama3.2:3b model)
- **MCP** - Model Context Protocol for LLM integration
- **OpenAI API** (optional) - Alternative LLM service

## Quick Mode (Faster Searches)

For faster search results, use `quick_mode=true`:

```bash
# API call with quick mode
curl "http://localhost:8000/search?query=Find%20apartments%20with%20Wi-Fi&quick_mode=true"
```

Quick mode:
- ✅ Uses first 2,000 listings (faster processing)
- ✅ Skips expensive distance calculations when not critical
- ✅ Returns results in 2-5 seconds instead of 30+ seconds
- ⚠️ May miss some results, but much faster

**In the Web UI**, quick mode is enabled by default for faster responses.

## Create Sample Dataset (For Testing)

For even faster testing, create a smaller sample dataset:

```bash
python create_sample_dataset.py 5000
```

This creates `list_sample.csv` with 5,000 rows. Then:

```bash
set DATA_PATH=list_sample.csv
python run_api.py
```

Searches will be much faster (1-2 seconds) with the sample dataset.

## Customization

### Adding Metro Stations / Grocery Stores

Edit `distance_calculator.py` to add more points of interest:

```python
LONDON_METRO_STATIONS = [
    (lat, lon, "Station Name"),
    # Add more stations...
]
```

### Adjusting Scoring Weights

Modify `scorer.py` to change how workspace scores are calculated.

### Changing LLM Model

The default model is `llama3.2:3b`. To use a different Ollama model:

```bash
# Pull a different model (example)
ollama pull llama3.2:3b

# Set environment variable
export LLM_MODEL=llama3.2:3b
# On Windows (PowerShell)
$env:LLM_MODEL = "llama3.2:3b"
# On Windows (cmd)
set LLM_MODEL=llama3.2:3b
```

Or in code:
```python
agent = AirbnbSearchAgent(llm_model="llama3.2:3b")
```

### Additional API Endpoints

- `GET /recommend?area=Islington&workspace=true&wifi=true&max_grocery_km=1.0&top_k=10&quick_mode=false`
- `POST /recommend` with JSON body `{ area, workspace, wifi, max_grocery_km, top_k, quick_mode }`
- `POST /chat` with `{ messages: [{role, content}], model? }` (requires Ollama running locally)
- `GET /image?url=<external_image_url>` proxies images from Airbnb CDNs for the UI
- `GET /listing/{id}` returns raw listing details by ID

  #### API examples

  ```bash
  # Recommend (GET)
  curl "http://localhost:8000/recommend?area=Islington&workspace=true&wifi=true&max_grocery_km=1.0&top_k=5&quick_mode=false"

  # Recommend (POST)
  curl -X POST "http://localhost:8000/recommend" \
    -H "Content-Type: application/json" \
    -d '{
      "area": "Islington",
      "workspace": true,
      "wifi": true,
      "max_grocery_km": 1.0,
      "top_k": 5,
      "quick_mode": false
    }'

  # Chat (Ollama-backed)
  curl -X POST "http://localhost:8000/chat" \
    -H "Content-Type: application/json" \
    -d '{
      "messages": [
        {"role": "user", "content": "Suggest areas in London good for quiet work."}
      ]
    }'

  # Image proxy
  curl "http://localhost:8000/image?url=https://a0.muscache.com/im/pictures/some-image.jpg"

  # Listing by ID
  curl "http://localhost:8000/listing/12345"

  # Locations suggestions
  curl "http://localhost:8000/locations?q=cam&limit=8"
  ```

## Author

Subhash Vadaparthi

## License

MIT License
