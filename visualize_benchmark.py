#!/usr/bin/env python3
"""
Simple visualization script for benchmark results

Usage:
    python visualize_benchmark.py benchmark_results.json
"""

import argparse
import json
import sys

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend by default
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError as e:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib or numpy not installed.")
    print(f"Error: {e}")
    print("\nTo install, run:")
    print("  python3 -m pip install matplotlib numpy")
    print("  # or")
    print("  pip install -r benchmark_requirements.txt")
    print("\nShowing text-based summary instead.")


def print_text_summary(data):
    """Print a text-based summary of results"""
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    print(f"\nBase URL: {data['base_url']}")
    print(f"Test Image: {data['test_image']}")
    print(f"Benchmark Timestamp: {data['benchmark_timestamp']}")
    
    print("\n" + "-"*80)
    print(f"{'Configuration':<40} {'RPS':<10} {'Mean RT':<12} {'P95 RT':<12} {'Error %':<10}")
    print("-"*80)
    
    for result in data['results']:
        config = result['config_name']
        metrics = result['metrics']
        print(f"{config:<40} {metrics['requests_per_second']:<10.2f} "
              f"{metrics['mean_response_time_ms']:<12.2f} "
              f"{metrics['p95_response_time_ms']:<12.2f} "
              f"{metrics['error_rate']*100:<10.2f}")
    
    print("\n" + "="*80)


def create_visualizations(data, output_file=None):
    """Create visualization charts"""
    configs = [r['config_name'] for r in data['results']]
    rps = [r['metrics']['requests_per_second'] for r in data['results']]
    mean_rt = [r['metrics']['mean_response_time_ms'] for r in data['results']]
    p95_rt = [r['metrics']['p95_response_time_ms'] for r in data['results']]
    p99_rt = [r['metrics']['p99_response_time_ms'] for r in data['results']]
    error_rates = [r['metrics']['error_rate'] * 100 for r in data['results']]
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Flyimg Performance Benchmark Results', fontsize=16, fontweight='bold')
    
    # Format config names for display
    short_configs = [c.replace('_', ' ').title() for c in configs]
    
    # 1. Requests per Second
    ax1 = axes[0, 0]
    bars1 = ax1.bar(short_configs, rps, color='steelblue', alpha=0.7)
    ax1.set_ylabel('Requests per Second', fontweight='bold')
    ax1.set_title('Throughput (RPS)', fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    plt.setp(ax1.xaxis.get_majorticklabels(), ha='right')
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9)
    
    # 2. Response Times (Mean, P95, P99)
    ax2 = axes[0, 1]
    x = np.arange(len(short_configs))
    width = 0.25
    ax2.bar(x - width, mean_rt, width, label='Mean', color='lightblue', alpha=0.8)
    ax2.bar(x, p95_rt, width, label='P95', color='steelblue', alpha=0.8)
    ax2.bar(x + width, p99_rt, width, label='P99', color='darkblue', alpha=0.8)
    ax2.set_ylabel('Response Time (ms)', fontweight='bold')
    ax2.set_title('Response Time Percentiles', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(short_configs, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    # 3. Error Rates
    ax3 = axes[1, 0]
    bars3 = ax3.bar(short_configs, error_rates, color='coral', alpha=0.7)
    ax3.set_ylabel('Error Rate (%)', fontweight='bold')
    ax3.set_title('Error Rate', fontweight='bold')
    ax3.grid(axis='y', alpha=0.3)
    ax3.tick_params(axis='x', rotation=45)
    plt.setp(ax3.xaxis.get_majorticklabels(), ha='right')
    # Add value labels on bars
    for bar in bars3:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}%',
                ha='center', va='bottom', fontsize=9)
    
    # 4. Comparison: All Configurations Side by Side
    ax4 = axes[1, 1]
    x = np.arange(len(short_configs))
    width = 0.6
    bars4 = ax4.bar(x, rps, width, color='steelblue', alpha=0.7)
    ax4.set_ylabel('Requests per Second', fontweight='bold')
    ax4.set_title('Throughput Comparison', fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(short_configs, rotation=45, ha='right')
    ax4.grid(axis='y', alpha=0.3)
    # Add value labels on bars
    for bar in bars4:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    # Save figure
    if output_file is None:
        output_file = 'benchmark_visualization.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nVisualization saved to: {output_file}")
    plt.close()  # Close the figure to free memory


def main():
    parser = argparse.ArgumentParser(description='Visualize benchmark results')
    parser.add_argument('input_file', help='JSON file with benchmark results')
    parser.add_argument('--output', '-o', help='Output image file (default: benchmark_visualization.png)')
    
    args = parser.parse_args()
    
    # Load data
    try:
        with open(args.input_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file: {e}")
        sys.exit(1)
    
    # Print text summary
    print_text_summary(data)
    
    # Create visualizations if matplotlib is available
    if HAS_MATPLOTLIB:
        create_visualizations(data, args.output)
    else:
        print("\nInstall matplotlib and numpy to generate visualizations:")
        print("  pip install matplotlib numpy")


if __name__ == '__main__':
    main()

