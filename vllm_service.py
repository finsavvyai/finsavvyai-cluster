#!/usr/bin/env python3
"""
vLLM Integration Service for FinSavvyAI
Handles local model serving with vLLM backend
"""

import asyncio
import aiohttp
import json
import time
import subprocess
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ModelConfig:
    """Configuration for a model"""

    name: str
    model_path: str
    port: int
    gpu: bool = True
    max_tokens: int = 4096
    context_length: int = 8192


class VLLMService:
    """Manages vLLM model serving"""

    def __init__(self):
        self.models: Dict[str, ModelConfig] = {}
        self.running_models: Dict[str, subprocess.Popen] = {}
        self.session = None

    async def start(self):
        """Start the vLLM service"""
        self.session = aiohttp.ClientSession()
        print("🚀 FinSavvyAI vLLM Service Started")

    async def detect_gpu(self):
        """Detect GPU availability (Apple Silicon, CUDA, etc.)"""
        try:
            # Check for Apple Silicon GPU
            result = subprocess.run(
                ["sysctl", "hw.optional.gpu"], capture_output=True, text=True
            )
            if result.returncode == 0:
                print("🍎 Apple Silicon GPU detected")
                return "mps"

            # Check for NVIDIA GPU
            try:
                result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
                if result.returncode == 0:
                    print("🟢 NVIDIA CUDA GPU detected")
                    return "cuda"
            except FileNotFoundError:
                pass

            print("💻 No GPU detected, using CPU")
            return "cpu"

        except Exception as e:
            print(f"⚠️ GPU detection failed: {e}")
            return "cpu"

    async def download_model(self, model_name: str, model_size="small"):
        """Download a model from Hugging Face"""
        print(f"📥 Downloading model: {model_name}")

        # Model configurations
        models = {
            "zephyr-7b-beta": {
                "repo": "HuggingFaceH4/zephyr-7b-beta",
                "files": ["*.json", "*.py", "*.safetensors"],
            },
            "mistral-7b": {
                "repo": "mistralai/Mistral-7B-Instruct-v0.2",
                "files": ["*.json", "*.py", "*.safetensors"],
            },
        }

        if model_name not in models:
            print(f"❌ Unknown model: {model_name}")
            return False

        model_config = models[model_name]
        models_dir = os.path.expanduser("~/finsavvyai-models")
        model_dir = os.path.join(models_dir, model_name)

        os.makedirs(model_dir, exist_ok=True)

        # Download using git clone (faster for large models)
        try:
            cmd = [
                "git",
                "clone",
                f"https://huggingface.co/{model_config['repo']}",
                model_dir,
            ]

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                print(f"✅ Model {model_name} downloaded successfully")
                return True
            else:
                print(f"❌ Failed to download {model_name}: {stderr.decode()}")
                return False

        except Exception as e:
            print(f"❌ Download error: {e}")
            return False

    async def start_model_server(
        self, model_name: str, model_path: str, port: int = 8000
    ):
        """Start vLLM server for a specific model"""
        if model_name in self.running_models:
            print(f"⚠️ Model {model_name} already running")
            return True

        print(f"🔥 Starting vLLM server for {model_name} on port {port}")

        # Detect GPU type
        gpu_type = await self.detect_gpu()

        # Build vLLM command
        cmd = [
            "python3",
            "-m",
            "vllm.entrypoints.api_server",
            "--model",
            model_path,
            "--port",
            str(port),
            "--host",
            "0.0.0.0",
            "--max-num-seqs",
            "8",
            "--max-num-batched-tokens",
            "4096",
        ]

        # Add GPU-specific arguments
        if gpu_type == "mps":
            cmd.extend(["--device", "mps"])
        elif gpu_type == "cuda":
            cmd.extend(["--device", "cuda"])
        else:
            cmd.extend(["--device", "cpu"])

        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Wait for server to start
            await asyncio.sleep(10)

            if process.poll() is None:
                print(f"✅ Model {model_name} server started successfully")
                self.running_models[model_name] = process
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ Failed to start {model_name}: {stderr}")
                return False

        except Exception as e:
            print(f"❌ Server error: {e}")
            return False

    async def stop_model_server(self, model_name: str):
        """Stop a running model server"""
        if model_name not in self.running_models:
            print(f"⚠️ Model {model_name} not running")
            return True

        process = self.running_models[model_name]
        print(f"🛑 Stopping model {model_name}")

        try:
            process.terminate()
            await asyncio.sleep(5)

            if process.poll() is None:
                process.kill()

            del self.running_models[model_name]
            print(f"✅ Model {model_name} stopped")
            return True

        except Exception as e:
            print(f"❌ Error stopping {model_name}: {e}")
            return False

    async def check_model_health(self, port: int = 8000):
        """Check if model server is healthy"""
        try:
            async with self.session.get(f"http://localhost:{port}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("status") == "healthy"
        except:
            pass
        return False

    async def generate_completion(
        self, prompt: str, model_name: str = "zephyr-7b-beta", port: int = 8000
    ):
        """Generate completion using local model"""
        url = f"http://localhost:{port}/v1/chat/completions"

        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.7,
        }

        try:
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "content": result["choices"][0]["message"]["content"],
                        "usage": result.get("usage", {}),
                        "model": model_name,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {await response.text()}",
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_available_models(self):
        """List available models in the models directory"""
        models_dir = os.path.expanduser("~/finsavvyai-models")
        if not os.path.exists(models_dir):
            return []

        models = []
        for item in os.listdir(models_dir):
            if os.path.isdir(os.path.join(models_dir, item)):
                models.append(item)

        return models

    async def get_running_models(self):
        """Get list of currently running models"""
        return list(self.running_models.keys())

    async def shutdown(self):
        """Shutdown the vLLM service"""
        print("🛑 Shutting down vLLM Service")

        # Stop all running models
        for model_name in list(self.running_models.keys()):
            await self.stop_model_server(model_name)

        if self.session:
            await self.session.close()


# Example usage
async def main():
    service = VLLMService()
    await service.start()

    # Detect GPU
    gpu_type = await service.detect_gpu()
    print(f"🔧 Using GPU: {gpu_type}")

    # Download model if needed
    models = await service.list_available_models()
    if not models:
        print("📥 No models found, downloading zephyr-7b-beta...")
        await service.download_model("zephyr-7b-beta")

    # Start model server
    await service.start_model_server(
        "zephyr-7b-beta", "~/finsavvyai-models/zephyr-7b-beta"
    )

    # Test completion
    result = await service.generate_completion(
        "Hello! Write a Python hello world function."
    )
    if result["success"]:
        print(f"🤖 Response: {result['content']}")
    else:
        print(f"❌ Error: {result['error']}")

    # Cleanup
    await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
