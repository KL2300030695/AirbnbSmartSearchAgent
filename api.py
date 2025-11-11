"""
FastAPI application for Airbnb Smart Search Agent.
Provides REST API endpoints for searching listings.
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import asyncio
from agent import AirbnbSearchAgent

# Initialize FastAPI app
app = FastAPI(
    title="Airbnb Smart Search Agent API",
    description="Intelligent Airbnb search based on workspace quality, Wi-Fi, and proximity",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (UI)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize agent (lazy loading)
agent: Optional[AirbnbSearchAgent] = None
initializing: bool = False
initialization_error: Optional[str] = None
# Cached locations index (built from dataset on init)
locations_index: List[str] = []


class SearchRequest(BaseModel):
    """Request model for search endpoint."""
    query: str
    top_k: Optional[int] = 10
    use_llm: Optional[bool] = True
    quick_mode: Optional[bool] = False


class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    success: bool
    query: str
    results_count: int
    results: List[Dict[str, Any]]
    criteria: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None


class ShortlistItem(BaseModel):
    id: Any
    name: str
    workspace_score: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    property_type: Optional[str] = None
    room_type: Optional[str] = None
    has_wifi: Optional[bool] = None
    has_workspace: Optional[bool] = None
    metro_distance_km: Optional[float] = None
    nearest_metro: Optional[str] = None
    grocery_distance_km: Optional[float] = None
    nearest_grocery: Optional[str] = None
    price: Optional[float] = None
    picture_url: Optional[str] = None


class ShortlistResponse(BaseModel):
    success: bool
    query: str
    results_count: int
    results: List[ShortlistItem]


class RecommendRequest(BaseModel):
    area: str
    workspace: bool = True
    wifi: bool = True
    max_grocery_km: float = 1.0
    top_k: int = 10
    quick_mode: bool = False


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str
    data_loaded: bool
    listings_count: Optional[int] = None


class ChatMessage(BaseModel):
    role: str  # 'system' | 'user' | 'assistant'
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None  # defaults to env LLM_MODEL or 'llama3.2:3b'


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str


def get_agent() -> AirbnbSearchAgent:
    """Get or initialize the agent."""
    global agent, initializing, initialization_error, locations_index
    if agent is None and not initializing:
        initializing = True
        try:
            data_path = os.getenv("DATA_PATH", "list.csv")
            use_llm = os.getenv("USE_LLM", "true").lower() == "true"
            # Use more capable model for Software 3.0 - defaults to llama3.2:3b (better than gemma:2b)
            llm_model = os.getenv("LLM_MODEL", "llama3.2:3b")
            
            agent = AirbnbSearchAgent(
                data_path=data_path,
                use_llm=use_llm,
                llm_model=llm_model
            )
            agent.initialize()
            # Build locations index after data is loaded
            try:
                locations_index = build_locations_index()
                print(f"Locations index built with {len(locations_index)} entries")
            except Exception as e:
                print(f"Failed to build locations index: {e}")
            initializing = False
        except Exception as e:
            initializing = False
            initialization_error = str(e)
            raise
    elif initializing:
        raise HTTPException(status_code=503, detail="Agent is still initializing. Please wait a moment and try again.")
    elif initialization_error:
        raise HTTPException(status_code=500, detail=f"Agent initialization failed: {initialization_error}")
    return agent


@app.get("/image")
def image_proxy(url: str = Query(..., description="External image URL to proxy")):
    """Proxy external listing images to avoid hotlink restrictions in the browser.

    Notes:
    - Only http/https URLs are allowed
    - Small timeout and user-agent set
    - Returns 502 for upstream fetch errors
    - Handles Airbnb CDN URLs with proper headers
    """
    try:
        from urllib.parse import urlparse
        import requests

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise HTTPException(status_code=400, detail="Invalid URL scheme")

        # Whitelist known Airbnb CDN hosts
        allowed_hosts = {
            "a0.muscache.com",
            "a1.muscache.com",
            "a2.muscache.com",
            "a0.muscache.net",
            "a1.muscache.net",
            "a2.muscache.net",
        }
        host = (parsed.hostname or "").lower()
        if host not in allowed_hosts:
            # Soft-deny: return 204 so frontend can use fallback image
            return Response(status_code=204)

        # Headers that work better with Airbnb CDN
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.airbnb.com/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

        timeout_s = 25

        def fetch_once() -> requests.Response:
            return requests.get(url, headers=headers, timeout=timeout_s, allow_redirects=True)

        # Try once, retry once on transient errors
        resp = fetch_once()
        if resp.status_code >= 500:
            try:
                resp = fetch_once()
            except Exception:
                pass

        if resp.status_code != 200 or not resp.content:
            # Return 204 to let frontend fallback image kick in silently
            return Response(status_code=204)

        # Determine content type: header first, then extension
        content_type = (resp.headers.get("Content-Type") or "").lower()
        if "image" not in content_type:
            ul = url.lower()
            if ul.endswith((".png")):
                content_type = "image/png"
            elif ul.endswith((".webp")):
                content_type = "image/webp"
            elif ul.endswith((".avif")):
                content_type = "image/avif"
            elif ul.endswith((".gif")):
                content_type = "image/gif"
            else:
                content_type = "image/jpeg"

        return Response(content=resp.content, media_type=content_type)
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        # Soft-fail with 204
        return Response(status_code=204)
    except Exception:
        # Any other failure: soft-fail with 204
        return Response(status_code=204)


@app.get("/")
async def root():
    """Root endpoint - serves UI if available, otherwise health check."""
    static_index = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    else:
        # Fallback to health check JSON
        try:
            agent = get_agent()
            return HealthResponse(
                status="healthy",
                message="Airbnb Smart Search Agent API is running",
                data_loaded=True,
                listings_count=len(agent.listings_df) if agent.listings_df is not None else None
            )
        except Exception as e:
            return HealthResponse(
                status="error",
                message=f"Error: {str(e)}",
                data_loaded=False
            )


@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup in background."""
    async def init_agent():
        try:
            print("Starting background agent initialization...")
            get_agent()
            print("Agent initialized successfully!")
        except Exception as e:
            print(f"Background initialization error: {e}")
    
    # Start initialization in background
    asyncio.create_task(init_agent())


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    try:
        agent = get_agent()
        return HealthResponse(
            status="healthy",
            message="Airbnb Smart Search Agent API is running",
            data_loaded=True,
            listings_count=len(agent.listings_df) if agent.listings_df is not None else None
        )
    except HTTPException:
        raise
    except Exception as e:
        return HealthResponse(
            status="initializing" if initializing else "error",
            message=f"Agent initialization: {str(e)}" if not initializing else "Agent is initializing...",
            data_loaded=False
        )


