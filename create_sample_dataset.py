"""
Create a smaller sample dataset for faster testing.
Extracts first N rows from list.csv for quick testing.
"""

import pandas as pd
import os

def create_sample_dataset(source_file="list.csv", output_file="list_sample.csv", num_rows=5000):
    """
    Create a smaller sample dataset for faster testing.
    
    Args:
        source_file: Source CSV file
        output_file: Output sample file
        num_rows: Number of rows to include
    """
    if not os.path.exists(source_file):
        print(f"❌ Source file {source_file} not found!")
        return
    
    print(f"Creating sample dataset from {source_file}...")
    print(f"Extracting first {num_rows:,} rows...")
    
    # Read in chunks to avoid memory issues
    chunks = []
    total_read = 0
    
    for chunk in pd.read_csv(source_file, chunksize=1000, low_memory=False):
        chunks.append(chunk)
        total_read += len(chunk)
        
        if total_read >= num_rows:
            # Trim last chunk if needed
            if total_read > num_rows:
                excess = total_read - num_rows
                chunks[-1] = chunks[-1].iloc[:-excess]
            break
        
        if len(chunks) % 10 == 0:
            print(f"  Read {total_read:,} rows...")
    
    # Combine chunks
    sample_df = pd.concat(chunks, ignore_index=True)
    
    # Save
    sample_df.to_csv(output_file, index=False)
    
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"\n✅ Sample dataset created!")
    print(f"   File: {output_file}")
    print(f"   Rows: {len(sample_df):,}")
    print(f"   Size: {file_size_mb:.1f} MB")
    print(f"\nTo use it, set environment variable:")
    print(f"   set DATA_PATH={output_file}")
    print(f"   python run_api.py")

if __name__ == "__main__":
    import sys
    
    num_rows = 5000
    if len(sys.argv) > 1:
        try:
            num_rows = int(sys.argv[1])
        except:
            print("Usage: python create_sample_dataset.py [num_rows]")
            print("Default: 5000 rows")
    
    create_sample_dataset(num_rows=num_rows)

