# Optional online research

Normal Burito chat stays on the selected local Ollama model. Online research
is a separate tool available only when the owner starts a chat with
`--enable-online`. The model cannot silently fall back to a hosted chat model.

The tool asks for approval on every request and shows the exact search query.
If approved, it sends that query alone to Vercel AI Gateway's Perplexity search
tool. It does not send the local conversation, memory, files, activity, or
project context. Search is billed by the provider; current Gateway docs list
Perplexity search at $5 per 1,000 searches, plus token charges for the selected
answer model. Check current pricing before enabling it.

## Configure a terminal session

Create an AI Gateway key in the Vercel dashboard. Keep it private: do not put
it in Git, a Burito memory, or a chat message. In Konsole, enter:

```sh
read -rsp 'AI Gateway key: ' AI_GATEWAY_API_KEY
printf '\n'
export AI_GATEWAY_API_KEY
export BURITO_GATEWAY_MODEL=openai/gpt-5.4-nano
BURITO_DATA_DIR=/mnt/burito-brain/data python3 -m burito chat \
  --model burito-local:8b --context-tokens 8192 \
  --enable-online --no-files --no-system
```

This model ID is an example. Use a model currently available to your Gateway
account. The local `burito-local:8b` model handles the conversation. The
Gateway model is used only inside the explicitly approved online research
request. You can omit `--no-files` or `--no-system` if you want those local
contexts in the conversation; they are still never included in the outgoing
search request.

After exiting the chat, remove the key from that terminal session:

```sh
unset AI_GATEWAY_API_KEY BURITO_GATEWAY_MODEL
```

If the key or model is missing, Burito refuses to start online mode. Without
`--enable-online`, inherited Gateway variables are removed before the local
agent starts and the online tool is unavailable. Activity-only mode cannot
enable online research. The browser UI does not yet expose approval requests,
so use the terminal chat for this feature.

This is an initial integration, not the roadmap's completed hybrid-routing
milestone. Verify a live search, approval denial, offline failure, timeout,
and provider errors before relying on it.