@app.post("/search", response_model=SearchResponse)
async def search_listings(request: SearchRequest):
    """
    Search for Airbnb listings based on natural language query.
    
    Example query:
    "Find apartments in London with a quiet workspace, stable Wi-Fi, and grocery stores within 1 km"
    """
    try:
        agent = get_agent()
        
        # Perform search (use quick_mode for faster results)
        results_df = agent.search(
            request.query, 
            top_k=request.top_k,
            quick_mode=request.quick_mode
        )
        
        if len(results_df) == 0:
            return SearchResponse(
                success=True,
                query=request.query,
                results_count=0,
                results=[]
            )
        
        # Format results
        formatted_results = agent.format_results(results_df)
        
        # Get parsed query info for debugging
        parsed = agent.query_parser.parse_query(request.query)
        
        return SearchResponse(
            success=True,
            query=request.query,
            results_count=len(formatted_results),
            results=formatted_results,
            criteria=parsed.get('criteria'),
            location=parsed.get('location'),
            constraints=parsed.get('constraints')
        )
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Search error: {error_details}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.get("/search", response_model=SearchResponse)
async def search_listings_get(
    query: str = Query(..., description="Natural language search query"),
    top_k: int = Query(10, description="Number of results to return"),
    quick_mode: bool = Query(True, description="Use quick mode for faster results (recommended)")
):
    """
    Search for Airbnb listings (GET endpoint).
    
    Example: /search?query=Find apartments with Wi-Fi&top_k=5
    """
    request = SearchRequest(query=query, top_k=top_k, quick_mode=quick_mode)
    return await search_listings(request)


def _none_if_nan(value):
    try:
        import math
        if isinstance(value, float) and math.isnan(value):
            return None
    except Exception:
        pass
    return value


