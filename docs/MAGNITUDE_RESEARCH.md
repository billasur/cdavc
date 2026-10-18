# Magnitude research and CD-AVC integration

## Sources inspected

- Magnitude repository: https://github.com/magnitudedev/magnitude
- Magnitude README: https://github.com/magnitudedev/magnitude/blob/main/README.md
- Inference v3 README: https://github.com/magnitudedev/magnitude/blob/main/inference-v3/README.md
- Inference v4 overview: https://github.com/magnitudedev/magnitude/blob/main/inference-v4/docs/overview.md

This was a source-level architecture review of the public repository, not a
binary decompilation. The repository is open source, so normal source analysis
was more appropriate than REA binary tooling.

## Observed techniques

Magnitude's public documentation and source structure show several relevant
ideas:

1. **Tune per model and device.** It does not rely only on universal runtime
   defaults. It measures or compiles device-specific implementations and caches
   reusable artifacts.
2. **Keep packed weights packed.** Its v3 documentation describes packet-native
   execution for MLX and GGUF formats rather than expanding full matrices into
   high-precision temporary tensors.
3. **Use speculative decoding.** The product advertises a model-specific
   drafter, while its newer engine has explicit assistant/head/drafter model
   handling.
4. **Treat KV memory as a first-class budget.** The product advertises
   quantized KV caches, bounded arenas and releasing idle capacity.
5. **Share prefixes and batch sessions.** The README calls out prefix-cache
   sharing and fast concurrent sessions. The inference sources contain
   scheduler, prefix-cache, memory and admission components.
6. **Separate policy from execution.** The v4 overview separates service
   admission, batching and lifecycle from numerical compilation and backend
   execution.
7. **Measure rather than claim.** The v3 documentation distinguishes modeled
   estimates, kernel-device time, wall time, cold compilation and warm timing.

## What CD-AVC now adopts

The repository now contains `cdavc.optimization` and `cdavc.launch`.

The launch policy currently:

- reserves memory for macOS/Linux and runtime overhead;
- selects a conservative context size from the model size and memory budget;
- uses q8 KV cache by default;
- limits concurrent sequences on larger models;
- bounds prefill and micro-batch sizes;
- enables continuous batching for llama.cpp;
- adds MTP flags when the model filename indicates an MTP artifact;
- uses MLX's bounded KV and prefill controls;
- lets the user print the command before execution;
- keeps the policy separate from the provider and verification cage.

## Deliberate non-copying boundary

CD-AVC does **not** claim to reproduce Magnitude's kernel compiler, TileLang,
Seismic, Metal code generation, device autotuner or performance claims. Those
are large inference-engine projects, not launch flags.

The next credible step is an empirical local tuner that benchmarks a small set
of safe profiles on the exact M3, stores results keyed by model digest,
runtime version and hardware identity, and reuses only qualified profiles.
