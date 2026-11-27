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

## First measured implementation

`academy/linear_regression.py` is the first isolated, standard-library teaching
implementation. It fits a one-variable least-squares line and reports MSE, MAE
and R² (undefined R² is `null` for constant targets). Tests use a deterministic
synthetic training set and separate held-out points. The source basis is
[Stanford CS229's linear regression notes](https://cs229.stanford.edu/notes_archive/cs229-notes-all/cs229-notes1.pdf)
and [MIT OCW's curve-fitting lesson](https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-00sc-introduction-to-computer-science-and-programming-spring-2011/unit-2/lecture-17-curve-fitting/);
neither source has been downloaded or imported. This verifies the implementation
and its tests only. It does not establish course completion, model training or
improved production capability.

The first memory-ranking baseline also reuses FTS5 with a volatile in-memory
index: on 1,010 synthetic records, the top five were all relevant for the fixed
`StudyCircle storage` query; 25 warm searches had a 1.190 ms median and 1.942 ms
p95. This small local measurement does not predict HDD latency or establish a
need for embeddings.

## Operational starter registry

`academy/curriculum/core.json` is the first versioned curriculum registry.
It defines prerequisites, objectives, exercises and test-based completion
criteria for vectors/matrices, descriptive statistics, probability and Bayes,
calculus/gradients, gradient descent, and linear regression. Its sources are
link-only: no third-party course files have been imported. MIT OCW 18.06 covers
linear algebra; 18.05 covers probability, Bayesian inference and statistics;
18.01 covers differentiation and integration; Stanford CS229 notes cover
regression and optimization. Asset licenses must be checked before importing
any course material.

`academy/progress.py` stores topic events through the existing private memory
database. Stages distinguish source verification, registration, retrieval,
passed exercises, implementation, reproduced experiments, benchmarked
capabilities and production approval. Passed work requires evidence; a topic
cannot be marked mastered from a model explanation. `python -m burito academy`
provides owner-managed progress commands. Automated tests use an isolated
database. Six non-personal starter topic records are now persisted on the
verified brain, each at `algorithm_implemented` with repository test evidence;
this is not a claim of course mastery.

The tested standard-library teaching code now includes vector/matrix operations,
descriptive statistics, conditional probability, Bayes, finite-difference
derivatives, gradient descent, closed-form and gradient-descent linear
regression, L2-regularized binary logistic regression, k-nearest neighbors,
a small CART-style decision tree, seeded k-means, classification metrics, and
deterministic train/test and train/validation/test splitting. These are
evaluated implementations, not evidence of course mastery or production
language-model training.

The isolated intent experiment compares deterministic rules with one-vs-rest
logistic regression on 40 training and 20 hand-separated held-out synthetic
phrases. The latest run gave 90% accuracy for both; candidate macro F1 was
0.889 versus 0.899 for the rules. This shows no production benefit. The script
records CPU and wall time, peak process RSS, settings and failure examples. The
candidate is not used by Burito's runtime.

## Retrieval evaluation

`python -m academy.evaluations.memory_retrieval` evaluates the FTS5 baseline on
1,011 temporary synthetic records. Its 13 cases cover exact and lexical
paraphrase recall, temporal/project context, prior decisions, blockers, an
experience, multiple relevant records, corrected/deleted records, conflicts,
irrelevant input and an ambiguous query with no useful search terms. It checks
personal-memory opt-out and conflict metadata. The current run measured
precision@5 0.240, recall@5 1.000, MRR 0.933, 1.157 ms median and 1.204 ms p95
over 60 warm searches. All positive relevant records were returned, though one
was not ranked first. The prior eight-case 1,009-record metrics are not directly
comparable because the query set and stopword/category filtering changed. These
measurements use temporary storage and include rebuilding the FTS index, not
HDD latency. No calibrated score threshold or embedding dependency is justified
by this synthetic set.
