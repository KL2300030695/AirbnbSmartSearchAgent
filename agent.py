"""
Main Airbnb Smart Search Agent.
Orchestrates data loading, query parsing, scoring, and ranking.
"""

import pandas as pd
from typing import Dict, List, Optional
from data_loader import AirbnbDataLoader
from query_parser import QueryParser
from scorer import WorkspaceScorer
from distance_calculator import DistanceCalculator, LONDON_METRO_STATIONS, LONDON_GROCERY_STORES


class AirbnbSearchAgent:
    """Main agent for intelligent Airbnb search."""
    
    def __init__(
        self,
        data_path: str = "list.csv",
        use_llm: bool = True,
        llm_api_key: Optional[str] = None,
        llm_model: str = "llama3.2:3b"
    ):
        """
        Initialize the search agent.
        
        Args:
            data_path: Path to Airbnb listings CSV
            use_llm: Whether to use LLM for query parsing
            llm_api_key: Optional API key for LLM service
            llm_model: Model name for Ollama (default: llama3.2:3b)
        """
        self.data_loader = AirbnbDataLoader(data_path)
        self.query_parser = QueryParser(use_llm=use_llm, llm_api_key=llm_api_key, llm_model=llm_model)
        self.scorer = WorkspaceScorer()
        self.distance_calc = DistanceCalculator()
        
        self.listings_df: Optional[pd.DataFrame] = None
        self.metro_stations = LONDON_METRO_STATIONS
        self.grocery_stores = LONDON_GROCERY_STORES
    
    def initialize(self):
        """Load and preprocess data."""
        print("Initializing agent...")
        self.listings_df = self.data_loader.load_data()
        self.listings_df = self.data_loader.preprocess()
        print("Agent initialized successfully!")
    
    def search(self, query: str, top_k: int = 10, quick_mode: bool = False) -> pd.DataFrame:
        """
        Search for listings based on natural language query.
        
        Args:
            query: Natural language query string
            top_k: Number of top results to return
            quick_mode: If True, skip expensive distance calculations for faster results
        
        Returns:
            DataFrame with ranked listings
        """
        if self.listings_df is None:
            self.initialize()
        
        print(f"\nProcessing query: '{query}' (quick_mode={quick_mode})")
        
        # Parse query
        parsed = self.query_parser.parse_query(query)
        criteria = parsed['criteria']
        location = parsed['location']
        constraints = parsed['constraints']
        
        print(f"Extracted criteria: {criteria}")
        print(f"Location filter: {location}")
        print(f"Constraints: {constraints}")
        
        # Prepare location filter
        location_filter = None
        if location.get('area'):
            location_filter = {'area': location['area']}
            # Try to find area center coordinates
            area_center = self._get_area_center(location['area'])
            if area_center:
                location_filter['area_center'] = area_center
                if 'max_distance' in constraints:
                    location_filter['max_distance_km'] = constraints['max_distance']
        
        # Optimize: Apply location filter first to reduce dataset size
        listings_to_process = self.listings_df.copy()
        
        # Quick pre-filter: Limit to first 2k listings in quick mode for much faster speed
        if quick_mode and len(listings_to_process) > 2000:
            listings_to_process = listings_to_process.head(2000).copy()
            print(f"Quick mode: Using first 2,000 listings for faster search")
        
        # For non-quick mode, still limit to reasonable size but calculate distances
        if not quick_mode and len(listings_to_process) > 5000:
            listings_to_process = listings_to_process.head(5000).copy()
            print(f"Processing first 5,000 listings for distance calculations (out of {len(self.listings_df)})")
        
        if location_filter and location_filter.get('area'):
            area = location_filter['area'].lower()
            # Initialize mask with same index as DataFrame
            mask = pd.Series(False, index=listings_to_process.index)
            # Search in multiple columns for better location matching
            search_columns = [
                'name', 'neighbourhood', 'neighbourhood_cleansed', 'description',
                'neighborhood_overview', 'city', 'market', 'smart_location'
            ]
            for col in search_columns:
                if col in listings_to_process.columns:
                    mask |= listings_to_process[col].astype(str).str.lower().str.contains(area, na=False, regex=False)
            
            # Also check if property type matches "apartment" if mentioned in query
            query_lower = query.lower()
            if 'apartment' in query_lower or 'flat' in query_lower:
                if 'property_type' in listings_to_process.columns:
                    property_mask = listings_to_process['property_type'].astype(str).str.lower().str.contains(
                        'apartment|flat|condo|condominium', na=False, regex=True
                    )
                    # Combine with location filter (both should match)
                    mask = mask & property_mask
            
            if mask.any():
                # Use .loc for proper indexing
                listings_to_process = listings_to_process.loc[mask].copy()
                print(f"Location filter (area: {area}) reduced dataset to {len(listings_to_process)} listings")
            else:
                print(f"Warning: No listings found matching area '{area}'. Searching all listings...")
        
        # Calculate proximity scores (optimized approach)
        if quick_mode:
            # Skip ALL expensive distance calculations in quick mode
            print("Quick mode: Skipping distance calculations for maximum speed")
            listings_with_proximity = listings_to_process.copy()
            listings_with_proximity['metro_distance_km'] = None
            listings_with_proximity['nearest_metro'] = None
            listings_with_proximity['grocery_distance_km'] = None
            listings_with_proximity['nearest_grocery'] = None
            # Use neutral scores (0.5) so they don't drag down the workspace score
            listings_with_proximity['metro_proximity_score'] = 0.5
            listings_with_proximity['grocery_proximity_score'] = 0.5
        else:
            # OPTIMIZED: First do quick ranking without distances, then calculate distances only for top candidates
            print("Full mode: Using two-phase approach (quick rank → distance calc for top candidates)")
            
            # Phase 1: Quick ranking without distances (use neutral scores)
            listings_quick = listings_to_process.copy()
            listings_quick['metro_proximity_score'] = 0.5
            listings_quick['grocery_proximity_score'] = 0.5
            
            # Quick pre-filter by basic criteria
            if criteria.get('wifi_quality', 0) > 0.2:
                wifi_mask = listings_quick['has_wifi'] == True
                if wifi_mask.any():
                    listings_quick = listings_quick.loc[wifi_mask].copy()
                    print(f"Wi-Fi filter: {len(listings_quick)} listings with Wi-Fi")
            if criteria.get('quiet_workspace', 0) > 0.2:
                room_type_mask = listings_quick['room_type'].astype(str).str.lower().str.contains('entire', na=False)
                workspace_mask = listings_quick.get('has_workspace', pd.Series([False] * len(listings_quick))) == True
                quiet_mask = room_type_mask | workspace_mask
                if quiet_mask.any():
                    listings_quick = listings_quick.loc[quiet_mask].copy()
                    print(f"Quiet workspace filter: {len(listings_quick)} listings with workspace features")
            
            # Quick rank to get top candidates
            ranked_quick = self.scorer.rank_listings(listings_quick, criteria, location_filter)
            
            # Phase 2: Calculate distances only for top 200 candidates (much faster!)
            top_candidates = ranked_quick.head(200)
            print(f"Calculating distances for top {len(top_candidates)} candidates (out of {len(ranked_quick)} ranked)")
            
            max_metro_dist = constraints.get('max_metro_distance', 2.0)
            max_grocery_dist = constraints.get('max_grocery_distance', 1.0)
            
            top_with_distances = self.distance_calc.calculate_proximity_scores(
                top_candidates,
                self.metro_stations,
                self.grocery_stores,
                max_metro_distance=max_metro_dist,
                max_grocery_distance=max_grocery_dist
            )
            
            # Phase 3: Re-rank top candidates with actual distances
            final_ranked = self.scorer.rank_listings(top_with_distances, criteria, location_filter)
            
            # Combine: top candidates with distances + rest without distances
            rest_without_distances = ranked_quick.iloc[200:].copy()
            rest_without_distances['metro_distance_km'] = None
            rest_without_distances['nearest_metro'] = None
            rest_without_distances['grocery_distance_km'] = None
            rest_without_distances['nearest_grocery'] = None
            
            # Final combined ranking (top with distances will naturally rank higher)
            listings_with_proximity = pd.concat([final_ranked, rest_without_distances], ignore_index=False)
            listings_with_proximity = listings_with_proximity.sort_values('workspace_score', ascending=False)
        
        # Rank listings (already done in full mode, or do it now for quick mode)
        if quick_mode:
            # In quick mode, calculate scores more efficiently
            print("Quick mode: Using optimized ranking")
            # Pre-filter by basic criteria before expensive scoring
            # Use lower threshold (0.2) since normalized weights are typically 0.25-0.4
            if criteria.get('wifi_quality', 0) > 0.2:
                wifi_mask = listings_with_proximity['has_wifi'] == True
                if wifi_mask.any():
                    listings_with_proximity = listings_with_proximity.loc[wifi_mask].copy()
                    print(f"Wi-Fi filter: {len(listings_with_proximity)} listings with Wi-Fi")
            if criteria.get('quiet_workspace', 0) > 0.2:
                # Prefer entire places for quiet workspace
                room_type_mask = listings_with_proximity['room_type'].astype(str).str.lower().str.contains('entire', na=False)
                workspace_mask = listings_with_proximity.get('has_workspace', pd.Series([False] * len(listings_with_proximity))) == True
                # Include listings that are either entire place OR have workspace
                quiet_mask = room_type_mask | workspace_mask
                if quiet_mask.any():
                    listings_with_proximity = listings_with_proximity.loc[quiet_mask].copy()
                    print(f"Quiet workspace filter: {len(listings_with_proximity)} listings with workspace features")
            
            ranked_listings = self.scorer.rank_listings(
                listings_with_proximity,
                criteria,
                location_filter
            )
        else:
            # In full mode, ranking was already done in the two-phase approach above
            ranked_listings = listings_with_proximity
        
        # Select top K
        top_listings = ranked_listings.head(top_k)
        
        # Print summary of results
        print(f"\n{'='*60}")
        print(f"Search Results Summary:")
        print(f"  Query: '{query}'")
        print(f"  Location filter: {location_filter.get('area') if location_filter else 'None'}")
        print(f"  Total listings processed: {len(listings_with_proximity)}")
        print(f"  Top results returned: {len(top_listings)}")
        if len(top_listings) > 0:
            avg_score = top_listings['workspace_score'].mean()
            print(f"  Average workspace score: {avg_score:.2%}")
        print(f"{'='*60}\n")
        
        return top_listings
    
    def _get_area_center(self, area_name: str) -> Optional[tuple]:
        """Get approximate center coordinates for an area."""
        # London area coordinates - based on the dataset being used
        area_coords = {
            'westminster': (51.4975, -0.1357),
            'camden': (51.5450, -0.1430),
            'islington': (51.5362, -0.1030),
            'hackney': (51.5450, -0.0550),
            'tower hamlets': (51.5200, -0.0290),
            'southwark': (51.5030, -0.0870),
            'lambeth': (51.4950, -0.1110),
            'kensington': (51.4990, -0.1930),
            'chelsea': (51.4870, -0.1690),
            'shoreditch': (51.5230, -0.0750),
            'soho': (51.5150, -0.1320),
            'covent garden': (51.5120, -0.1230),
            'finsbury park': (51.5642, -0.1065),
            'camberwell': (51.4740, -0.0920),
            'rotherhithe': (51.5000, -0.0500),
        }
        
        area_lower = area_name.lower()
        return area_coords.get(area_lower)
    
    def format_results(self, results_df: pd.DataFrame) -> List[Dict]:
        """
        Format results for display.
        
        Args:
            results_df: DataFrame with ranked listings
        
        Returns:
            List of formatted result dictionaries
        """
        formatted = []
        
        def _extract_image_url(row: pd.Series) -> Optional[str]:
            """Extract the best available image URL from listing data."""
            candidates = []
            
            # Priority order: prefer actual room images
            # Try various URL fields in order of preference
            url_fields = [
                'picture_url',
                'xl_picture_url', 
                'medium_url',
                'thumbnail_url',
                'image_url',
            ]
            
            for field in url_fields:
                url = row.get(field)
                if pd.notna(url) and isinstance(url, str) and url.strip():
                    url = url.strip()
                    # Validate it's a proper HTTP URL
                    if url.startswith(('http://', 'https://')):
                        # Ensure URL is complete (not truncated)
                        if len(url) > 20:  # Minimum reasonable URL length
                            candidates.append(url)
            
            # Try parse 'images' field if present (could be JSON or comma-separated)
            images_field = row.get('images') or row.get('photos') or row.get('image_urls')
            if pd.notna(images_field) and isinstance(images_field, str):
                try:
                    import json as _json
                    if images_field.strip().startswith('['):
                        arr = _json.loads(images_field.replace("'", '"'))
                        if isinstance(arr, list) and arr:
                            for img_url in arr:
                                if isinstance(img_url, str) and img_url.startswith(('http://', 'https://')):
                                    candidates.insert(0, img_url)  # Prefer first image from array
                except Exception:
                    # Fallback: comma-separated
                    if ',' in images_field:
                        for url_part in images_field.split(','):
                            url = url_part.strip().strip('"').strip("'")
                            if url.startswith(('http://', 'https://')) and len(url) > 20:
                                candidates.insert(0, url)
            
            # Return the first valid candidate
            for url in candidates:
                if url and isinstance(url, str):
                    return url
            return None

        for idx, row in results_df.iterrows():
            picture_url = _extract_image_url(row)
            result = {
                'id': row.get('id', 'N/A'),
                'name': row.get('name', 'Unnamed Listing'),
                'workspace_score': round(row.get('workspace_score', 0), 3),
                'location': {
                    'latitude': row.get('latitude'),
                    'longitude': row.get('longitude'),
                },
                'property_type': row.get('property_type', 'Unknown'),
                'room_type': row.get('room_type', 'Unknown'),
                'has_wifi': row.get('has_wifi', False),
                'has_workspace': row.get('has_workspace', False),
                'metro_distance_km': round(row.get('metro_distance_km', float('inf')), 2) if pd.notna(row.get('metro_distance_km')) else None,
                'nearest_metro': row.get('nearest_metro'),
                'grocery_distance_km': round(row.get('grocery_distance_km', float('inf')), 2) if pd.notna(row.get('grocery_distance_km')) else None,
                'nearest_grocery': row.get('nearest_grocery'),
                'price': row.get('price_numeric'),
                'picture_url': picture_url,
            }
            
            # Add description if available
            if 'description' in row and pd.notna(row['description']):
                desc = str(row['description'])
                result['description'] = desc[:200] + '...' if len(desc) > 200 else desc
            
            formatted.append(result)
        
        return formatted

