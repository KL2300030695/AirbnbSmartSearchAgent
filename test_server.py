"""
Quick test to verify server can start on port 8000
"""
import socket
import sys

def check_port(port):
    """Check if a port is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result != 0  # True if port is available

if __name__ == "__main__":
    port = 8000
    if check_port(port):
        print(f"✅ Port {port} is available")
        print("You can start the server with:")
        print("  uvicorn api:app --host 0.0.0.0 --port 8000")
    else:
        print(f"❌ Port {port} is in use")
        print("\nTry one of these:")
        print("  1. Find and stop the process using port 8000")
        print("  2. Use a different port: uvicorn api:app --host 0.0.0.0 --port 8001")
        sys.exit(1)

