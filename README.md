```markdown
# 🚀 Hybrid AI Homelab Gateway

A production-grade, "scale-to-zero" AI routing gateway built for a high-performance Windows/WSL2 workstation. This stack intelligently routes user prompts from a unified web interface to either a local GPU cluster (Ollama) or cloud-based AI agent teams (Google Gemini), securely exposed to the outside world via Cloudflare Zero Trust.

## 🏗️ Architecture Overview
* **Frontend:** Open WebUI (Local Port 8080)
* **Router:** Python FastAPI (`gateway.py`)
* **Local Compute:** Ollama (Gemma models via RTX 5070 Ti)
* **Cloud Compute:** Google Gemini 2.5 Flash (Standard & Agentic Sandbox)
* **Ingress:** Cloudflare Tunnels
* **Process Manager:** PM2 (Node.js)

### Routing Logic
* **Default:** Prompts map directly to the local GPU (0 external token cost).
* **`#gemini` tag:** Bypasses local hardware and streams a direct, single-turn response from Gemini 2.5 Flash.
* **`#codeagent` tag:** Wakes up a multi-agent cloud team (Supervisor + Coder). The Supervisor uses live Google Search and local RAG document context to formulate a plan, then passes it to the Coder to write and execute Python in an isolated cloud sandbox.

---

## ⚙️ System Requirements & Tuning (Crucial)

This stack is designed for a heavy workstation (e.g., 128GB RAM, high-end GPU). To prevent the WSL2 Linux subsystem from starving Windows of resources and causing UI stutter, you **must** apply these system limits.

### 1. WSL Hard Limits (`.wslconfig`)
In your Windows user directory (`%USERPROFILE%`), create a `.wslconfig` file to cap Linux memory and prevent disk-swap freezing:
```ini
[wsl2]
memory=32GB
processors=8
swap=0

```

*Run `wsl --shutdown` in PowerShell after creating this to apply the limits.*

### 2. Ollama VRAM Auto-Release (Scale-to-Zero)

By default, Ollama holds models in VRAM for 5 minutes, which can lag the Windows desktop rendering. Force it to drop the model instantly after a chat pauses.
Inside WSL, run: `sudo systemctl edit ollama.service` and add:

```ini
[Service]
Environment="OLLAMA_KEEP_ALIVE=15s"

```

Reload and apply:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama

```

---

## 🛠️ Environment Setup

### 1. Pull Local Models

Ensure you have your LLMs and your ultra-fast RAG embedding model pulled into Ollama:

```bash
ollama pull gemma4:e4b
ollama pull gemma3:4b
ollama pull nomic-embed-text

```

### 2. Secrets Management

Create a `.env` file in the root of this project folder to securely store your cloud API keys. **Do not commit this file to version control.**

```text
GEMINI_API_KEY="AIzaSyYourActualKeyGoesHere..."

```

---

## 🌐 Open WebUI Configuration

Once Open WebUI is installed, you must lock it behind the Python gateway so it cannot bypass your routing rules.

1. Go to **Admin Panel > Settings > Connections**.
2. **OpenAI API:** Set the Base URL to your Python gateway (e.g., `http://127.0.0.1:8000/v1`).
3. **Ollama API:** Disable/Remove the direct `localhost:11434` connection.
4. Go to **Admin Panel > Settings > Documents**.
5. Set the **Embedding Engine** to `Ollama` and the **Embedding Model** to `nomic-embed-text`. (This keeps your document RAG entirely local and private).

---

## 🚦 Process Management (PM2)

We use PM2 to keep the entire stack running headless in the background.

**Start the Stack:**

```bash
# 1. Start the Python Gateway
pm2 start "uvicorn gateway:app --host 127.0.0.1 --port 8000" --name "ai-gateway"

# 2. Start Open WebUI 
pm2 start open-webui --name "open-webui"

# 3. Start the Secure Cloudflare Bridge
pm2 start "cloudflared tunnel run --url http://localhost:8080 ai-gateway" --name "cloudflare-tunnel"

```

**Save the state** so PM2 remembers this configuration:

```bash
pm2 save

```

**Useful PM2 Commands:**

* `pm2 list` - View system status, CPU, and Memory usage.
* `pm2 logs` - Stream live logs across the whole stack.
* `pm2 flush` - Clear all saved log files to free up disk space.

---

## ⚡ Windows Auto-Boot Automation

WSL sleeps by default on Windows startup. To make this server truly headless (booting silently when you turn on the PC), use the Windows Task Scheduler to wake up WSL and PM2.

1. Open **Windows Task Scheduler**.
2. Create a Basic Task named "Start AI Server (WSL)".
3. Trigger: **When I log on**.
4. Action: **Start a program**.
5. Program: `wsl.exe`
6. Arguments: `bash -lic "pm2 resurrect"`

Now, the moment you log into Windows, your secure Cloudflare tunnel, local Python router, and Web UI will all spin up invisibly in the background with 0% idle CPU usage.

```

```
