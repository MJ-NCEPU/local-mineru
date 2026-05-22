#!/usr/bin/env python
# Production server runner using Waitress
from project.app import app
from waitress import serve
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == '__main__':
    # Get port from environment variable or use default 5000
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"Starting production server on {host}:{port}")
    print("Using Waitress as WSGI server")
    
    # Serve with Waitress - configure for high concurrency
    serve(
        app,
        host=host,
        port=port,
        threads=64,  # Number of worker threads
        connection_limit=1000,  # Maximum number of concurrent connections
        channel_timeout=300,  # Seconds to wait for a complete request
        cleanup_interval=30,  # Seconds between cleaning up closed connections
        url_scheme='http'  # Scheme to use in environ (can be http or https)
    )