#!/usr/bin/env python3
"""
Comprehensive Test Suite for FinSavvyAI System
Tests cluster, API, and local LLM functionality
"""

import asyncio
import aiohttp
import requests
import json
import time
import subprocess
import sys
from typing import Dict, List, Optional
from datetime import datetime


class FinSavvyAITester:
    """Comprehensive testing suite for FinSavvyAI"""

    def __init__(self):
        self.cluster_url = "http://localhost:8001"
        self.local_llm_url = "http://localhost:8000"
        self.cloudflare_url = "https://finsavvyai-api.broad-dew-49ad.workers.dev"
        self.results = []

    def log_result(
        self, test_name: str, success: bool, message: str, duration: float = 0
    ):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        }
        self.results.append(result)

        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message} ({duration:.2f}s)")

    async def test_cloudflare_api(self):
        """Test Cloudflare Workers API"""
        print("\n🌐 Testing Cloudflare API...")

        start_time = time.time()
        try:
            # Health check
            response = requests.get(f"{self.cloudflare_url}/health", timeout=10)
            if response.status_code == 200:
                health = response.json()
                self.log_result(
                    "Cloudflare Health Check", True, f"Status: {health['status']}"
                )
            else:
                self.log_result(
                    "Cloudflare Health Check", False, f"HTTP {response.status_code}"
                )
                return

            # Models endpoint
            response = requests.get(f"{self.cloudflare_url}/v1/models", timeout=10)
            if response.status_code == 200:
                models = response.json()
                model_count = len(models.get("data", []))
                self.log_result(
                    "Cloudflare Models List", True, f"Found {model_count} models"
                )
            else:
                self.log_result(
                    "Cloudflare Models List", False, f"HTTP {response.status_code}"
                )

            # Chat completion
            chat_data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello! Say hello back in one sentence.",
                    }
                ],
                "max_tokens": 50,
            }

            response = requests.post(
                f"{self.cloudflare_url}/v1/chat/completions", json=chat_data, timeout=30
            )
            if response.status_code == 200:
                completion = response.json()
                content = completion["choices"][0]["message"]["content"]
                self.log_result(
                    "Cloudflare Chat Completion", True, f"Response: {content[:50]}..."
                )
            else:
                self.log_result(
                    "Cloudflare Chat Completion", False, f"HTTP {response.status_code}"
                )

        except Exception as e:
            self.log_result("Cloudflare API", False, f"Connection error: {str(e)}")

    async def test_local_cluster(self):
        """Test local cluster system"""
        print("\n🏠 Testing Local Cluster...")

        start_time = time.time()
        try:
            # Health check
            response = requests.get(f"{self.cluster_url}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                self.log_result(
                    "Cluster Health Check", True, f"Status: {health['status']}"
                )
            else:
                self.log_result("Cluster Health Check", False, "Cluster not running")
                return

            # Cluster status
            response = requests.get(f"{self.cluster_url}/cluster/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                self.log_result(
                    "Cluster Status",
                    True,
                    f"Nodes: {status['online_nodes']}/{status['total_nodes']}",
                )
            else:
                self.log_result("Cluster Status", False, f"HTTP {response.status_code}")

            # List nodes
            response = requests.get(f"{self.cluster_url}/cluster/nodes", timeout=5)
            if response.status_code == 200:
                nodes = response.json()
                node_count = len(nodes.get("nodes", []))
                self.log_result("Cluster Nodes List", True, f"Found {node_count} nodes")
            else:
                self.log_result(
                    "Cluster Nodes List", False, f"HTTP {response.status_code}"
                )

            # Test cluster chat completion
            chat_data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello from cluster test!"}],
                "max_tokens": 50,
            }

            response = requests.post(
                f"{self.cluster_url}/v1/chat/completions", json=chat_data, timeout=15
            )
            if response.status_code == 200:
                completion = response.json()
                content = completion["choices"][0]["message"]["content"]
                node_info = completion.get("cluster_info", {})
                self.log_result(
                    "Cluster Chat Completion",
                    True,
                    f"Response from {node_info.get('node_name', 'unknown')}",
                )
            else:
                self.log_result(
                    "Cluster Chat Completion", False, f"HTTP {response.status_code}"
                )

        except Exception as e:
            self.log_result("Local Cluster", False, f"Connection error: {str(e)}")

    async def test_vllm_service(self):
        """Test vLLM service if running"""
        print("\n🔥 Testing vLLM Service...")

        try:
            # Check if vLLM is running
            response = requests.get(f"{self.local_llm_url}/health", timeout=5)
            if response.status_code == 200:
                self.log_result("vLLM Health Check", True, "vLLM service is running")

                # Test vLLM models endpoint
                response = requests.get(f"{self.local_llm_url}/v1/models", timeout=5)
                if response.status_code == 200:
                    models = response.json()
                    model_count = len(models.get("data", []))
                    self.log_result(
                        "vLLM Models List", True, f"Found {model_count} models"
                    )

                    # Test vLLM chat completion
                    chat_data = {
                        "model": models["data"][0]["id"]
                        if models["data"]
                        else "default",
                        "messages": [
                            {"role": "user", "content": "Hello from vLLM test!"}
                        ],
                        "max_tokens": 50,
                    }

                    response = requests.post(
                        f"{self.local_llm_url}/v1/chat/completions",
                        json=chat_data,
                        timeout=30,
                    )
                    if response.status_code == 200:
                        completion = response.json()
                        content = completion["choices"][0]["message"]["content"]
                        self.log_result(
                            "vLLM Chat Completion", True, f"Response: {content[:50]}..."
                        )
                    else:
                        self.log_result(
                            "vLLM Chat Completion",
                            False,
                            f"HTTP {response.status_code}",
                        )
                else:
                    self.log_result(
                        "vLLM Models List", False, f"HTTP {response.status_code}"
                    )
            else:
                self.log_result("vLLM Health Check", False, "vLLM service not running")

        except Exception as e:
            self.log_result("vLLM Service", False, f"Connection error: {str(e)}")

    def test_file_system(self):
        """Test file system and dependencies"""
        print("\n📁 Testing File System...")

        # Check models directory
        from pathlib import Path

        models_dir = Path.home() / "finsavvyai-models"

        if models_dir.exists():
            model_count = len([d for d in models_dir.iterdir() if d.is_dir()])
            self.log_result("Models Directory", True, f"Found {model_count} models")
        else:
            self.log_result("Models Directory", False, "Models directory not found")

        # Check essential files
        essential_files = [
            "cluster_master.py",
            "cluster_worker.py",
            "vllm_service.py",
            "download_models.py",
        ]

        for file_name in essential_files:
            if Path(file_name).exists():
                self.log_result(f"File: {file_name}", True, "File exists")
            else:
                self.log_result(f"File: {file_name}", False, "File missing")

        # Check Python dependencies
        try:
            import aiohttp

            self.log_result("Dependency: aiohttp", True, "Installed")
        except ImportError:
            self.log_result("Dependency: aiohttp", False, "Not installed")

        try:
            import requests

            self.log_result("Dependency: requests", True, "Installed")
        except ImportError:
            self.log_result("Dependency: requests", False, "Not installed")

    def test_network_connectivity(self):
        """Test network connectivity"""
        print("\n🌍 Testing Network Connectivity...")

        # Test internet connectivity
        try:
            response = requests.get("https://httpbin.org/get", timeout=10)
            if response.status_code == 200:
                self.log_result("Internet Connectivity", True, "Connected to internet")
            else:
                self.log_result(
                    "Internet Connectivity", False, f"HTTP {response.status_code}"
                )
        except Exception as e:
            self.log_result("Internet Connectivity", False, f"No internet: {str(e)}")

        # Test Hugging Face connectivity
        try:
            response = requests.get("https://huggingface.co", timeout=10)
            if response.status_code == 200:
                self.log_result("Hugging Face Access", True, "Can access Hugging Face")
            else:
                self.log_result(
                    "Hugging Face Access", False, f"HTTP {response.status_code}"
                )
        except Exception as e:
            self.log_result("Hugging Face Access", False, f"No access: {str(e)}")

    def test_system_resources(self):
        """Test system resources"""
        print("\n💻 Testing System Resources...")

        try:
            import psutil

            # Memory
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            total_gb = memory.total / (1024**3)
            self.log_result(
                "System Memory",
                True,
                f"{available_gb:.1f}GB available / {total_gb:.1f}GB total",
            )

            # Disk space
            disk = psutil.disk_usage("/")
            free_gb = disk.free / (1024**3)
            total_gb = disk.total / (1024**3)
            self.log_result(
                "Disk Space", True, f"{free_gb:.1f}GB free / {total_gb:.1f}GB total"
            )

            # CPU cores
            cpu_count = psutil.cpu_count()
            self.log_result("CPU Cores", True, f"{cpu_count} cores available")

        except ImportError:
            self.log_result("System Resources", False, "psutil not installed")
        except Exception as e:
            self.log_result("System Resources", False, f"Error: {str(e)}")

    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 FinSavvyAI Comprehensive Test Suite")
        print("=" * 50)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        total_start = time.time()

        # Run all test categories
        self.test_file_system()
        self.test_network_connectivity()
        self.test_system_resources()
        await self.test_cloudflare_api()
        await self.test_local_cluster()
        await self.test_vllm_service()

        total_duration = time.time() - total_start

        # Generate summary
        self.generate_summary(total_duration)

    def generate_summary(self, total_duration: float):
        """Generate test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)

        passed = len([r for r in self.results if r["success"]])
        failed = len([r for r in self.results if not r["success"]])
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed / total * 100):.1f}%")
        print(f"⏱️ Total Duration: {total_duration:.2f}s")

        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['message']}")

        print(f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Save results to file
        results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w") as f:
            json.dump(
                {
                    "summary": {
                        "total": total,
                        "passed": passed,
                        "failed": failed,
                        "success_rate": passed / total * 100,
                        "duration": total_duration,
                    },
                    "results": self.results,
                },
                f,
                indent=2,
            )

        print(f"📄 Detailed results saved to: {results_file}")


async def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        # Run specific test category
        test_type = sys.argv[1].lower()
        tester = FinSavvyAITester()

        if test_type == "cloudflare":
            await tester.test_cloudflare_api()
        elif test_type == "cluster":
            await tester.test_local_cluster()
        elif test_type == "vllm":
            await tester.test_vllm_service()
        elif test_type == "system":
            tester.test_file_system()
            tester.test_network_connectivity()
            tester.test_system_resources()
        else:
            print(f"Unknown test type: {test_type}")
            print("Available: cloudflare, cluster, vllm, system, all")
    else:
        # Run all tests
        tester = FinSavvyAITester()
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

