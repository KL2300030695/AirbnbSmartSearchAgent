"""
Quick test script for the API (without starting server).
Tests the agent initialization and a simple search.
"""

import os
from agent import AirbnbSearchAgent

def test_agent_with_csv():
    """Test agent with the list.csv file."""
    print("Testing Airbnb Smart Search Agent with list.csv")
    print("="*80)
    
    data_path = "list.csv"
    if not os.path.exists(data_path):
        print(f"[ERROR] {data_path} not found!")
        return
    
    print(f"\n[OK] Found {data_path}")
    print("Initializing agent (this may take a while for large files)...")
    
    try:
        # Initialize with Ollama (will fallback to rule-based if Ollama not available)
        agent = AirbnbSearchAgent(
            data_path=data_path,
            use_llm=True,
            llm_model="llama3.2:3b"
        )
        agent.initialize()
        
        print(f"\n[OK] Agent initialized with {len(agent.listings_df)} listings")
        
        # Test a simple search
        print("\nTesting search query...")
        query = "Find apartments with Wi-Fi and quiet workspace"
        
        results_df = agent.search(query, top_k=5)
        formatted = agent.format_results(results_df)
        
        print(f"\n[OK] Found {len(formatted)} results")
        for i, result in enumerate(formatted[:3], 1):
            print(f"\n  {i}. {result['name']}")
            print(f"     Score: {result['workspace_score']:.3f}")
            print(f"     Wi-Fi: {result['has_wifi']}")
            print(f"     Workspace: {result['has_workspace']}")
        
        print("\n" + "="*80)
        print("[OK] Test completed successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent_with_csv()

