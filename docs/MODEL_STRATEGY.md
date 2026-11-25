# Model strategy

Use Qwen3 8B Q4_K_M through local Ollama initially. The Modelfile allocates
8,192 tokens. The migration launcher expects the `burito-local:8b` alias.
When verifying with a different installed alias, pass it explicitly.

On the RTX 5070, the 8K test delivered 97.5 generation tokens/s with full GPU
offload and 6,905 MiB peak GPU memory. 32K used 10,854 MiB. The 40K test
partially offloaded and fell to 50.0 tokens/s. The model found the synthetic
code word at all tested lengths, with exact one-word formatting only at 4K.
See the [Ryoku setup guide](RYOKU_SETUP.md) for the complete measurements.

Evaluate task success, latency, tool reliability, output formatting and memory
consumption before changing defaults. Prefer local inference for private
context. Optional cloud routing requires explicit data sharing, a cost limit
and an auditable routing decision. Model changes should be reversible.
