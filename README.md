# Agent Arena
A multi-model benchmarking platform that races GPT-4o, Claude Sonnet, and Gemini Flash on the same GitHub issue. Compares cost, speed, and quality in real time, instrumented with PostHog LLM observability.

## Table of Contents

- [Demo](#demo)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Insights — Dogfooding in Action](#insights--dogfooding-in-action)
- [Roadmap](#roadmap)

## Demo

The general flow of Agent Arena from creating a GitHub issue to launching 3 competing AI agents. Shows the process of context retrieval → planning → coding → PR creation.

[![Agent Arena Demo](https://img.youtube.com/vi/Qj8r42F1ZIw/0.jpg)](https://www.youtube.com/watch?v=Qj8r42F1ZIw)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, LangGraph, LiteLLM, asyncio |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| LLM Models | GPT-4o, Claude Sonnet, Gemini Flash |
| Retrieval | Pinecone (semantic search) |
| Observability | PostHog (`$ai_generation` events) |
| Visualization | Recharts, React Flow |****

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
 
## Insights — Dogfooding in Action

Agent Arena instruments itself. Every LLM call in the pipeline emits a `$ai_generation` event, and the Insights page surfaces that telemetry in the UI with cost, tokens, latency, and success rate broken down by phase and model.

> **Note:** These numbers reflect a small sample of test runs on a single sandbox repo, not a production-grade benchmark. The goal isn't to crown a "best model" but to demonstrate what becomes visible when you instrument your AI pipeline properly.

### Insights Dashboard
<img width="1050" height="857" alt="agent-arena-insights" src="https://github.com/user-attachments/assets/7d657ed6-f01c-4b60-ab28-15043aefe7e9" />

### What the data surfaced

**Reliability varies across models.** Claude Sonnet showed the strongest pipeline conversion (80%), rarely failing once it cleared context retrieval. GPT-4o landed in the middle (59%), with occasional failures at both ends of the pipeline. Gemini Flash started the most runs but finished the fewest (32%) suggesting it compensates for lower quality with more retries in the ReAct loop.

**Cost alone is misleading.** Gemini Flash is the cheapest per call, but its low conversion rate means a lot of that spend goes toward failed runs. Claude Sonnet is the most expensive per call, but its higher reliability makes the cost-per-successful-PR more competitive than the raw numbers suggest. Without observability, users would only see the per-call price and miss the bigger picture.

**Token patterns reveal strategy differences.** Claude Sonnet consumed significantly more input tokens, especially during planning and context retrieval. This indicates it reads more context before acting. The other models were more balanced between input and output. This heavier upfront investment in context likely contributes to Claude's higher completion rate.

### The point

None of these insights was obvious before instrumentation. LLM observability gives users visibility into cost, tokens, latency, and success rate per phase, per model, so they can make informed decisions about which models to use, where the  pipeline is breaking, and where the budget is actually going.

## Roadmap

- **Custom Repo Support** — allow users to connect their own GitHub repositories instead of running against a fixed sandbox repo, so they can benchmark models on their actual codebase and issues
- **Sandbox Execution (Testing)** — add a containerized runtime that executes each model's generated code before PR creation, validating that the output actually runs and passes tests rather than relying solely on code review
- **Quality Scoring** — automated diff analysis to score each PR on correctness, code style, and completeness. Move from just "did it create a PR" to "was the PR actually good"
- **Prompt Template Experimentation** — let users swap out system prompts per phase and compare how different prompt strategies affect cost, speed, and output quality across models
