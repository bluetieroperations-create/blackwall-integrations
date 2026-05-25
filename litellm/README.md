# Black_Wall + LiteLLM

Gate agent actions at your **LLM gateway**. If your agents route through the LiteLLM
Proxy, this guardrail risk-checks every `tool_call` the model returns *before* it
reaches your agent — blocked calls are stripped and replaced with guidance, so the
agent never executes the dangerous one. One place to protect every agent behind the
proxy.

```bash
pip install litellm requests
export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

## Proxy setup (sits in the request path)

Drop [`blackwall_guardrail.py`](./blackwall_guardrail.py) next to your proxy config and register it:

```yaml
# config.yaml
litellm_settings:
  callbacks: blackwall_guardrail.blackwall_instance
```

Now every response that comes back through the proxy with `tool_calls` gets each call
risk-checked. On `STOP` / `HUMAN_REQUIRED`, the call is removed from the response and
the agent is told it was **not executed** — it course-corrects instead of running it.

> Reference implementation for the proxy **post-call hook**. LiteLLM's `CustomLogger`
> hook signatures and response shape change between versions — the response-walking is
> written defensively, but test against your version and adjust if needed.

## SDK fallback (if you're not running the proxy)

If you use the LiteLLM **SDK** directly (`litellm.completion(...)`) and execute tools in
your own code, you don't need the callback — just put a guard on the tool functions
(see the [`crewai`](../crewai), [`langchain`](../langchain), or [`pydantic-ai`](../pydantic-ai)
guards; the `@guard` decorator is framework-agnostic).

Run [`blackwall_guardrail.py`](./blackwall_guardrail.py) directly for a quick logic smoke test (no LiteLLM needed).
