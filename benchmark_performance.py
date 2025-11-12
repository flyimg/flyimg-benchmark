#!/usr/bin/env python3
"""
Performance Benchmarking Script for Flyimg

This script runs load tests against a Flyimg instance and collects performance metrics.
You should manually configure the parameters.yml file with your desired settings
(cache enabled/disabled, rate limiting enabled/disabled) before running the benchmark.

Usage:
    python benchmark_performance.py --config-name NAME [--url URL] [--container-name NAME] 
                                   [--port PORT] [--test-image PATH] [--output OUTPUT]
                                   [--num-requests N] [--concurrency N]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class LoadTester:
    """Simple load tester using Python requests"""
    
    def __init__(self, url: str, num_requests: int = 1000, concurrency: int = 10):
        self.url = url
        self.num_requests = num_requests
        self.concurrency = concurrency
        self.results = []
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def make_request(self) -> Dict:
        """Make a single HTTP request and return timing data"""
        start_time = time.time()
        try:
            response = self.session.get(self.url, timeout=10)
            elapsed = time.time() - start_time
            
            return {
                'status_code': response.status_code,
                'response_time': elapsed * 1000,  # Convert to milliseconds
                'content_length': len(response.content),
                'success': 200 <= response.status_code < 300,
                'error': None
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                'status_code': 0,
                'response_time': elapsed * 1000,
                'content_length': 0,
                'success': False,
                'error': str(e)
            }
    
    def run(self) -> Dict:
        """Run the load test"""
        print(f"Running load test: {self.num_requests} requests with {self.concurrency} concurrent connections...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = [executor.submit(self.make_request) for _ in range(self.num_requests)]
            results = []
            
            completed = 0
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1
                if completed % 100 == 0:
                    print(f"  Completed: {completed}/{self.num_requests}")
        
        total_time = time.time() - start_time
        
        return self._calculate_metrics(results, total_time)
    
    def _calculate_metrics(self, results: List[Dict], total_time: float) -> Dict:
        """Calculate performance metrics from results"""
        response_times = [r['response_time'] for r in results]
        response_times.sort()
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        total_requests = len(results)
        successful_requests = len(successful)
        failed_requests = len(failed)
        
        if not response_times:
            return {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'requests_per_second': 0,
                'total_time': total_time,
                'mean_response_time': 0,
                'min_response_time': 0,
                'max_response_time': 0,
                'p50_response_time': 0,
                'p95_response_time': 0,
                'p99_response_time': 0,
                'error_rate': 1.0
            }
        
        mean_rt = sum(response_times) / len(response_times)
        min_rt = min(response_times)
        max_rt = max(response_times)
        
        def percentile(data, p):
            if not data:
                return 0
            k = (len(data) - 1) * p
            f = int(k)
            c = k - f
            if f + 1 < len(data):
                return data[f] + c * (data[f + 1] - data[f])
            return data[f]
        
        p50 = percentile(response_times, 0.50)
        p95 = percentile(response_times, 0.95)
        p99 = percentile(response_times, 0.99)
        
        rps = successful_requests / total_time if total_time > 0 else 0
        error_rate = failed_requests / total_requests if total_requests > 0 else 0
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'requests_per_second': round(rps, 2),
            'total_time': round(total_time, 2),
            'mean_response_time_ms': round(mean_rt, 2),
            'min_response_time_ms': round(min_rt, 2),
            'max_response_time_ms': round(max_rt, 2),
            'p50_response_time_ms': round(p50, 2),
            'p95_response_time_ms': round(p95, 2),
            'p99_response_time_ms': round(p99, 2),
            'error_rate': round(error_rate, 4),
            'status_codes': self._count_status_codes(results)
        }
    
    def _count_status_codes(self, results: List[Dict]) -> Dict:
        """Count status codes"""
        counts = {}
        for r in results:
            code = r['status_code']
            counts[code] = counts.get(code, 0) + 1
        return counts


class BenchmarkRunner:
    """Main benchmark runner"""
    
    def __init__(self, base_url: str, test_image: str, output_file: str, container_name: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.test_image = test_image
        self.output_file = output_file
        self.container_name = container_name
        self.results = []
    
    def run_benchmark(self, config_name: str, num_requests: int = 1000, concurrency: int = 10) -> Dict:
        """Run a single benchmark test"""
        print(f"\n{'='*80}")
        print(f"Running benchmark: {config_name}")
        print(f"{'='*80}")
        
        # Construct test URL
        test_url = f"{self.base_url}/upload/w_500,h_500,rf_1/{self.test_image}"
        
        # Run load test
        tester = LoadTester(test_url, num_requests, concurrency)
        metrics = tester.run()
        
        result = {
            'config_name': config_name,
            'timestamp': datetime.now().isoformat(),
            'test_parameters': {
                'url': test_url,
                'num_requests': num_requests,
                'concurrency': concurrency
            },
            'metrics': metrics
        }
        
        # Print summary
        print(f"\nResults for {config_name}:")
        print(f"  Requests per second: {metrics['requests_per_second']:.2f}")
        print(f"  Mean response time: {metrics['mean_response_time_ms']:.2f} ms")
        print(f"  P95 response time: {metrics['p95_response_time_ms']:.2f} ms")
        print(f"  P99 response time: {metrics['p99_response_time_ms']:.2f} ms")
        print(f"  Error rate: {metrics['error_rate']*100:.2f}%")
        print(f"  Successful requests: {metrics['successful_requests']}/{metrics['total_requests']}")
        
        return result
    
    def save_results(self):
        """Save results to JSON file, appending if file exists"""
        # Load existing results if file exists
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r') as f:
                    existing_data = json.load(f)
                # Append new results to existing results
                existing_data['results'].extend(self.results)
                output_data = existing_data
            except (json.JSONDecodeError, KeyError):
                # If file is corrupted or has wrong format, create new
                output_data = {
                    'benchmark_timestamp': datetime.now().isoformat(),
                    'base_url': self.base_url,
                    'test_image': self.test_image,
                    'results': self.results
                }
        else:
            # Create new file
            output_data = {
                'benchmark_timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'test_image': self.test_image,
                'results': self.results
            }
        
        with open(self.output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n{'='*80}")
        print(f"Results saved to: {self.output_file}")
        print(f"{'='*80}")


def check_docker_container(container_name: str) -> bool:
    """Check if Docker container is running"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            check=True
        )
        return container_name in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_container_url(container_name: str, port: int = 80) -> Optional[str]:
    """Get URL for Docker container"""
    if not check_docker_container(container_name):
        print(f"Warning: Container '{container_name}' not found. Trying to use localhost:{port}")
        return f"http://localhost:{port}"
    
    # Try to get container's IP or use localhost with port mapping
    try:
        result = subprocess.run(
            ['docker', 'port', container_name],
            capture_output=True,
            text=True,
            check=True
        )
        # Parse port mapping (e.g., "80/tcp -> 0.0.0.0:8099")
        for line in result.stdout.strip().split('\n'):
            if '80/tcp' in line:
                parts = line.split('->')
                if len(parts) > 1:
                    host_port = parts[1].strip().split(':')[1]
                    return f"http://localhost:{host_port}"
    except subprocess.CalledProcessError:
        pass
    
    return f"http://localhost:{port}"


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark Flyimg performance. Configure parameters.yml manually before running.'
    )
    parser.add_argument(
        '--url',
        type=str,
        help='Base URL of Flyimg instance (e.g., http://localhost:8099)'
    )
    parser.add_argument(
        '--container-name',
        type=str,
        help='Docker container name (alternative to --url)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=80,
        help='Port number (default: 80, used with --container-name)'
    )
    parser.add_argument(
        '--test-image',
        type=str,
        default='Rovinj-Croatia.jpg',
        help='Test image path relative to web/ directory (default: Rovinj-Croatia.jpg)'
    )
    parser.add_argument(
        '--num-requests',
        type=int,
        default=1000,
        help='Number of requests per test (default: 1000)'
    )
    parser.add_argument(
        '--concurrency',
        type=int,
        default=10,
        help='Number of concurrent connections (default: 10)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='benchmark_results.json',
        help='Output JSON file (default: benchmark_results.json)'
    )
    parser.add_argument(
        '--config-name',
        type=str,
        required=True,
        help='Configuration name/identifier for this benchmark run (e.g., "cache_enabled_rl_disabled")'
    )
    
    args = parser.parse_args()
    
    # Determine base URL
    if args.url:
        base_url = args.url.rstrip('/')
    elif args.container_name:
        base_url = get_container_url(args.container_name, args.port)
        if not base_url:
            print(f"Error: Could not determine URL for container '{args.container_name}'")
            sys.exit(1)
    else:
        print("Error: Either --url or --container-name must be provided")
        parser.print_help()
        sys.exit(1)
    
    # Check if test image exists (for local testing)
    test_image_path = f"web/{args.test_image}"
    if not os.path.exists(test_image_path) and not args.url:
        print(f"Warning: Test image '{test_image_path}' not found locally")
        print("Make sure the image exists in the web/ directory or use --url for remote testing")
    
    # Initialize benchmark runner
    container_name = args.container_name if args.container_name else None
    runner = BenchmarkRunner(base_url, args.test_image, args.output, container_name)
    
    # Run single benchmark with the specified config name
    print(f"\nNote: Make sure you have manually configured the parameters.yml")
    print(f"      with the desired cache and rate limiting settings before running this benchmark.")
    
    result = runner.run_benchmark(
        args.config_name,
        args.num_requests,
        args.concurrency
    )
    runner.results.append(result)
    
    # Save results
    runner.save_results()
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    metrics = result['metrics']
    print(f"Configuration: {args.config_name}")
    print(f"  Requests per second: {metrics['requests_per_second']:.2f}")
    print(f"  Mean response time: {metrics['mean_response_time_ms']:.2f} ms")
    print(f"  P95 response time: {metrics['p95_response_time_ms']:.2f} ms")
    print(f"  P99 response time: {metrics['p99_response_time_ms']:.2f} ms")
    print(f"  Error rate: {metrics['error_rate']*100:.2f}%")
    print(f"  Successful requests: {metrics['successful_requests']}/{metrics['total_requests']}")


if __name__ == '__main__':
    main()

