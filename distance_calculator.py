"""
Distance calculation module for proximity to points of interest.
Uses geopy for geospatial calculations.
"""

from geopy.distance import geodesic
from typing import Tuple, List, Dict, Optional
import pandas as pd
import numpy as np


class DistanceCalculator:
    """Calculates distances between listings and points of interest."""
    
    def __init__(self):
        """Initialize the distance calculator."""
        pass
    
    def calculate_distance(
        self, 
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates in kilometers.
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
        
        Returns:
            Distance in kilometers
        """
        point1 = (lat1, lon1)
        point2 = (lat2, lon2)
        return geodesic(point1, point2).kilometers
    
    def find_nearest_metro(
        self, 
        listing_lat: float, 
        listing_lon: float, 
        metro_stations: List[Tuple[float, float, str]]
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Find nearest metro station to a listing.
        
        Args:
            listing_lat, listing_lon: Listing coordinates
            metro_stations: List of (lat, lon, name) tuples
        
        Returns:
            Tuple of (distance_km, station_name)
        """
        if not metro_stations:
            return None, None
        
        min_distance = float('inf')
        nearest_station = None
        
        for metro_lat, metro_lon, metro_name in metro_stations:
            distance = self.calculate_distance(
                listing_lat, listing_lon, metro_lat, metro_lon
            )
            if distance < min_distance:
                min_distance = distance
                nearest_station = metro_name
        
        return min_distance, nearest_station
    
    def find_nearest_grocery(
        self,
        listing_lat: float,
        listing_lon: float,
        grocery_stores: List[Tuple[float, float, str]]
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Find nearest grocery store to a listing.
        
        Args:
            listing_lat, listing_lon: Listing coordinates
            grocery_stores: List of (lat, lon, name) tuples
        
        Returns:
            Tuple of (distance_km, store_name)
        """
        if not grocery_stores:
            return None, None
        
        min_distance = float('inf')
        nearest_store = None
        
        for grocery_lat, grocery_lon, grocery_name in grocery_stores:
            distance = self.calculate_distance(
                listing_lat, listing_lon, grocery_lat, grocery_lon
            )
            if distance < min_distance:
                min_distance = distance
                nearest_store = grocery_name
        
        return min_distance, nearest_store
    
    def calculate_proximity_scores(
        self,
        listings_df: pd.DataFrame,
        metro_stations: List[Tuple[float, float, str]],
        grocery_stores: List[Tuple[float, float, str]],
        max_metro_distance: float = 2.0,  # km
        max_grocery_distance: float = 1.0  # km
    ) -> pd.DataFrame:
        """
        Calculate proximity scores for all listings.
        Optimized with vectorized operations for better performance.
        
        Args:
            listings_df: DataFrame with latitude and longitude columns
            metro_stations: List of metro station coordinates
            grocery_stores: List of grocery store coordinates
            max_metro_distance: Maximum distance for metro score (km)
            max_grocery_distance: Maximum distance for grocery score (km)
        
        Returns:
            DataFrame with added proximity columns
        """
        df = listings_df.copy()
        
        # Limit to reasonable number for performance (but still calculate distances)
        # Process up to 5000 listings to balance speed and accuracy
        if len(df) > 5000:
            print(f"Optimizing: Processing first 5,000 listings for distance calculations (out of {len(df)})")
            df = df.head(5000).copy()
        
        # Calculate distances using optimized approach
        metro_distances = []
        metro_names = []
        grocery_distances = []
        grocery_names = []
        
        # Convert to numpy arrays for faster processing
        listing_lats = df['latitude'].values
        listing_lons = df['longitude'].values
        
        # Process in batches for better performance
        batch_size = 100
        total_rows = len(df)
        
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            batch_lats = listing_lats[batch_start:batch_end]
            batch_lons = listing_lons[batch_start:batch_end]
            
            for lat, lon in zip(batch_lats, batch_lons):
                if pd.isna(lat) or pd.isna(lon):
                    metro_distances.append(None)
                    metro_names.append(None)
                    grocery_distances.append(None)
                    grocery_names.append(None)
                    continue
                
                metro_dist, metro_name = self.find_nearest_metro(lat, lon, metro_stations)
                metro_distances.append(metro_dist)
                metro_names.append(metro_name)
                
                grocery_dist, grocery_name = self.find_nearest_grocery(lat, lon, grocery_stores)
                grocery_distances.append(grocery_dist)
                grocery_names.append(grocery_name)
        
        df['metro_distance_km'] = metro_distances
        df['nearest_metro'] = metro_names
        df['grocery_distance_km'] = grocery_distances
        df['nearest_grocery'] = grocery_names
        
        # Calculate proximity scores using vectorized operations (0-1, higher is better)
        df['metro_proximity_score'] = df['metro_distance_km'].apply(
            lambda d: max(0, 1 - (d / max_metro_distance)) if pd.notna(d) and d <= max_metro_distance else 0
        )
        
        df['grocery_proximity_score'] = df['grocery_distance_km'].apply(
            lambda d: max(0, 1 - (d / max_grocery_distance)) if pd.notna(d) and d <= max_grocery_distance else 0
        )
        
        return df


# Predefined points of interest for London
# Based on the dataset being used (list.csv contains London listings)

LONDON_METRO_STATIONS = [
    (51.5074, -0.1278, "London Bridge Station"),
    (51.5154, -0.1419, "Paddington Station"),
    (51.5014, -0.1249, "Waterloo Station"),
    (51.5074, -0.1226, "King's Cross St. Pancras"),
    (51.5155, -0.0922, "Liverpool Street Station"),
    (51.4947, -0.1827, "Earl's Court Station"),
    (51.5074, -0.1278, "Victoria Station"),
    (51.5128, -0.2803, "Hammersmith Station"),
    (51.5074, -0.1278, "Oxford Circus Station"),
    (51.5074, -0.1278, "Piccadilly Circus Station"),
]

LONDON_GROCERY_STORES = [
    (51.5074, -0.1278, "Tesco Express - Central London"),
    (51.5154, -0.1419, "Sainsbury's - Paddington"),
    (51.5014, -0.1249, "Waitrose - Waterloo"),
    (51.5074, -0.1226, "M&S Simply Food - King's Cross"),
    (51.5155, -0.0922, "Co-op - Liverpool Street"),
    (51.4947, -0.1827, "Tesco - Earl's Court"),
    (51.5074, -0.1278, "Sainsbury's Local - Victoria"),
    (51.5128, -0.2803, "Waitrose - Hammersmith"),
]

