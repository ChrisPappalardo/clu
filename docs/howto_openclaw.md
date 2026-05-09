# How I built my local OpenClaw box (CLU‑oriented)

This guide documents the exact approach I use for a **local‑only** OpenClaw setup that can live “in the closet” and act as the always‑on base for a CLU‑style agentic council. It follows the flow of the OpenClaw setup article and is grounded in the hardware/quantization research in `docs/research/openclaw_pi_hardware_quantization_research.md`.

**Order of sections**
1. Concepts (LLM sizing, quantization, GPU classes)
2. Recommended ITX hardware list
3. Installation (Ubuntu + llama.cpp + OpenClaw + optional Ollama)
4. Agent configuration (Gmail, Telegram, optional channels)

---

## 1) Concepts: model sizing, quantization, and GPU classes

### 1.1 Model parameters → GPU memory
A model’s **parameter count** is the main driver of GPU memory (VRAM) usage. A helpful rule‑of‑thumb:

- **fp16/bf16:** VRAM ≈ **2 × X GB** for X‑billion parameters
- **fp32:** VRAM ≈ **4 × X GB** for X‑billion parameters

For short contexts, weight memory dominates. For long contexts, attention memory can dominate (see below).

### 1.2 Quantization: smaller models in less VRAM (with trade‑offs)
Quantization stores weights in fewer bits:

- **INT8:** ~1 byte/parameter
- **INT4:** ~0.5 bytes/parameter

Most quantized formats add a small overhead (roughly 8–15%). GGUF, GPTQ, and AWQ differ slightly, but the practical takeaway is: **INT4 cuts VRAM dramatically**, usually with a **small quality hit** that varies by model and task.

**What to expect in practice (quality):**
- INT8 is often near‑FP16 in quality.
- INT4 is typically good for everyday tasks, but can show measurable drops in perplexity/accuracy depending on model and benchmark.

### 1.3 Context length grows memory fast
Self‑attention memory scales **quadratically** with context length. If you double context, you more than double memory use. This is why a model that fits at 4k context can OOM at 16k without any change to weights.

**Practical rule:** If you care about long contexts, budget extra VRAM headroom even when weights “fit.”

### 1.4 CPU / disk offload: what happens when VRAM runs out
If a model doesn’t fully fit in GPU memory:
- It spills to **system RAM** (much slower).
- If RAM is insufficient, it can spill to **disk** (very slow).

This keeps things running, but latency climbs. For an always‑on OpenClaw box, you want **VRAM to fit the model** and **RAM to avoid disk offload**.

### 1.5 GPU classes and price/performance
You have three practical GPU classes:

1. **Consumer RTX (best value):**
   Great price/perf, easiest to find. The sweet spot for local LLMs under $1,500.

2. **Workstation GPUs (RTX A‑series):**
   More VRAM, much higher cost. Usually not worth it unless you need 24–48GB in a single card and have budget headroom.

3. **Datacenter GPUs (A/H‑series):**
   Highest performance and VRAM, but priced out of consumer budgets and not suited to ITX builds.

**Bottom line:** For a closet‑friendly ITX build under $1,500, a **consumer RTX GPU** (new or used) is the right choice.

---

## 2) Recommended ITX “closet box” hardware list (<$1,500)

This list is designed for a **quiet, compact, always‑on** system with enough VRAM headroom for **7–13B models in fp16** or **20–30B models in INT4**, depending on context length.

### 2.1 Core build (recommended)

| Component | Recommendation | Why |
| --- | --- | --- |
| **Case** | Cooler Master NR200 (or similar airflow‑first ITX case) | Great airflow and GPU clearance; keeps temps low in a closet. |
| **GPU** | **RTX 4070 Ti Super 16GB** (new) | Best price/perf with 16GB VRAM; enough for larger INT4 models. |
| **CPU** | AMD Ryzen 7 7700 (65W) | Efficient, plenty of CPU for orchestration and offload without excess heat. |
| **Motherboard** | B650 ITX board (Wi‑Fi) | Modern platform, small footprint, stable. |
| **RAM** | 64GB (2×32GB) DDR5 | Provides RAM headroom for CPU offload and large context loads. |
| **Storage** | 2TB NVMe SSD | Fast disk for model storage and any offload. |
| **PSU** | 750W SFX (80+ Gold/Platinum) | Quiet + sufficient headroom for a 16GB GPU. |
| **Cooler** | Low‑profile or compact tower with quiet fans | Keep noise down in a closet. |

**Why 16GB VRAM?** It’s the best compromise for price/perf under $1,500 and gives you realistic room for larger quantized models and multi‑agent workloads.

