"""
Test search speed and diagnose timeout issues.
"""
import time
import requests
import sys

def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    try:
        start = time.time()
        r = requests.get('http://localhost:8000/health', timeout=10)
        elapsed = time.time() - start
        print(f"✅ Health check: {r.status_code} in {elapsed:.2f}s")
        print(f"   Response: {r.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_search(query="quiet workspace wifi", quick_mode=True):
    """Test search endpoint."""
    print(f"\nTesting search: '{query}' (quick_mode={quick_mode})...")
    try:
        start = time.time()
        url = f'http://localhost:8000/search?query={query}&top_k=10&quick_mode={str(quick_mode).lower()}'
        r = requests.get(url, timeout=20)
        elapsed = time.time() - start
        print(f"✅ Search completed: {r.status_code} in {elapsed:.2f}s")
        if r.status_code == 200:
            data = r.json()
            print(f"   Results: {data.get('results_count', 0)}")
            print(f"   Success: {data.get('success', False)}")
            if data.get('results'):
                print(f"   First result: {data['results'][0].get('name', 'N/A')[:50]}")
        else:
            print(f"   Error: {r.text[:200]}")
        return elapsed
    except requests.exceptions.Timeout:
        print(f"❌ Search timed out after 20s")
        return None
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return None

if __name__ == "__main__":
    print("="*60)
    print("SEARCH SPEED TEST")
    print("="*60)
    
    # Wait for server
    print("\nWaiting for server to be ready...")
    for i in range(10):
        if test_health():
            break
        time.sleep(2)
        print(f"  Retry {i+1}/10...")
    else:
        print("❌ Server not responding. Is it running?")
        sys.exit(1)
    
    # Test quick search
    elapsed = test_search("quiet workspace wifi london", quick_mode=True)
    
    if elapsed and elapsed > 15:
        print(f"\n⚠️  WARNING: Search took {elapsed:.2f}s (UI timeout is 15s)")
        print("   Consider using sample dataset or further optimization")
    elif elapsed:
        print(f"\n✅ Search is fast enough: {elapsed:.2f}s")
    
    print("\n" + "="*60)

