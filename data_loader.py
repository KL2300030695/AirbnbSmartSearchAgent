"""
Data loader for Airbnb listings dataset.
Handles loading, parsing, and preprocessing of Airbnb data.
"""

import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Optional


class AirbnbDataLoader:
    """Loads and preprocesses Airbnb listing data."""
    
    def __init__(self, data_path: str = "list.csv"):
        """
        Initialize the data loader.
        
        Args:
            data_path: Path to the listings CSV file
        """
        self.data_path = data_path
        self.df: Optional[pd.DataFrame] = None
        
    def load_data(self) -> pd.DataFrame:
        """Load Airbnb listings from CSV file."""
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(
                f"Dataset not found at {self.data_path}. "
                "Please download from http://insideairbnb.com/get-the-data.html"
            )
        
        print(f"Loading data from {self.data_path}...")
        # Check file size first
        file_size_mb = os.path.getsize(self.data_path) / (1024 * 1024)
        
        # Use chunked reading for files larger than 50MB
        if file_size_mb > 50:
            print(f"Large file detected ({file_size_mb:.1f} MB), using optimized chunked reading...")
            chunks = []
            chunk_size = 20000  # Larger chunks for better performance
            for i, chunk in enumerate(pd.read_csv(self.data_path, chunksize=chunk_size, low_memory=False)):
                chunks.append(chunk)
                if (i + 1) % 10 == 0:
                    print(f"  Loaded {len(chunks) * chunk_size:,} rows...")
            self.df = pd.concat(chunks, ignore_index=True)
        else:
            self.df = pd.read_csv(self.data_path, low_memory=False)
        print(f"Loaded {len(self.df):,} listings")
        return self.df
    
    def preprocess(self) -> pd.DataFrame:
        """Preprocess the loaded data."""
        if self.df is None:
            self.load_data()
        
        # Ensure required columns exist
        required_cols = ['id', 'latitude', 'longitude']
        missing_cols = [col for col in required_cols if col not in self.df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Filter out listings without coordinates
        self.df = self.df.dropna(subset=['latitude', 'longitude'])
        
        # Parse amenities if available (optimized)
        print("Preprocessing amenities...")
        if 'amenities' in self.df.columns:
            # Use vectorized string operations where possible
            self.df['amenities_list'] = self.df['amenities'].apply(self._parse_amenities)
            
            # Convert to string for faster searching
            amenities_str = self.df['amenities'].astype(str).str.lower()
            
            # Extract workspace-related features using vectorized operations
            self.df['has_wifi'] = amenities_str.str.contains('wifi|internet', case=False, na=False, regex=True)
            self.df['has_workspace'] = amenities_str.str.contains('workspace|desk|laptop', case=False, na=False, regex=True)
        else:
            self.df['amenities_list'] = [[]] * len(self.df)
            self.df['has_wifi'] = False
            self.df['has_workspace'] = False
        
        # Extract property type and room type
        if 'property_type' not in self.df.columns:
            self.df['property_type'] = 'Unknown'
        if 'room_type' not in self.df.columns:
            self.df['room_type'] = 'Unknown'
        
        # Extract price if available
        if 'price' in self.df.columns:
            self.df['price_numeric'] = self.df['price'].apply(self._parse_price)
        else:
            self.df['price_numeric'] = np.nan
        
        print(f"Preprocessed {len(self.df)} listings")
        return self.df
    
    def _parse_amenities(self, amenities_str: str) -> List[str]:
        """Parse amenities string into a list."""
        if pd.isna(amenities_str):
            return []
        
        try:
            # Try JSON parsing first
            if isinstance(amenities_str, str) and amenities_str.startswith('['):
                return json.loads(amenities_str.replace("'", '"'))
            # Otherwise, try comma-separated
            elif isinstance(amenities_str, str):
                return [a.strip().strip('"').strip("'") for a in amenities_str.split(',')]
        except:
            pass
        
        return []
    
    def _parse_price(self, price_str: str) -> float:
        """Parse price string to float."""
        if pd.isna(price_str):
            return np.nan
        
        try:
            # Remove currency symbols and commas
            price_clean = str(price_str).replace('$', '').replace(',', '').replace('€', '').replace('£', '').strip()
            return float(price_clean)
        except:
            return np.nan
    
    def get_listings(self) -> pd.DataFrame:
        """Get the preprocessed listings dataframe."""
        if self.df is None:
            self.preprocess()
        return self.df
    
    def get_listing_by_id(self, listing_id: int) -> Optional[Dict]:
        """Get a specific listing by ID."""
        if self.df is None:
            self.preprocess()
        
        listing = self.df[self.df['id'] == listing_id]
        if len(listing) == 0:
            return None
        
        return listing.iloc[0].to_dict()