See https://pcpartpicker.com/list/WsvCzv

### 2.2 Used‑GPU alternative (more VRAM)
If you can find a **used RTX 3090 (24GB)** at a good price and it fits your case, it’s the best VRAM‑per‑dollar option. It runs hotter and draws more power, so make sure your case has strong airflow and your PSU is sized accordingly.

### 2.3 Closet‑friendly settings
- **Set a power limit** on the GPU (70–80%) to cut heat/noise with small performance loss.
- Use **quiet fan curves** and higher‑airflow intake.
- Avoid a sealed cabinet; give the case **airflow in/out**.

---

## 3) Installation (Ubuntu + llama.cpp + OpenClaw)

### 3.1 Install Ubuntu LTS
1. Install **Ubuntu 24.04 LTS** (or 22.04 if you prefer longer‑tested driver compatibility).
2. Enable SSH during install (headless closet access).
3. After first boot:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y build-essential git curl unzip
   ```

### 3.2 Install NVIDIA drivers
Use Ubuntu’s recommended drivers:
```bash
sudo ubuntu-drivers install
sudo reboot
```
Verify:
```bash
nvidia-smi
```

### 3.3 Build llama.cpp from source (GPU)
llama.cpp is the primary local runtime in this guide.

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build -j
```

**Notes**
- Binaries land in `build/bin/`.
- If your version uses classic Makefiles, binaries may be `./main` and `./server`; check the build output for exact names.

### 3.4 Download a GGUF model
Store models under a dedicated folder (e.g., `~/models`).
Choose a GGUF file that matches your VRAM budget and desired quantization.

### 3.5 Quick local test
Run a local prompt to validate the model:
```bash
./build/bin/llama-cli -m ~/models/your-model.gguf -p "Summarize the news in 3 bullet points."
```

### 3.6 Optional: run a local HTTP server
llama.cpp can expose an HTTP server for local clients. Check the build output for the server binary name and run it with your model. This makes it easy for OpenClaw to call a local, OpenAI‑compatible endpoint.

### 3.7 Install OpenClaw
OpenClaw’s official install script:
```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```
Then run onboarding:
```bash
openclaw onboard
```

### 3.8 Optional: install Ollama (secondary runtime)
If you want an alternate local runtime with easy model management:
```bash
curl -fsSL https://ollama.com/install.sh | bash
```

You can use Ollama for quick model swaps and llama.cpp for tuned performance.

---

## 4) Configure OpenClaw agents (Gmail, Telegram, optional channels)

### 4.1 Dedicated agent account (recommended)
Create a **separate Gmail account** for the agent so you can grant limited access and keep personal email isolated.

### 4.2 Workspace identity files
OpenClaw stores agent identity and instructions in workspace files. Create/edit:

- **AGENTS.md** — core instructions and memory
- **SOUL.md** — tone and boundaries
- **IDENTITY.md** — name, emoji, vibe
- **TOOLS.md** — how tools should be used
- **USER.md** — your preferences and context

These files are loaded at startup, so they act as the agent’s “operating system.”

### 4.3 Telegram channel (recommended)
1. Install Telegram on your phone.
2. Use **@BotFather** to create a bot and get a token.
3. Add the token in OpenClaw’s Telegram channel configuration.

Telegram is the easiest always‑on channel for daily use.

### 4.4 Gmail and Google Calendar access
Enable the Gmail/Calendar skill during onboarding (or add it later).
Keep access **read‑only** whenever possible, and only expand permissions when you trust the workflows.

### 4.5 Optional channels
Add additional channels as needed:
- **Slack** (team ops / reminders)
- **Discord** (community / dev coordination)
- **WhatsApp** (personal messaging)
- **iMessage** (Mac‑bound personal workflows)

Treat each channel as a “front door” to the same agent brain.

### 4.6 First‑run checklist
- OpenClaw Gateway running
- Local LLM runtime running (llama.cpp server or Ollama)
- Telegram bot connected
- Gmail/Calendar permissions validated
- Workspace files populated (AGENTS/SOUL/IDENTITY/TOOLS/USER)

Once all of the above are green, give your agent a **single concrete job** (e.g., “Create a daily CLU briefing summary at 6am”) and let it run.

---

## Next steps (CLU‑oriented)
- Add your CLU data sources and briefing formats to AGENTS.md.
- Create a daily cron schedule for briefings and reports.
- Gradually add tools and channels as you trust the system.

This should leave you with a quiet, local, always‑on OpenClaw box that can serve as the base for your CLU‑style agentic council.
