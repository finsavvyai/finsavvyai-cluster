#!/usr/bin/env python3
"""
Model Download Manager for FinSavvyAI
Handles downloading and managing LLM models from Hugging Face
"""

import os
import sys
import subprocess
import requests
import json
from pathlib import Path
from typing import Dict, List, Optional
import asyncio
import time


class ModelDownloadManager:
    """Manages downloading and organizing LLM models"""

    def __init__(self, models_dir: str = None):
        if models_dir is None:
            self.models_dir = Path.home() / "finsavvyai-models"
        else:
            self.models_dir = Path(models_dir)

        self.models_dir.mkdir(exist_ok=True)
        self.config_file = self.models_dir / "models.json"
        self.load_config()

        # Available models configuration
        self.available_models = {
            "zephyr-7b-beta": {
                "repo_id": "HuggingFaceH4/zephyr-7b-beta",
                "size": "4.8GB",
                "type": "chat",
                "description": "Fast and capable chat model",
                "recommended": True,
            },
            "mistral-7b-instruct": {
                "repo_id": "mistralai/Mistral-7B-Instruct-v0.2",
                "size": "4.1GB",
                "type": "chat",
                "description": "Instruction-tuned model for chat",
                "recommended": True,
            },
            "llama-2-7b-chat": {
                "repo_id": "meta-llama/Llama-2-7b-chat-hf",
                "size": "6.7GB",
                "type": "chat",
                "description": "Meta's Llama 2 chat model",
                "recommended": False,
                "requires_auth": True,
            },
            "phi-2": {
                "repo_id": "microsoft/phi-2",
                "size": "2.8GB",
                "type": "chat",
                "description": "Small but capable model from Microsoft",
                "recommended": True,
            },
        }

    def load_config(self):
        """Load models configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self.downloaded_models = json.load(f)
            except:
                self.downloaded_models = {}
        else:
            self.downloaded_models = {}

    def save_config(self):
        """Save models configuration to file"""
        with open(self.config_file, "w") as f:
            json.dump(self.downloaded_models, f, indent=2)

    def list_available_models(self) -> Dict:
        """List all available models for download"""
        return self.available_models

    def list_downloaded_models(self) -> List[str]:
        """List all downloaded models"""
        models = []
        for model_name in self.downloaded_models.keys():
            model_path = self.models_dir / model_name
            if model_path.exists():
                models.append(model_name)
        return models

    def get_model_size(self, model_name: str) -> int:
        """Get model directory size in bytes"""
        model_path = self.models_dir / model_name
        if not model_path.exists():
            return 0

        total_size = 0
        for file_path in model_path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def get_disk_space(self) -> Dict:
        """Get available disk space"""
        stat = os.statvfs(self.models_dir)
        total = stat.f_frsize * stat.f_blocks
        free = stat.f_frsize * stat.f_bavail
        used = total - free

        return {"total": total, "free": free, "used": used, "free_gb": free / (1024**3)}

    async def check_hf_access(self, model_name: str) -> bool:
        """Check if we can access the Hugging Face model"""
        if model_name not in self.available_models:
            return False

        repo_id = self.available_models[model_name]["repo_id"]
        url = f"https://huggingface.co/{repo_id}"

        try:
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False

    async def download_model_git(self, model_name: str, progress_callback=None) -> bool:
        """Download model using git clone (recommended)"""
        if model_name not in self.available_models:
            print(f"❌ Unknown model: {model_name}")
            return False

        model_info = self.available_models[model_name]
        repo_id = model_info["repo_id"]
        model_path = self.models_dir / model_name

        if model_path.exists():
            print(f"⚠️ Model {model_name} already exists")
            return True

        print(f"📥 Downloading {model_name} from {repo_id}")
        print(f"📁 Target directory: {model_path}")
        print(f"💾 Expected size: {model_info['size']}")

        try:
            # Use git clone for efficient downloading
            cmd = ["git", "clone", f"https://huggingface.co/{repo_id}", str(model_path)]

            if model_info.get("requires_auth"):
                print("🔐 This model requires Hugging Face authentication")
                print("Please run: huggingface-cli login")
                # For models requiring auth, we might need to use the HF token
                hf_token = os.getenv("HF_TOKEN")
                if hf_token:
                    cmd = [
                        "git",
                        "clone",
                        f"https://user:{hf_token}@huggingface.co/{repo_id}",
                        str(model_path),
                    ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
            )

            # Monitor progress
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output and progress_callback:
                    progress_callback(output.strip())
                if output:
                    print(f"   {output.strip()}")

            if process.returncode == 0:
                print(f"✅ Successfully downloaded {model_name}")

                # Update configuration
                self.downloaded_models[model_name] = {
                    "repo_id": repo_id,
                    "downloaded_at": time.time(),
                    "size": self.get_model_size(model_name),
                    "path": str(model_path),
                }
                self.save_config()
                return True
            else:
                print(f"❌ Failed to download {model_name}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Git clone failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False

    async def download_model_hf(self, model_name: str, progress_callback=None) -> bool:
        """Download model using huggingface-hub library"""
        try:
            from huggingface_hub import snapshot_download
        except ImportError:
            print("❌ huggingface-hub not installed. Run: pip install huggingface-hub")
            return False

        if model_name not in self.available_models:
            print(f"❌ Unknown model: {model_name}")
            return False

        model_info = self.available_models[model_name]
        repo_id = model_info["repo_id"]
        model_path = self.models_dir / model_name

        if model_path.exists():
            print(f"⚠️ Model {model_name} already exists")
            return True

        print(f"📥 Downloading {model_name} using huggingface-hub")

        try:

            def download_callback(progress):
                if progress_callback:
                    progress_callback(progress)

            downloaded_path = snapshot_download(
                repo_id=repo_id, local_dir=str(model_path), local_dir_use_symlinks=False
            )

            print(f"✅ Successfully downloaded {model_name}")

            # Update configuration
            self.downloaded_models[model_name] = {
                "repo_id": repo_id,
                "downloaded_at": time.time(),
                "size": self.get_model_size(model_name),
                "path": downloaded_path,
            }
            self.save_config()
            return True

        except Exception as e:
            print(f"❌ Download failed: {e}")
            return False

    def delete_model(self, model_name: str) -> bool:
        """Delete a downloaded model"""
        model_path = self.models_dir / model_name

        if not model_path.exists():
            print(f"⚠️ Model {model_name} not found")
            return False

        try:
            import shutil

            shutil.rmtree(model_path)

            if model_name in self.downloaded_models:
                del self.downloaded_models[model_name]
                self.save_config()

            print(f"✅ Deleted model {model_name}")
            return True

        except Exception as e:
            print(f"❌ Failed to delete {model_name}: {e}")
            return False

    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get information about a specific model"""
        if model_name in self.available_models:
            info = self.available_models[model_name].copy()
            info["name"] = model_name

            if model_name in self.downloaded_models:
                info["downloaded"] = True
                info["size_bytes"] = self.get_model_size(model_name)
                info["downloaded_at"] = self.downloaded_models[model_name][
                    "downloaded_at"
                ]
            else:
                info["downloaded"] = False

            return info

        return None


