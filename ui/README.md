# Burito interface preview

This is the first local interface design pass for Burito. It is a static, dependency-free preview of the intended assistant console, built with plain HTML, CSS, and JavaScript.

Open `index.html` in a browser. The orbiting core, clock, responsive navigation, and preview notices are UI behavior only. The assistant runtime is not connected, so chat and context controls are deliberately disabled. No sample hardware readings, activity records, model telemetry, or successful PC actions are presented as real.

The next integration milestone is to serve this UI from a local frontend process and connect its chat panel to Burito's Eve session API, then replace each status placeholder only with data returned by the local runtime. Keep approval prompts tied to actual tool requests and show the exact proposed action before execution.
