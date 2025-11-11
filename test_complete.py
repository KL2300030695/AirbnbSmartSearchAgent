"""
Complete system test - verifies everything works
"""
import requests
import time

API_URL = "http://localhost:8000"

def test_system():
    print("="*80)
    print("COMPLETE SYSTEM TEST")
    print("="*80)
    
    # Test 1: Health check
    print("\n1. Testing Health Endpoint...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health: {data.get('status')}")
            print(f"   ✅ Data Loaded: {data.get('data_loaded')}")
            if data.get('listings_count'):
                print(f"   ✅ Listings: {data.get('listings_count'):,}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Cannot connect: {e}")
        print(f"   Make sure server is running at {API_URL}")
        return
    
    # Test 2: Search
    print("\n2. Testing Search...")
    try:
        query = "Find apartments in London with Wi-Fi and workspace"
        start = time.time()
        response = requests.get(
            f"{API_URL}/search",
            params={"query": query, "top_k": 5, "quick_mode": True},
            timeout=20
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Search completed in {elapsed:.2f}s")
            print(f"   ✅ Results: {data.get('results_count', 0)}")
            if data.get('results_count', 0) > 0:
                result = data['results'][0]
                print(f"   ✅ Top result: {result.get('name', 'N/A')}")
                print(f"   ✅ Score: {result.get('workspace_score', 0):.3f}")
        else:
            print(f"   ❌ Search failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Search error: {e}")
    
    # Test 3: UI
    print("\n3. Testing UI...")
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ UI loads successfully")
        else:
            print(f"   ⚠️  UI status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ UI error: {e}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_system()

