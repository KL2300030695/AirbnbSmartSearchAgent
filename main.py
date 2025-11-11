"""
Main entry point for Airbnb Smart Search Agent.
Provides CLI interface for user interaction.
"""

import os
import sys
from agent import AirbnbSearchAgent
import json


def print_result(result: dict, index: int):
    """Print a formatted result."""
    print(f"\n{'='*80}")
    print(f"#{index + 1} - {result['name']}")
    print(f"{'='*80}")
    print(f"Workspace Score: {result['workspace_score']:.3f} / 1.0")
    print(f"Property Type: {result['property_type']}")
    print(f"Room Type: {result['room_type']}")
    print(f"Wi-Fi Available: {'Yes' if result['has_wifi'] else 'No'}")
    print(f"Dedicated Workspace: {'Yes' if result['has_workspace'] else 'No'}")
    
    if result['metro_distance_km'] is not None:
        print(f"Nearest Metro: {result['nearest_metro']} ({result['metro_distance_km']} km)")
    else:
        print("Nearest Metro: Not found")
    
    if result['grocery_distance_km'] is not None:
        print(f"Nearest Grocery: {result['nearest_grocery']} ({result['grocery_distance_km']} km)")
    else:
        print("Nearest Grocery: Not found")
    
    if result.get('price'):
        print(f"Price: ${result['price']:.2f}")
    
    if result.get('description'):
        print(f"\nDescription: {result['description']}")
    
    print(f"Coordinates: ({result['location']['latitude']:.4f}, {result['location']['longitude']:.4f})")
    print(f"Listing ID: {result['id']}")


def main():
    """Main CLI interface."""
    print("="*80)
    print("Airbnb Smart Search Agent")
    print("="*80)
    print("\nThis agent helps you find Airbnb listings based on:")
    print("  - Quiet workspace requirements")
    print("  - Wi-Fi quality")
    print("  - Proximity to metro/bus stations")
    print("  - Proximity to grocery stores")
    print("\n" + "="*80)
    
    # Check if data file exists
    data_path = os.getenv("DATA_PATH", "list.csv")
    if not os.path.exists(data_path):
        print(f"\n[WARNING] Dataset not found at {data_path}")
        print("Please download the Airbnb dataset from:")
        print("http://insideairbnb.com/get-the-data.html")
        print("\nPlace the 'listings.csv' file in the 'data/' directory.")
        
        create_sample = input("\nWould you like to create a sample dataset for testing? (y/n): ")
        if create_sample.lower() == 'y':
            create_sample_data()
            print("\n[OK] Sample dataset created! You can now test the agent.")
        else:
            print("\nExiting. Please download the dataset and try again.")
            sys.exit(1)
    
    # Initialize agent
    use_llm = os.getenv('USE_LLM', 'true').lower() == 'true'
    llm_api_key = os.getenv('OPENAI_API_KEY')
    llm_model = os.getenv('LLM_MODEL', 'llama3.2:3b')
    
    try:
        agent = AirbnbSearchAgent(
            data_path=data_path,
            use_llm=use_llm,
            llm_api_key=llm_api_key,
            llm_model=llm_model
        )
        agent.initialize()
        
        if use_llm:
            print("[OK] LLM parsing enabled")
        else:
            print("[OK] Using rule-based query parsing (set USE_LLM=true to enable LLM)")
    except Exception as e:
        print(f"\n[ERROR] Error initializing agent: {e}")
        sys.exit(1)
    
    # Interactive loop
    print("\n" + "="*80)
    print("Ready to search! Type your query or 'quit' to exit.")
    print("="*80)
    
    while True:
        print("\n" + "-"*80)
        query = input("\nEnter your search query: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye!")
            break
        
        if not query:
            print("Please enter a valid query.")
            continue
        
        try:
            # Search
            results_df = agent.search(query, top_k=10)
            
            if len(results_df) == 0:
                print("\n[ERROR] No listings found matching your criteria.")
                print("Try adjusting your search query.")
                continue
            
            # Format and display results
            formatted_results = agent.format_results(results_df)
            
            print(f"\n[OK] Found {len(formatted_results)} listings:")
            
            for i, result in enumerate(formatted_results):
                print_result(result, i)
            
            # Option to save results
            save = input(f"\n\nSave results to JSON? (y/n): ").strip().lower()
            if save == 'y':
                output_file = "search_results.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(formatted_results, f, indent=2, ensure_ascii=False)
                print(f"[OK] Results saved to {output_file}")
        
        except Exception as e:
            print(f"\n[ERROR] Error during search: {e}")
            import traceback
            traceback.print_exc()


def create_sample_data():
    """Create a sample dataset for testing."""
    import pandas as pd
    import os
    
    os.makedirs("data", exist_ok=True)
    
    # Create sample listings
    sample_data = {
        'id': [1, 2, 3, 4, 5],
        'name': [
            'Cozy Apartment in Islington',
            'Modern Studio with Workspace',
            'Quiet House near Metro',
            'Spacious Condo with Wi-Fi',
            'Budget Room in Camden'
        ],
        'latitude': [51.5362, 51.5150, 51.5074, 51.5230, 51.5450],
        'longitude': [-0.1030, -0.1320, -0.1278, -0.0750, -0.1430],
        'property_type': ['Apartment', 'Studio', 'House', 'Condo', 'Private Room'],
        'room_type': ['Entire place', 'Entire place', 'Entire place', 'Entire place', 'Private room'],
        'amenities': [
            '["Wifi", "Kitchen", "Workspace", "Quiet"]',
            '["Wifi", "High-speed internet", "Laptop-friendly workspace"]',
            '["Wifi", "Kitchen", "Soundproof"]',
            '["Wifi", "Ethernet connection", "Dedicated workspace"]',
            '["Wifi", "Kitchen"]'
        ],
        'price': ['$50', '$75', '$100', '$90', '$30'],
        'description': [
            'Perfect for remote workers. Quiet neighborhood.',
            'Modern studio with dedicated workspace area.',
            'Peaceful house ideal for work from home.',
            'Spacious condo with excellent internet connection.',
            'Budget-friendly option in central location.'
        ]
    }
    
    df = pd.DataFrame(sample_data)
    df.to_csv("data/listings.csv", index=False)
    print("\n[OK] Created sample dataset with 5 listings")


if __name__ == "__main__":
    main()