def _map_to_shortlist(formatted_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map full formatted results to compact shortlist items."""
    shortlist = []
    for r in formatted_results:
        loc = r.get('location') or {}
        shortlist.append({
            'id': r.get('id'),
            'name': r.get('name', 'Unnamed Listing'),
            'workspace_score': float(r.get('workspace_score', 0) or 0),
            'latitude': _none_if_nan(loc.get('latitude')),
            'longitude': _none_if_nan(loc.get('longitude')),
            'property_type': r.get('property_type'),
            'room_type': r.get('room_type'),
            'has_wifi': r.get('has_wifi'),
            'has_workspace': r.get('has_workspace'),
            'metro_distance_km': _none_if_nan(r.get('metro_distance_km')),
            'nearest_metro': r.get('nearest_metro'),
            'grocery_distance_km': _none_if_nan(r.get('grocery_distance_km')),
            'nearest_grocery': r.get('nearest_grocery'),
            'price': _none_if_nan(r.get('price')),
            'picture_url': r.get('picture_url'),
        })
    return shortlist


@app.post("/shortlist", response_model=ShortlistResponse)
async def shortlist_post(request: SearchRequest):
    """Return a concise ranked shortlist with workspace score and travel distances.

    Note: quick_mode defaults to False here to compute actual distances unless explicitly set.
    """
    try:
        agent = get_agent()
        quick = False if request.quick_mode is None else request.quick_mode
        results_df = agent.search(
            request.query,
            top_k=request.top_k,
            quick_mode=quick
        )
        formatted_results = agent.format_results(results_df)
        compact = _map_to_shortlist(formatted_results)
        return ShortlistResponse(
            success=True,
            query=request.query,
            results_count=len(compact),
            results=compact
        )
    except Exception as e:
        import traceback
        print("Shortlist error:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Shortlist error: {str(e)}")


@app.get("/shortlist", response_model=ShortlistResponse)
async def shortlist_get(
    query: str = Query(..., description="Natural language search query"),
    top_k: int = Query(10, description="Number of results to return"),
    quick_mode: bool = Query(False, description="Use quick mode (skips distance calc)"),
):
    request = SearchRequest(query=query, top_k=top_k, quick_mode=quick_mode)
    return await shortlist_post(request)


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    """Simple chat endpoint backed by local Ollama.

    Uses model from request or environment variable LLM_MODEL (default 'llama3.2:3b').
    Requires Ollama to be running locally (default host/port).
    """
    try:
        import requests
        model = (body.model or os.getenv("LLM_MODEL") or "llama3.2:3b").strip()
        # Safety: restrict roles
        msgs = []
        for m in body.messages:
            role = m.role if m.role in ("system", "user", "assistant") else "user"
            msgs.append({"role": role, "content": m.content})

        # Ensure a concise assistant behavior by prepending a light system prompt if none provided
        has_system = any(m["role"] == "system" for m in msgs)
        if not has_system:
            msgs.insert(0, {
                "role": "system",
                "content": (
                    "You are a concise travel search assistant for workspace-friendly stays. "
                    "Greet briefly. When users ask about stays, acknowledge and be succinct."
                )
            })

        payload = {
            "model": model,
            "messages": msgs,
            # Keep defaults sensible; adjust as needed
            "stream": False,
        }
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=60
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Ollama error: HTTP {resp.status_code}")
        data = resp.json()
        message = (data.get("message") or {}).get("content") or ""
        if not message:
            # Some variants may return accumulated responses, try 'content' directly
            message = data.get("content") or ""
        return ChatResponse(content=message.strip())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


def _build_query_from_params(area: str, workspace: bool, wifi: bool, max_grocery_km: float) -> str:
    needs = []
    if workspace:
        needs.append("quiet workspace")
    if wifi:
        needs.append("stable Wi-Fi")
    # Always include grocery constraint
    needs.append(f"grocery stores within {max_grocery_km} km")
    needs_str = ", ".join(needs)
    return f"Find apartments near {area} with {needs_str}"


@app.get("/recommend", response_model=ShortlistResponse)
async def recommend_get(
    area: str = Query(..., description="Area or neighborhood, e.g., Westminster"),
    workspace: bool = Query(True, description="Require quiet workspace"),
    wifi: bool = Query(True, description="Require stable Wi‑Fi"),
    max_grocery_km: float = Query(1.0, ge=0.1, le=10.0, description="Max grocery distance in km"),
    top_k: int = Query(10, ge=1, le=50),
    quick_mode: bool = Query(False)
):
    query = _build_query_from_params(area, workspace, wifi, max_grocery_km)
    req = SearchRequest(query=query, top_k=top_k, quick_mode=quick_mode)
    return await shortlist_post(req)


@app.post("/recommend", response_model=ShortlistResponse)
async def recommend_post(body: RecommendRequest):
    query = _build_query_from_params(body.area, body.workspace, body.wifi, body.max_grocery_km)
    req = SearchRequest(query=query, top_k=body.top_k, quick_mode=body.quick_mode)
    return await shortlist_post(req)


def build_locations_index(max_count: int = 1000) -> List[str]:
    """Build a list of unique location strings from the dataset.

    Tries common columns used in Airbnb datasets and returns a deduplicated,
    frequency-sorted list of location names.
    """
    if agent is None or agent.data_loader.df is None:
        return []
    import pandas as pd
    df = agent.data_loader.df
    candidate_cols = [
        "city", "neighbourhood_cleansed", "neighbourhood", "market", "state"
    ]
    parts: List[pd.Series] = []
    for col in candidate_cols:
        if col in df.columns:
            s = df[col].astype(str).str.strip()
            s = s[~s.isna() & (s.str.lower() != "nan") & (s.str.len() > 0)]
            parts.append(s)
    if not parts:
        # As a last resort, attempt to infer from name/title if exists (very fuzzy)
        if "name" in df.columns:
            s = df["name"].astype(str).str.strip()
            s = s[~s.isna() & (s.str.lower() != "nan") & (s.str.len() > 0)]
            parts.append(s)
        else:
            return []
    all_vals = pd.concat(parts, ignore_index=True)
    # Normalize whitespace
    all_vals = all_vals.str.replace(r"\s+", " ", regex=True).str.strip()
    # Basic cleaning: remove clearly non-location artifacts
    import re
    def is_plausible_location(s: str) -> bool:
        if not s:
            return False
        sl = s.lower()
        # exclude common noise tokens
        noise_tokens = [
            'highlight', 'highlights', 'about this space', 'room type', 'entire place',
            'private room', 'shared room', 'united kingdom', 'uk'
        ]
        if any(t in sl for t in noise_tokens):
            return False
        # exclude strings with many digits or special chars
        if sum(c.isdigit() for c in s) > 0:
            return False
        if len(s) > 40:
            return False
        # allow letters, spaces, hyphens and apostrophes
        if not re.match(r"^[A-Za-z][A-Za-z \-']*[A-Za-z]$", s):
            return False
        # limit words to at most 4
        if len(s.split()) > 4:
            return False
        return True
    all_vals = all_vals[all_vals.apply(is_plausible_location)]
    vc = all_vals.value_counts()
    # Keep top N unique values
    top = vc.head(max_count).index.tolist()
    # Deduplicate while preserving order/case formatting to Title
    seen = set()
    result: List[str] = []
    for v in top:
        title = v.title()
        if title not in seen:
            seen.add(title)
            result.append(title)
    return result


@app.get("/locations")
async def locations(q: Optional[str] = Query(None, description="Query string for filtering locations"), limit: int = Query(10, ge=1, le=50)):
    """Return dataset-driven location suggestions.

    If q is provided, performs a case-insensitive substring match.
    Returns up to `limit` suggestions.
    """
    global locations_index
    # If index empty but agent ready, try rebuilding once
    if not locations_index and agent is not None and agent.data_loader.df is not None:
        try:
            locations = build_locations_index()
            locations_index = locations
        except Exception:
            pass
    suggestions = locations_index or []
    if q:
        ql = q.lower()
        suggestions = [s for s in suggestions if ql in s.lower()]
    return {"locations": suggestions[:limit]}


@app.get("/favicon.ico")
async def favicon_ico():
    """Serve favicon.ico file (fallback for browsers that don't support SVG)."""
    favicon_ico_path = os.path.join(os.path.dirname(__file__), "static", "favicon.ico")
    favicon_svg_path = os.path.join(os.path.dirname(__file__), "static", "favicon.svg")
    
    # Prefer .ico, fallback to .svg
    if os.path.exists(favicon_ico_path):
        return FileResponse(favicon_ico_path, media_type="image/x-icon")
    elif os.path.exists(favicon_svg_path):
        return FileResponse(favicon_svg_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/favicon.svg")
async def favicon_svg():
    """Serve favicon.svg file directly."""
    favicon_path = os.path.join(os.path.dirname(__file__), "static", "favicon.svg")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/listing/{listing_id}")
async def get_listing(listing_id: int):
    """Get details for a specific listing by ID."""
    try:
        agent = get_agent()
        listing = agent.data_loader.get_listing_by_id(listing_id)
        
        if listing is None:
            raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")
        
        return {
            "success": True,
            "listing": listing
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

