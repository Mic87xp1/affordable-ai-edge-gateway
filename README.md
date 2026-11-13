# Tier-0 Hybrid AI Edge Gateway (Edge-First + Cloud Fallback)

**Part of "The Affordable AI Lab" Initiative** — Demonstrating how legacy, ultra-low-power hardware can be repurposed into a resilient, zero-cost hybrid AI gateway using **Ollama**, **LiteLLM Proxy**, and **Open WebUI**.

---

## Architecture Overview

Running modern LLMs purely on legacy CPUs without dedicated GPUs often leads to high latency and timeouts on complex prompts. This architecture solves the problem by introducing a **latency-based routing layer**:

1. **Edge-First Execution:** Simple queries, bash/SQL commands, and short code snippets are handled 100% locally in under 10 seconds with zero cloud token consumption.
2. **Transparent Cloud Fallback:** If a complex prompt exceeds the local CPU compute threshold (10s), LiteLLM cleanly aborts the local inference and seamlessly delegates the request to a free-tier cloud model without breaking the user's chat session.

```text
[ Open WebUI ] 
      │ (OpenAI-compatible API)
      ▼
[ LiteLLM Proxy ] ──► Custom Telemetry Hook (model_footer.py)
      │
      ├──► Primary (Timeout: 10s) ──► [ Ollama (Local CPU) ] (qwen2.5:0.5b / qwen2.5-coder:0.5b)
      │
      └──► Fallback (On Timeout) ───► [ Google Gemini API ]  (gemini-3.5-flash-lite)
```

---

## Testbed Hardware & Software Stack

* **Host Machine:** Lenovo ThinkCentre M73 Tiny (Legacy Enterprise Mini PC)
* **CPU:** Intel Core i3-4130T (Haswell Dual-Core, 2.90 GHz, 35W TDP, CPU-only inference)
* **RAM:** 8 GB DDR3 (Replicable down to 4 GB systems thanks to the ultra-low 0.5B parameter footprint)
* **OS:** DietPi OS (Debian-based, minimal memory footprint)
* **Inference & Routing Stack:**
  * **Ollama:** Local model runtime (`qwen2.5:0.5b`, `qwen2.5-coder:0.5b`)
  * **LiteLLM Proxy:** Request routing, parameter sanitization, timeout enforcement, and custom logging
  * **Open WebUI:** Self-hosted chat frontend

---

## Engineering Challenges & Solutions

Deploying Small Language Models (0.5B) on legacy x86_64 CPUs surfaced three critical bottlenecks, resolved at the architectural level:

### 1. Tool / Function Calling Overhead on 0.5B Models
* **Bottleneck:** Modern versions of Open WebUI automatically inject JSON schemas for built-in tools (calendar, tasks, memory, code interpreter) into the request payload. A 0.5B model either hallucinates raw JSON schemas instead of answering or saturates the dual-core CPU during prompt prefill, triggering immediate timeouts.
* **Fix:** Disabled built-in tools, code interpreter, memory, and vision capabilities on local model profiles in Open WebUI, paired with `drop_params: true` and strict `allowed_openai_params` whitelisting in LiteLLM before forwarding requests to Ollama.

### 2. Latency-Based Routing (Time-Based Fallback)
* **Bottleneck:** Long timeouts (30s+) degrade user experience on complex tasks, while infinite timeouts lock up the local CPU thread.
* **Fix:** Enforced a strict `timeout: 10` (with `connect_timeout: 2` and `max_retries: 0`) on local Ollama workers. When a task exceeds 10 seconds, LiteLLM intercepts the timeout and routes the prompt to `gemini-3.5-flash-lite` transparently.

### 3. Backend Observability in Chat (`model_footer.py`)
* **Bottleneck:** Open WebUI displays only the selected router alias (e.g., `local-coder`), hiding whether the response was generated locally or served by the cloud fallback.
* **Fix:** Implemented a custom Python `CustomLogger` in LiteLLM (`async_post_call_streaming_iterator_hook` and `async_post_call_success_hook`) that dynamically appends the actual serving model signature to the bottom of every response.

---

## Empirical Benchmarks

| Test Case | Prompt Profile | Target Alias | Execution Path | Outcome & Latency |
| :--- | :--- | :--- | :--- | :--- |
| **Test 1: Short Snippet** | Responsive HTML/CSS/JS sticky header, regex validation, Bash/SQL one-liners | `local-coder` | **100% Local** (`qwen2.5-coder:0.5b`) | Completed in **< 10s**, smooth token streaming, 0 cloud tokens used. |
| **Test 2: Complex Engineering** | Full Java domain class + custom exceptions + dynamic pricing + Javadoc + JUnit 5 `@ParameterizedTest` suite (6 cases) | `local-coder` | **Local -> Cloud Fallback** (`gemini-3.5-flash-lite`) | Local threshold reached at 10s; LiteLLM seamlessly switched to Gemini and delivered the full multi-class implementation with zero UI errors. |

---

## Setup & Configuration

### 1. Clone & Prepare Directory
```bash
git clone https://github.com/Mic87xp1/affordable-ai-edge-gateway.git
cd affordable-ai-edge-gateway
cp config/config.yaml.example config/config.yaml
```

### 2. Pull Local Models via Ollama
```bash
ollama pull qwen2.5:0.5b
ollama pull qwen2.5-coder:0.5b
# Optional: create custom alias if used in config.yaml
ollama cp qwen2.5:0.5b local-worker
```

### 3. Configure API Keys & Start LiteLLM Proxy
Edit `config/config.yaml` with your Google AI Studio API key (or export `GEMINI_API_KEY` as an environment variable), ensure `scripts/model_footer.py` is in your `PYTHONPATH`, and launch the proxy:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/scripts
litellm --config config/config.yaml --port 4000
```

### 4. Configure Open WebUI (Critical for 0.5B Models)
Connect Open WebUI to LiteLLM by adding `http://localhost:4000/v1` as an OpenAI-compatible API endpoint. Then, edit the model profiles for `smart-agent` and `local-coder` (**Workspace → Models → Edit**):

1. **Capabilities:** Uncheck **Vision**, **Web Search**, **Image Generation**, and **Code Interpreter**.
2. **Built-in Tools / Default Features:** Disable **Memory** and any active tool/function calling integrations.

> **Why this matters:** Leaving these enabled injects large JSON tool schemas into every prompt, overwhelming 0.5B parameter models and causing immediate CPU prefill timeouts or raw JSON output.

---

## Roadmap: Next Hardware Tier
This repository establishes the **Tier-0 baseline** on legacy Haswell architecture. The next phase of **The Affordable AI Lab** will benchmark modern **AMD Ryzen Mini PC architectures** (leveraging DDR4/DDR5 bandwidth and Radeon iGPU acceleration) to measure how higher local compute shifts the fallback threshold toward larger parameter models (3B–7B+).