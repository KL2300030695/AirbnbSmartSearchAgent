"""
Test script for the Airbnb Smart Search Agent.
Tests the agent with sample queries.
"""

from agent import AirbnbSearchAgent
import os


def test_agent():
    """Test the agent with sample queries."""
    print("Testing Airbnb Smart Search Agent\n")
    print("="*80)
    
    # Create sample data if it doesn't exist
    data_path = "data/listings.csv"
    if not os.path.exists(data_path):
        print("Creating sample data...")
        from main import create_sample_data
        create_sample_data()
    
    # Initialize agent
    agent = AirbnbSearchAgent(data_path=data_path, use_llm=False)
    agent.initialize()
    
    # Test queries
    test_queries = [
        "Find apartments in London with a quiet workspace, stable Wi-Fi, and grocery stores within 1 km",
        "I need a place with good Wi-Fi and near metro station in London",
        "Looking for quiet workspace in Islington",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"Test Query {i}: {query}")
        print('='*80)
        
        try:
            results = agent.search(query, top_k=3)
            formatted = agent.format_results(results)
            
            print(f"\nFound {len(formatted)} results:")
            for j, result in enumerate(formatted, 1):
                print(f"\n  {j}. {result['name']}")
                print(f"     Score: {result['workspace_score']:.3f}")
                print(f"     Wi-Fi: {result['has_wifi']}")
                if result['metro_distance_km']:
                    print(f"     Metro: {result['metro_distance_km']} km")
                if result['grocery_distance_km']:
                    print(f"     Grocery: {result['grocery_distance_km']} km")
        
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("Testing complete!")


if __name__ == "__main__":
    test_agent()

