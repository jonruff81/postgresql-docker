#!/usr/bin/env python3
"""
Monitor API calls to a specific endpoint and track response times.
"""

import requests
import time
import argparse
from datetime import datetime
import sys
import statistics

def monitor_endpoint(endpoint, interval=5, duration=None, verbose=False):
    """
    Monitor an API endpoint by making periodic requests and tracking response times.
    
    Args:
        endpoint (str): The API endpoint to monitor (without http://localhost:5000)
        interval (int): Seconds between requests
        duration (int, optional): How long to run the monitor (in seconds)
        verbose (bool): Whether to print detailed information
    """
    url = f"http://localhost:5000/api/{endpoint}"
    print(f"Monitoring endpoint: {url}")
    print(f"Making requests every {interval} seconds")
    if duration:
        print(f"Will run for {duration} seconds")
    print()
    
    start_time = time.time()
    request_count = 0
    response_times = []
    error_count = 0
    
    try:
        while True:
            # Check if we've reached the duration
            if duration and (time.time() - start_time) >= duration:
                break
                
            # Make the request with cache-busting parameter
            request_time = datetime.now()
            request_url = f"{url}?_t={int(time.time())}"
            
            try:
                req_start = time.time()
                response = requests.get(request_url, timeout=30)
                elapsed = time.time() - req_start
                response_times.append(elapsed)
                
                # Format timestamp
                timestamp = request_time.strftime("%H:%M:%S")
                
                if response.status_code == 200:
                    # Process the response
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            record_count = len(data)
                            if verbose:
                                print(f"[{timestamp}] ✓ Success ({elapsed:.3f}s) - {record_count} records")
                            else:
                                sys.stdout.write(f"\r[{timestamp}] Request {request_count+1}: {elapsed:.3f}s - {record_count} records")
                                sys.stdout.flush()
                        else:
                            if verbose:
                                print(f"[{timestamp}] ✓ Success ({elapsed:.3f}s) - Non-list response")
                            else:
                                sys.stdout.write(f"\r[{timestamp}] Request {request_count+1}: {elapsed:.3f}s - Non-list response")
                                sys.stdout.flush()
                    except Exception as e:
                        print(f"[{timestamp}] ⚠️ Error parsing response: {str(e)}")
                        error_count += 1
                else:
                    print(f"[{timestamp}] ✗ HTTP Error {response.status_code}: {response.text[:100]}")
                    error_count += 1
                    
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Request failed: {str(e)}")
                error_count += 1
            
            request_count += 1
            
            # Sleep until next interval
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    
    # Print summary statistics
    print("\n\nSummary:")
    print(f"  Total requests: {request_count}")
    print(f"  Errors: {error_count}")
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        print(f"  Average response time: {avg_time:.3f}s")
        print(f"  Min response time: {min(response_times):.3f}s")
        print(f"  Max response time: {max(response_times):.3f}s")
        
        if len(response_times) > 1:
            print(f"  Response time std dev: {statistics.stdev(response_times):.3f}s")
    
    print(f"  Total monitoring time: {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor API endpoint performance")
    parser.add_argument("--endpoint", default="cost-codes-with-groups", 
                        help="API endpoint to monitor (without the /api/ prefix)")
    parser.add_argument("--interval", type=int, default=5,
                        help="Seconds between requests (default: 5)")
    parser.add_argument("--duration", type=int, default=None,
                        help="How long to run the monitor in seconds (default: indefinitely)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print detailed information for each request")
    
    args = parser.parse_args()
    
    monitor_endpoint(args.endpoint, args.interval, args.duration, args.verbose)
