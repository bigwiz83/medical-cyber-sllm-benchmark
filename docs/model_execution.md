# Model execution contract

The executed backbones were Qwen 3.5 27B, Gemma 3 27B, and gpt-oss 20B. Exact Ollama manifest and
weight-blob digests are recorded in `configs/models.lock.json`. All were served from one immutable
Ollama container image listed in `configs/runtime.lock.json`.

Shared settings were temperature 0, inference concurrency 1, a 16,384-token context window, a fixed
seed policy, and no runtime network access. Each condition used five scheduled model calls per cell.
Each call allowed up to three attempts, capped generation at 2,048 tokens, limited the canonical
prompt to 48,000 UTF-8 bytes, and used a 600-second request timeout. Qwen and Gemma used Ollama
`/api/generate` with `format=json` and `stream=false`; gpt-oss used the frozen `/api/chat` route with equivalent
strict-JSON handling. Qwen requests set `think=false`, gpt-oss used `think=low`, and Gemma omitted
the unsupported field. These exact per-condition route and residency values are listed in
`configs/conditions.json`.
The single-RAG form used four independent passes and one synthesis pass. The fixed team used asset,
vulnerability, evidence-checking, context, and coordination slots. Ablated functions were replaced by
a neutral no-op to keep the call ceiling aligned. The bounded autonomous form used a planner, three
host-bounded specialist roles, and a final synthesis pass; host schemas and target identifiers stayed
fixed.

Failures were not retried beyond the frozen per-call ceiling and were retained in scoring. Model
loading was kept resident within a production block instead of loading and unloading for each cell.
The primary Qwen comparator block used `keep_alive="5m"`; the secondary Gemma/gpt-oss block and
the autonomous Qwen block used `keep_alive=-1`. Residency did not change the single-request
concurrency ceiling.
The supplied lock records identify, but do not redistribute, upstream model artifacts.

## Executed hardware

Inference ran on one NVIDIA RTX PRO 6000 Blackwell Workstation Edition GPU with 95.59 GB reported
memory, an AMD Ryzen Threadripper PRO 3995WX CPU with 64 physical and 128 logical cores, and 251.59
GB system memory. The runtime used Docker Desktop 29.5.3 on WSL2 kernel
`6.6.87.2-microsoft-standard-WSL2`. GPU driver and CUDA runtime versions were not archived. Resource
and latency values therefore describe this execution environment and must not be interpreted as a
causal efficiency comparison across architectures.

`configs/prompt_contract.md` separates the comparator finding-envelope contract from the autonomous
planning/specialist/synthesis contract. The public release supports exact reproduction of analyses
from the released terminal predictions and a bounded reconstruction of the inference environment.
It provides every frozen five-slot call-seed schedule and per-cell retrieved-object list, but not raw
transport response bodies, retry histories, intermediate planner or specialist outputs, or the
original runner. It therefore does not claim byte-identical model-call replay.

`environment/original-analysis.uv.lock` is retained only because the frozen mixed-model reports bind
to its SHA-256. It describes the broader executed project environment and contains an editable
project entry; do not run `uv sync` from that file in this public package. Install the self-contained
analysis environment from `requirements-lock.txt` instead.
