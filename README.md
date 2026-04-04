# Agent Arena
A multi-model benchmarking platform that races GPT-4o, Claude Sonnet, and Gemini Flash on the same GitHub issue. Compares cost, speed, and quality in real time, instrumented with PostHog LLM observability.

## Architecture
### Backend

The backend is a FastAPI application built around a LangGraph `StateGraph`. Each agent run is an autonomous ReAct loop that decides which tools to call based on the current state.

- **Async Parallel Execution**

  All three strategies run concurrently via `asyncio.gather`. GPT-4o, Claude Sonnet, and Gemini Flash will process the task in parallel rather than sequentially. Each strategy runs in its own thread via `loop.run_in_executor` to avoid blocking the event loop.

- **Agent Tools**

  Each model is a ReAct agent with four tools at its disposal:
  
  - **Retrieve Context** — semantic search via Pinecone to find the most relevant files in the repo
  - **Plan** — LLM generates an execution plan across the retrieved files
  - **Code** — LLM generates file modifications
  - **Create PR** — commits changes and opens a GitHub Pull Request

- **Real-time Streaming (SSE)**

  As each agent completes a phase, it pushes an event to a shared `asyncio.Queue`. A FastAPI `StreamingResponse` consumes the queue and streams Server-Sent Events to the frontend in real time. The frontend will receive step updates, artifacts, and final summaries without polling.

- **Observability**
  Every LLM call emits a `$ai_generation` event to PostHog with:
  - `$ai_model` — which model was called
  - `$ai_input_tokens` / `$ai_output_tokens` — token usage
  - `$ai_total_cost_usd` — cost per call
  - `$ai_latency_ms` — response time
  - `phase` — which pipeline phase the call belongs to
  - `strategy_name` — which model strategy is running
  - `arena_trace_id` — ties all calls from the same arena run together

### Frontend

The frontend is a React application built on Typescript and Tailwind CSS.

- **Pre-Launch View**
  Repo viewer (file tree via GitHub API), issue creator, and agent configurator side by side. Users write an issue, configure model/temperature per agent, and hit Launch Run.

- **Live Monitor**
  On launch, three `AgentTrack` components stream SSE events in real time. Each track moves through the pipeline phases independently, showing live step progress and collapsible artifacts (context files, execution plan, generated code) at each phase.

- **Insights Page**
  Three PostHog-powered charts surfaced directly in the UI:
  - **Phase Funnel** — React Flow visualization showing conversion rate across pipeline phases per model
  - **Cost Breakdown** — grouped bar chart showing total LLM cost per phase by model
  - **Token Usage** — stacked bar chart showing input vs output token split per phase by model
