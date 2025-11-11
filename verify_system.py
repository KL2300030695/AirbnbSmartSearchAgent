"""
Quick verification script to check all components work
"""
import sys

def verify_imports():
    """Verify all imports work."""
    print("Verifying imports...")
    try:
        from agent import AirbnbSearchAgent
        from distance_calculator import LONDON_METRO_STATIONS, LONDON_GROCERY_STORES
        from query_parser import QueryParser
        from scorer import WorkspaceScorer
        from data_loader import AirbnbDataLoader
        from api import app
        print("✅ All imports successful")
        print(f"✅ London Metro Stations: {len(LONDON_METRO_STATIONS)}")
        print(f"✅ London Grocery Stores: {len(LONDON_GROCERY_STORES)}")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def verify_no_bangalore():
    """Verify no Bangalore references."""
    print("\nChecking for Bangalore references...")
    import os
    import re
    
    files_to_check = [
        'agent.py', 'distance_calculator.py', 'query_parser.py',
        'api.py', 'README.md', 'test_agent.py'
    ]
    
    found = False
    for file in files_to_check:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                if re.search(r'[Bb]angalore|BANGALORE|indiranagar|Indiranagar', content):
                    print(f"⚠️  Found Bangalore reference in {file}")
                    found = True
    
    if not found:
        print("✅ No Bangalore references found")
    return not found

def verify_data_path():
    """Verify data file exists."""
    print("\nChecking data files...")
    import os
    
    if os.path.exists('list.csv'):
        size_mb = os.path.getsize('list.csv') / (1024 * 1024)
        print(f"✅ list.csv exists ({size_mb:.1f} MB)")
    else:
        print("⚠️  list.csv not found")
    
    if os.path.exists('list_sample.csv'):
        size_mb = os.path.getsize('list_sample.csv') / (1024 * 1024)
        print(f"✅ list_sample.csv exists ({size_mb:.1f} MB)")
    else:
        print("ℹ️  list_sample.csv not found (optional)")

if __name__ == "__main__":
    print("="*80)
    print("SYSTEM VERIFICATION")
    print("="*80)
    
    imports_ok = verify_imports()
    bangalore_ok = verify_no_bangalore()
    verify_data_path()
    
    print("\n" + "="*80)
    if imports_ok and bangalore_ok:
        print("✅ SYSTEM READY")
    else:
        print("⚠️  Some issues found - check above")
    print("="*80)

