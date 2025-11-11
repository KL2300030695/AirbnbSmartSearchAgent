"""
Workspace scoring and ranking module.
Computes composite scores based on user criteria.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class WorkspaceScorer:
    """Calculates workspace quality scores for listings."""
    
    def __init__(self):
        """Initialize the workspace scorer."""
        pass
    
    def calculate_workspace_score(
        self,
        listing: pd.Series,
        criteria: Dict[str, float]
    ) -> float:
        """
        Calculate workspace score based on user criteria.
        
        Args:
            listing: Single listing row from DataFrame
            criteria: Dictionary with weights for different factors
                - quiet_workspace: weight for quiet workspace (0-1)
                - wifi_quality: weight for Wi-Fi quality (0-1)
                - metro_proximity: weight for metro proximity (0-1)
                - grocery_proximity: weight for grocery proximity (0-1)
        
        Returns:
            Composite workspace score (0-1)
        """
        score = 0.0
        total_weight = 0.0
        
        # Quiet workspace score
        if criteria.get('quiet_workspace', 0) > 0:
            quiet_score = self._calculate_quiet_score(listing)
            weight = criteria['quiet_workspace']
            score += quiet_score * weight
            total_weight += weight
        
        # Wi-Fi quality score
        if criteria.get('wifi_quality', 0) > 0:
            wifi_score = self._calculate_wifi_score(listing)
            weight = criteria['wifi_quality']
            score += wifi_score * weight
            total_weight += weight
        
        # Metro proximity score
        if criteria.get('metro_proximity', 0) > 0:
            metro_score = listing.get('metro_proximity_score', 0.5)  # Default to 0.5 if missing
            weight = criteria['metro_proximity']
            score += metro_score * weight
            total_weight += weight
        
        # Grocery proximity score
        if criteria.get('grocery_proximity', 0) > 0:
            grocery_score = listing.get('grocery_proximity_score', 0.5)  # Default to 0.5 if missing
            weight = criteria['grocery_proximity']
            score += grocery_score * weight
            total_weight += weight
        
        # If no criteria specified, calculate a default score based on available features
        if total_weight == 0:
            # Default scoring when no specific criteria
            base_score = 0.3  # Base score
            if listing.get('has_wifi', False):
                base_score += 0.3
            if listing.get('has_workspace', False):
                base_score += 0.2
            room_type = str(listing.get('room_type', '')).lower()
            if 'entire' in room_type:
                base_score += 0.2
            return min(1.0, base_score)
        
        # Normalize by total weight
        if total_weight > 0:
            score = score / total_weight
        
        return min(1.0, max(0.0, score))
    
    def _calculate_quiet_score(self, listing: pd.Series) -> float:
        """
        Calculate quiet workspace score.
        Based on property type, room type, and amenities.
        """
        score = 0.5  # Base score
        
        # Entire place is generally quieter
        room_type = str(listing.get('room_type', '')).lower()
        if 'entire' in room_type:
            score += 0.3
        elif 'private' in room_type:
            score += 0.1
        
        # Property type considerations
        property_type = str(listing.get('property_type', '')).lower()
        if 'apartment' in property_type or 'condo' in property_type:
            score += 0.1
        elif 'house' in property_type:
            score += 0.15
        
        # Check for quiet-related amenities
        amenities = listing.get('amenities_list', [])
        if isinstance(amenities, list):
            amenities_str = ' '.join([str(a).lower() for a in amenities])
            if 'quiet' in amenities_str:
                score += 0.1
            if 'soundproof' in amenities_str:
                score += 0.15
        
        return min(1.0, score)
    
    def _calculate_wifi_score(self, listing: pd.Series) -> float:
        """
        Calculate Wi-Fi quality score.
        Based on Wi-Fi availability and related amenities.
        """
        score = 0.0
        
        # Check if Wi-Fi is available
        has_wifi = listing.get('has_wifi', False)
        if has_wifi:
            score = 0.7  # Base score for having Wi-Fi
        
        # Check for high-speed internet mentions
        amenities = listing.get('amenities_list', [])
        if isinstance(amenities, list):
            amenities_str = ' '.join([str(a).lower() for a in amenities])
            if 'high speed' in amenities_str or 'fast' in amenities_str:
                score += 0.2
            if 'ethernet' in amenities_str or 'wired' in amenities_str:
                score += 0.1
        
        return min(1.0, score)
    
    def rank_listings(
        self,
        listings_df: pd.DataFrame,
        criteria: Dict[str, float],
        location_filter: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        Rank listings based on workspace score and criteria.
        
        Args:
            listings_df: DataFrame with listings
            criteria: User criteria with weights
            location_filter: Optional location filter dict with:
                - area: area name to filter by
                - max_distance_km: maximum distance from area center
        
        Returns:
            DataFrame sorted by workspace score (descending)
        """
        df = listings_df.copy()
        
        # Apply location filter if provided
        if location_filter:
            df = self._apply_location_filter(df, location_filter)
        
        # Calculate workspace scores (optimized for speed)
        # Use vectorized operations where possible
        df['workspace_score'] = 0.0
        
        # Base score from features
        if criteria.get('wifi_quality', 0) > 0:
            wifi_col = df.get('has_wifi', pd.Series([False] * len(df)))
            df['workspace_score'] += wifi_col.astype(float) * criteria['wifi_quality']
        if criteria.get('quiet_workspace', 0) > 0:
            workspace_col = df.get('has_workspace', pd.Series([False] * len(df)))
            room_type_col = df.get('room_type', pd.Series([''] * len(df)))
            quiet_score = workspace_col.astype(float) * 0.5
            quiet_score += (room_type_col.astype(str).str.lower().str.contains('entire', na=False).astype(float) * 0.5)
            df['workspace_score'] += quiet_score * criteria['quiet_workspace']
        
        # Proximity scores (already calculated or defaulted)
        if criteria.get('metro_proximity', 0) > 0:
            metro_score = df.get('metro_proximity_score', 0.5)
            df['workspace_score'] += pd.to_numeric(metro_score, errors='coerce').fillna(0.5) * criteria['metro_proximity']
        if criteria.get('grocery_proximity', 0) > 0:
            grocery_score = df.get('grocery_proximity_score', 0.5)
            df['workspace_score'] += pd.to_numeric(grocery_score, errors='coerce').fillna(0.5) * criteria['grocery_proximity']
        
        # Normalize scores to 0-1 range first
        raw_scores = pd.to_numeric(df['workspace_score'], errors='coerce').fillna(0).clip(0, 1)

        # Stretch distribution per-query using min-max scaling for better visual spread
        s_min = float(raw_scores.min()) if len(raw_scores) else 0.0
        s_max = float(raw_scores.max()) if len(raw_scores) else 1.0
        if s_max > s_min:
            scaled = (raw_scores - s_min) / (s_max - s_min)
            df['workspace_score'] = scaled.clip(0, 1)
        else:
            # All scores identical; keep as-is
            df['workspace_score'] = raw_scores
        
        # Sort by workspace score
        df = df.sort_values('workspace_score', ascending=False)
        
        return df
    
    def _apply_location_filter(
        self,
        df: pd.DataFrame,
        location_filter: Dict
    ) -> pd.DataFrame:
        """Apply location-based filtering."""
        area = location_filter.get('area', '').lower()
        
        if not area:
            return df
        
        # Try to match area in various columns
        # Initialize mask with same index as DataFrame
        mask = pd.Series(False, index=df.index)
        
        # Check in name, neighborhood, or description columns
        for col in ['name', 'neighbourhood', 'neighbourhood_cleansed', 'neighborhood', 'description']:
            if col in df.columns:
                mask |= df[col].astype(str).str.lower().str.contains(area, na=False)
        
        # If max_distance is specified, filter by distance from area center
        if 'max_distance_km' in location_filter and 'area_center' in location_filter:
            center_lat, center_lon = location_filter['area_center']
            from distance_calculator import DistanceCalculator
            calc = DistanceCalculator()
            
            distances = df.apply(
                lambda row: calc.calculate_distance(
                    row['latitude'], row['longitude'], center_lat, center_lon
                ),
                axis=1
            )
            # Ensure distances Series has same index
            distances.index = df.index
            mask |= distances <= location_filter['max_distance_km']
        
        # Use .loc for proper indexing
        if mask.any():
            return df.loc[mask].copy()
        return df

