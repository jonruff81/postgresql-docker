#!/usr/bin/env python3
"""
Test script to check API endpoint response times and reliability
"""

import requests
import time
import sys
import json
from datetime import datetime

def test_endpoint(url, num_requests=5, delay=0.5):
    """Test an API endpoint for response time and consistency"""
    
    print(f"Testing endpoint: {url}")
    print(f"Making {num_requests} requests with {delay}s delay between them")
    print()
    
    results = {
        'success': 0,
        'errors': 0,
        'exceptions': 0,
        'response_times': [],
        'status_codes': [],
        'error_messages': []
    }
    
    for i in range(num_requests):
        try:
            # Add cache busting parameter
            request_url = f"{url}?_t={int(time.time())}"
            start_time = time.time()
            current_time = datetime.now().strftime("%H:%M:%S.%f")
            
            print(f"Request {i+1}/{num_requests} at {current_time}")
            
            response = requests.get(request_url, timeout=30)
            elapsed = time.time() - start_time
            results['response_times'].append(elapsed)
            results['status_codes'].append(response.status_code)
            
            if response.status_code == 200:
                results['success'] += 1
                # Check if response is valid JSON and count records
                try:
                    data = response.json()
                    record_count = len(data) if isinstance(data, list) else 0
                    print(f"  ✓ Success ({elapsed:.3f}s) - Received {record_count} records")
                except:
                    print(f"  ✓ Success ({elapsed:.3f}s) - Response not valid JSON")
            else:
                results['errors'] += 1
                error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                results['error_messages'].append(error_msg)
                print(f"  ✗ Error ({elapsed:.3f}s) - {error_msg}")
                
        except Exception as e:
            results['exceptions'] += 1
            print(f"  ✗ Exception: {str(e)}")
            results['error_messages'].append(str(e))
        
        # Wait between requests
        if i < num_requests - 1:
            time.sleep(delay)
    
    # Print summary
    print("\nSummary:")
    print(f"  Total requests: {num_requests}")
    print(f"  Successful: {results['success']}")
    print(f"  Errors: {results['errors']}")
    print(f"  Exceptions: {results['exceptions']}")
    
    if results['response_times']:
        avg_time = sum(results['response_times']) / len(results['response_times'])
        print(f"  Average response time: {avg_time:.3f}s")
    
    return results

if __name__ == "__main__":
    # Default endpoint
    endpoint = "http://localhost:5000/api/cost-codes-with-groups"
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        endpoint = sys.argv[1]
    
    test_endpoint(endpoint)
