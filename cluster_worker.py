#!/usr/bin/env python3
"""
FinSavvyAI Worker Node - For Other Laptops
Run this on each laptop you want to add to the cluster
"""

import asyncio
import aiohttp
import json
import time
import socket
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class WorkerConfig:
    """Worker configuration"""

    node_id: str
    name: str
    host: str
    port: int
    models: List[str]
    master_host: str
    master_port: int = 8000


class ClusterWorker:
    """Worker node that connects to the cluster master"""

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.master_url = f"http://{config.master_host}:{config.master_port}"
        self.heartbeat_task = None

    async def start(self):
        """Start the worker node"""
        print(f"🚀 Starting FinSavvyAI Worker: {self.config.name}")
        print(f"   Node ID: {self.config.node_id}")
        print(f"   Host: {self.config.host}:{self.config.port}")
        print(f"   Models: {', '.join(self.config.models)}")
        print(f"   Master: {self.master_url}")
        print()

        # Register with master
        await self.register_with_master()

        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())

        # Start local LLM server
        await self.start_llm_server()

        print(f"✅ Worker node ready and connected to cluster!")

    async def start_llm_server(self):
        """Start local LLM server with OpenAI-compatible endpoints"""
        from aiohttp import web

        app = web.Application()

        # CORS middleware
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization"
            )
            return response

        app.middlewares.append(cors_middleware)

        # Routes
        app.router.add_post("/v1/chat/completions", self.handle_completion)
        app.router.add_get("/v1/models", self.handle_models)
        app.router.add_get("/health", self.handle_health)
        app.router.add_options("/{path:.*}", self.handle_options)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.config.host, self.config.port)
        await site.start()

        print(f"🔥 LLM server running on http://{self.config.host}:{self.config.port}")

    async def handle_options(self, request):
        """Handle CORS preflight requests"""
        return web.Response(status=200)

    async def register_with_master(self):
        """Register this node with the cluster master"""
        print(f"📡 Registering with cluster master at {self.master_url}...")

        data = {
            "id": self.config.node_id,
            "name": self.config.name,
            "host": self.config.host,
            "port": self.config.port,
            "models": self.config.models,
            "capabilities": {
                "gpu": self.check_gpu_availability(),
                "memory": self.get_memory_info(),
                "cpu_cores": self.get_cpu_info(),
                "platform": sys.platform,
            },
            "max_load": 10,
        }

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.master_url}/cluster/join", json=data
                ) as response:
                    result = await response.json()
                    if result.get("status") == "registered":
                        print(f"✅ Successfully registered with cluster master!")
                        print(f"   Assigned node ID: {result.get('node_id')}")
                        return True
                    else:
                        print(f"❌ Failed to register: {result}")
                        return False
        except Exception as e:
            print(f"❌ Cannot connect to cluster master: {e}")
            print(f"   Make sure the cluster master is running at {self.master_url}")
            return False

    async def heartbeat_loop(self):
        """Send periodic heartbeat to master"""
        while True:
            try:
                data = {
                    "id": self.config.node_id,
                    "status": "online",
                    "load": self.get_current_load(),
                }

                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        f"{self.master_url}/cluster/heartbeat", json=data
                    ) as response:
                        if response.status == 200:
                            print(f"💓 Heartbeat sent")
                        else:
                            print(f"⚠️  Heartbeat failed: {response.status}")

            except Exception as e:
                print(f"❌ Heartbeat error: {e}")

            await asyncio.sleep(30)  # Heartbeat every 30 seconds

    async def handle_completion(self, request):
        """Handle chat completion requests"""
        try:
            data = await request.json()

            print(
                f"📨 Processing completion request for model: {data.get('model', 'unknown')}"
            )

            # Mock response - replace with actual LLM call
            response = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": data.get("model", "gpt-3.5-turbo"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"Hello from {self.config.name}! I'm running on {self.config.host} and processed your request locally. This response is coming from your home cluster worker node.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 25,
                    "total_tokens": 35,
                },
                "worker_info": {
                    "node_id": self.config.node_id,
                    "node_name": self.config.name,
                    "host": self.config.host,
                    "platform": sys.platform,
                },
            }

            print(f"✅ Request processed successfully")
            return web.json_response(response)

        except Exception as e:
            print(f"❌ Error processing completion: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_models(self, request):
        """Return available models"""
        models = []
        for model in self.config.models:
            models.append(
                {
                    "id": model,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": f"worker-{self.config.node_id}",
                }
            )

        return web.json_response({"object": "list", "data": models})

    async def handle_health(self, request):
        """Health check endpoint"""
        return web.json_response(
            {
                "status": "healthy",
                "node_id": self.config.node_id,
                "node_name": self.config.name,
                "host": self.config.host,
                "models": self.config.models,
                "capabilities": {
                    "gpu": self.check_gpu_availability(),
                    "memory": self.get_memory_info(),
                    "cpu_cores": self.get_cpu_info(),
                },
            }
        )

    def check_gpu_availability(self):
        """Check if GPU is available"""
        try:
            # Check for CUDA
            import torch

            if torch.cuda.is_available():
                return {"cuda": True, "devices": torch.cuda.device_count()}
        except ImportError:
            pass

        try:
            # Check for Apple Silicon GPU
            import subprocess

            result = subprocess.run(
                ["sysctl", "hw.optional.gpu"], capture_output=True, text=True
            )
            if result.returncode == 0 and "hw.optional.gpu: 1" in result.stdout:
                return {"apple_silicon": True}
        except:
            pass

        return {"gpu": False}

    def get_memory_info(self):
        """Get memory information"""
        try:
            import psutil

            return {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
            }
        except ImportError:
            return {"total": 0, "available": 0, "used": 0}

    def get_cpu_info(self):
        """Get CPU information"""
        try:
            import psutil

            return {
                "cores": psutil.cpu_count(),
                "usage_percent": psutil.cpu_percent(interval=1),
            }
        except ImportError:
            return {"cores": 0, "usage_percent": 0}

    def get_current_load(self):
        """Get current load for this worker"""
        return 2  # Mock load


def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Connect to an external host to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def interactive_setup():
    """Interactive setup for worker configuration"""
    print("🤖 FinSavvyAI Worker Node Setup")
    print("=" * 40)
    print()

    # Get local IP
    local_ip = get_local_ip()
    print(f"📍 Detected your IP: {local_ip}")

    # Configuration
    print("\n📝 Worker Configuration:")
    print("-" * 20)

    node_id = (
        input(f"Node ID (e.g., laptop-mbp): ").strip()
        or f"laptop-{local_ip.split('.')[-1]}"
    )
    name = input(f"Node Name (e.g., MacBook Pro): ").strip() or f"Worker-{node_id}"

    # Choose models
    print("\n🧠 Available models to host:")
    print("1. gpt-3.5-turbo")
    print("2. gpt-4")
    print("3. claude-3-sonnet")
    print("4. llama-2-7b")
    print("5. custom (comma-separated list)")

    model_choice = input("Choose models (e.g., 1,3,5): ").strip()

    model_map = {
        "1": ["gpt-3.5-turbo"],
        "2": ["gpt-4"],
        "3": ["claude-3-sonnet"],
        "4": ["llama-2-7b"],
        "5": [],
    }

    models = []
    for choice in model_choice.split(","):
        choice = choice.strip()
        if choice in model_map:
            models.extend(model_map[choice])
        elif choice == "5":
            custom_models = input("Enter custom models (comma-separated): ").strip()
            models.extend([m.strip() for m in custom_models.split(",")])

    if not models:
        models = ["gpt-3.5-turbo"]  # Default

    port = int(input(f"Port (default 8001): ").strip() or "8001")
    master_host = input(f"Master host IP (default 10.0.0.10): ").strip() or "10.0.0.10"
    master_port = int(input(f"Master port (default 8000): ").strip() or "8000")

    return WorkerConfig(
        node_id=node_id,
        name=name,
        host=local_ip,
        port=port,
        models=models,
        master_host=master_host,
        master_port=master_port,
    )


async def main():
    """Main setup function"""
    try:
        # Interactive setup
        config = interactive_setup()

        print("\n🔧 Starting worker with configuration:")
        print(f"   Node ID: {config.node_id}")
        print(f"   Name: {config.name}")
        print(f"   Host: {config.host}:{config.port}")
        print(f"   Models: {', '.join(config.models)}")
        print(f"   Master: {config.master_host}:{config.master_port}")
        print()

        # Create and start worker
        worker = ClusterWorker(config)
        await worker.start()

        print(f"\n✅ Worker node is running!")
        print(f"💡 Press Ctrl+C to stop the worker")

        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            print(f"\n🛑 Stopping worker node...")
            if worker.heartbeat_task:
                worker.heartbeat_task.cancel()
            print(f"✅ Worker stopped successfully")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print(
            f"💡 Make sure the cluster master is running at {config.master_host}:{config.master_port}"
        )


if __name__ == "__main__":
    asyncio.run(main())
