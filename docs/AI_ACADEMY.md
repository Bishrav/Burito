# Burito Academy and research plan

Extend the existing `curriculum/seed.json`, `burito/school.py` and
`burito/knowledge.py` instead of starting a second lesson engine. Use the existing
private storage model for installed lessons. Keep original examples and synthetic
fixtures in Git and store authorized third-party material privately with its
license. Source-grounded retrieval preserves citations.

## Expandable curriculum

| Track | Scope and first example |
| --- | --- |
| Mathematics and computing | Algebra, vectors and tensors, decompositions, calculus, probability, Bayesian statistics, information theory, optimization, numerical methods, discrete math, graphs, algorithms, complexity, OS, systems, networks, databases, security, compilers, parallelism and GPU programming. Check a finite-difference gradient against an analytic one. |
| Classical ML | Supervised, unsupervised and semi-supervised learning; regression, regularization, neighbors, trees, forests, SVMs, kernels, boosting, Bayes, Gaussian processes, clustering, PCA, anomaly detection, calibration, time series and recommendations. Fit regression from scratch against a deterministic baseline. |
| Deep learning | Perceptrons, MLPs, backpropagation, activations, losses, SGD/Adam, regularization, normalization, CNNs, RNN/LSTM/GRU, autoencoders, GANs and diffusion. Validate gradients before a small CPU-trained network. |
| Transformers and language | Tokenization, embeddings, attention, position, encoder/decoder and mixture of experts, pretraining, instruction and preference tuning, retrieval, LoRA/QLoRA, quantization, distillation, KV caching, routing and evaluation. Compare local retrieval with a keyword baseline. |
| Reinforcement learning | MDPs, rewards, Bellman equations, dynamic programming, Monte Carlo, TD, Q-learning/SARSA, DQN, policy gradients, actor–critic/PPO, contextual bandits, offline and multi-agent RL, and safe exploration. Use a seeded grid simulation before any computer integration. |
| NLP, vision and audio | Intent, entities, extraction, sentiment, summaries, QA, semantic search, dialogue; image processing, classification, detection, segmentation, OCR, spatial reasoning, multimodal models; DSP, voice activity, recognition, synthesis, wake words and interruption. Use synthetic or licensed fixtures. |
| Advanced AI and research | Transfer, active, continual, federated, self-supervised, online, meta- and few-shot learning; curriculum learning, causal inference, evolutionary search, constraints, neuro-symbolic AI, knowledge graphs, planning, multi-agent systems, cognitive and world models, AutoML, interpretability, alignment, safety and robustness. Add emerging topics through verified references and owner-approved goals. |

Each module requires an ID, prerequisites, objectives, math, verified sources,
examples, a from-scratch implementation where useful, a framework comparison,
exercises, synthetic or licensed data, correctness tests, benchmarks, failure
cases, a Burito application and an exit criterion. Record collected, indexed,
evaluated understanding, implemented, trained, evaluated and approved as distinct
states. A stored lesson does not establish understanding.

## Starter source registry

| Source | Initial use and ingestion status |
| --- | --- |
| [MIT 6.036](https://ocw.mit.edu/courses/6-036-introduction-to-machine-learning-fall-2020/) | Fall 2020 course, instructors listed by MIT. Link verified; materials not imported. |
| [Stanford Engineering Everywhere CS229](https://see.stanford.edu/Course/CS229) | Stanford course notes for classical ML. Link verified; confirm item terms before import. |
| [Dive into Deep Learning](https://d2l.ai/) | Candidate text and implementation examples. Record edition and separate code and prose terms per artifact. |
| [PyTorch tutorials](https://docs.pytorch.org/tutorials/) | Official framework tutorials. Pin package and documentation versions for experiments. |

Screen Berkeley and CMU course materials, official Hugging Face documentation,
established ML/DL/RL textbooks, peer-reviewed papers, arXiv and OpenReview per
item before ingestion. A preprint is provisional evidence. Each item needs
URL, title, author, publication date, version, license, ingestion date, subject,
verification and reliability. Record unknown fields and defer imports with
unresolved rights. Respect access controls and copyright. Link first.

## Learning and experiment lifecycle

Keep a small research area isolated from production. Start with unit-tested
standard-library baselines for intent, duration, ranking, recommendations,
classification, calibration, failure recovery, context and routing. Add NumPy,
scikit-learn or PyTorch only when an experiment requires it. Evaluate Pandas,
SciPy, JAX, Transformers, PEFT, Gymnasium, Stable-Baselines3, FAISS, MLflow,
Optuna or ONNX Runtime against measured need. No framework bundle is required.

Record dataset/model version, split, seed, configuration, time, hardware use,
metrics, baseline, failures, limitations and artifact checksums. Use frozen
synthetic test fixtures, evaluate privacy and security regressions, and compare
task success, uncertainty, resource use and latency. Train candidates in
isolation and keep an artifact registry with checksum, data provenance, results
and rollback target. Require owner approval for deployment and monitor changes.
Guard against poisoning, leakage, overfitting, forgetting, reward hacking and
unauthorized training. A database update or retrieval changes what the model
can read. Training or adaptation changes weights or separate learned adapters.

The RTX 5070 has a 12 GB VRAM budget and Qwen3 8B at 8K is the production baseline.
Start with CPU classical ML and tiny networks. Benchmark driver/runtime
compatibility, peak VRAM/RAM, temperature, duration and storage before a training
run. Investigate mixed precision, efficient attention, accumulation, checkpointing,
offload, quantization, LoRA/QLoRA, specialist models and distillation only against
measured goals. Keep inference and training workloads separate where they
compete. Obtain approval for large downloads, private training and heavy runs.
No frontier pretraining or continuous production self-training.

Reusable skills require approval of their purpose, preconditions, tools, inputs,
scope, execution, expected results, verification, known failures, recovery and
versions. An observed task never creates standing permission.