# CLI Interface
async def main():
    """Command line interface for the model download manager"""
    manager = ModelDownloadManager()

    if len(sys.argv) < 2:
        print("🤖 FinSavvyAI Model Download Manager")
        print("=" * 40)
        print("\nUsage:")
        print("  python3 download_models.py list          # List available models")
        print("  python3 download_models.py downloaded     # List downloaded models")
        print("  python3 download_models.py download <model>  # Download a model")
        print("  python3 download_models.py delete <model>    # Delete a model")
        print("  python3 download_models.py info <model>      # Get model info")
        print("\nAvailable models:")
        for name, info in manager.list_available_models().items():
            status = "✅" if name in manager.list_downloaded_models() else "⬇️"
            print(f"  {status} {name} - {info['description']} ({info['size']})")
        return

    command = sys.argv[1].lower()

    if command == "list":
        print("📋 Available Models:")
        print("-" * 40)
        for name, info in manager.list_available_models().items():
            print(f"🤖 {name}")
            print(f"   Description: {info['description']}")
            print(f"   Size: {info['size']}")
            print(f"   Type: {info['type']}")
            if info.get("requires_auth"):
                print(f"   ⚠️ Requires Hugging Face authentication")
            print()

    elif command == "downloaded":
        downloaded = manager.list_downloaded_models()
        if not downloaded:
            print("📭 No models downloaded yet")
        else:
            print("📥 Downloaded Models:")
            print("-" * 40)
            for name in downloaded:
                size_bytes = manager.get_model_size(name)
                size_gb = size_bytes / (1024**3)
                info = manager.get_model_info(name)
                print(f"✅ {name}")
                print(f"   Size: {size_gb:.2f}GB")
                if info and info.get("downloaded_at"):
                    import time

                    downloaded_time = time.ctime(info["downloaded_at"])
                    print(f"   Downloaded: {downloaded_time}")
                print()

    elif command == "download":
        if len(sys.argv) < 3:
            print("❌ Please specify a model to download")
            return

        model_name = sys.argv[2]
        if model_name not in manager.list_available_models():
            print(f"❌ Unknown model: {model_name}")
            return

        # Check disk space
        disk_info = manager.get_disk_space()
        print(f"💾 Available disk space: {disk_info['free_gb']:.1f}GB")

        if disk_info["free_gb"] < 5:
            print("⚠️ Low disk space! You need at least 5GB free for most models")
            return

        # Try git download first, fallback to huggingface-hub
        success = await manager.download_model_git(model_name)
        if not success:
            print("🔄 Trying huggingface-hub download...")
            success = await manager.download_model_hf(model_name)

        if success:
            print(f"🎉 Model {model_name} is ready to use!")
        else:
            print(f"❌ Failed to download {model_name}")

    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Please specify a model to delete")
            return

        model_name = sys.argv[2]
        manager.delete_model(model_name)

    elif command == "info":
        if len(sys.argv) < 3:
            print("❌ Please specify a model")
            return

        model_name = sys.argv[2]
        info = manager.get_model_info(model_name)

        if info:
            print(f"🤖 Model Information: {model_name}")
            print("-" * 40)
            print(f"Description: {info['description']}")
            print(f"Size: {info['size']}")
            print(f"Type: {info['type']}")
            print(f"Repository: {info['repo_id']}")
            print(f"Downloaded: {'Yes' if info['downloaded'] else 'No'}")

            if info["downloaded"]:
                size_gb = info["size_bytes"] / (1024**3)
                print(f"Actual Size: {size_gb:.2f}GB")
                print(f"Path: {info['path']}")
        else:
            print(f"❌ Unknown model: {model_name}")

    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
