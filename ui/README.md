# Burito interface preview

This is Burito's local, dependency-free assistant console, built with plain HTML, CSS, and JavaScript.

Run `python3 -m burito web --model burito-local:8b --context-tokens 8192` from the repository root and open `http://127.0.0.1:8765`. The chat uses the local Eve runtime. The token meter appears after a turn when the model reports usage; it distinguishes the latest model pass from session totals and labels remaining context as an estimate. It is not a billing quota. No sample hardware readings, activity records, model telemetry, or successful PC actions are presented as real.

Context switches remain preview-only. Approval prompts must stay tied to actual tool requests and show the exact proposed action before execution.
