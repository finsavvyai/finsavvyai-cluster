# 🏠 FinSavvyAI Home Cluster

Your own private LLM cluster that distributes work across all your computers!

## 🚀 Quick Setup

### 1. On Your Main Computer (Cluster Master)
```bash
# Install dependencies
pip3 install aiohttp

# Start the cluster master
python3 cluster_master.py
```

### 2. On Other Laptops (Workers)
```bash
# Install dependencies  
pip3 install aiohttp psutil

# Start the worker
python3 cluster_worker.py
```

That's it! Your cluster will auto-discover and distribute requests.

## 📱 Mobile Access

Once running, use from any device:

**API Key**: `finsavvy-5d19b8e7c71d4679`

**Endpoints**:
- Health: `http://YOUR_IP:8000/health`
- Cluster Status: `http://YOUR_IP:8000/cluster/status`
- Chat API: `http://YOUR_IP:8000/v1/chat/completions`

**Example Usage**:
```bash
curl -H "Authorization: Bearer finsavvy-5d19b8e7c71d4679" \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"Hello!"}]}' \
     http://YOUR_IP:8000/v1/chat/completions
```

## 🎯 What This Does

✅ **No more OpenAI/Anthropic bills** - Use your own computers  
✅ **Automatic load balancing** - Distributes work across all devices  
✅ **Mobile access** - Use from anywhere with internet  
✅ **OpenAI compatible** - Works with existing apps  
✅ **Zero configuration** - Workers auto-discover the master  

## 🔧 Advanced Usage

### Check Cluster Status
```bash
curl http://YOUR_IP:8000/cluster/status
```

### List Connected Nodes
```bash
curl http://YOUR_IP:8000/cluster/nodes
```

### Add More Computers
Just run `python3 cluster_worker.py` on any laptop you want to add!

## 🌐 Network Discovery

The cluster automatically:
- Scans your local network (10.0.0.x range)
- Finds available worker nodes
- Balances requests based on load
- Handles node failures gracefully

## 📊 Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Mobile App    │    │   Web Client    │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
          ┌─────────────────────┐
          │   Cluster Master    │  ← Port 8000
          │   (Load Balancer)   │
          └─────────┬───────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───▼───┐      ┌───▼───┐      ┌───▼───┐
│Worker1│      │Worker2│      │Worker3│
│Laptop │      │Desktop│      │Server │
└───────┘      └───────┘      └───────┘
```

## 🎉 You're Ready!

**Start the cluster master, run workers on other laptops, and enjoy your private LLM network!**

Your cluster will automatically handle all the complexity - you just get fast, private AI responses from your own computers. 🚀