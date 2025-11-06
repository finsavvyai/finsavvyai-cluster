#!/usr/bin/env python3
"""
FinSavvyAI API Usage Example
"""

import requests

CLOUDFLARE_API = "https://finsavvyai-api.broad-dew-49ad.workers.dev"
LOCAL_CLUSTER = "http://localhost:8001"

def main():
    print("🤖 FinSavvyAI API Demo")
    print("=" * 40)
    print(f"Cloudflare API: {CLOUDFLARE_API}")
    print(f"Local Cluster: {LOCAL_CLUSTER}")
    print("
Start local cluster with: python3 cluster_master.py")

if __name__ == "__main__":
    main()
