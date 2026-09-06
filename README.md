# LangGraph OKF Consumer (Legal Knowledge Graph)

A demonstration consumer for [Google's Open Knowledge Format (OKF v0.2)](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md), using LangGraph for keyword-guided graph traversal over fictional legal contracts.

This is a partial implementation, not a conformance-certified consumer. The bundled
agreements and human review records are fictional fixtures. See
[bundle scope](bundles/legal_sample/scope.md) for missing evidence and calculation limits.

> **Scope Note**: This repository focuses exclusively on the **OKF Consumer setup**. Ingestion/producer logic will be addressed in a separate project.

---

## Why OKF Over Conventional RAG for Legal Documents

Conventional RAG chops legal documents into isolated vector chunks, losing:
1. **Contract Structure**: Agreements, sections, clauses, and exhibits are flattened.
2. **Cross-References**: Clauses referencing definitions (e.g. "Confidential Information", "Fees") or addenda (e.g. DPA supercaps) are severed.
3. **Trust & Provenance**: Cannot distinguish attorney-reviewed clauses from AI drafts.
4. **Freshness**: Outdated or superseded terms pollute similarity search.

**OKF (Open Knowledge Format v0.2)** represents legal knowledge as a directory tree of Markdown files with YAML frontmatter:
- **Progressive Disclosure**: Agents navigate using `index.md` files at each level, loading only what is needed.
- **Trust Tiers**: `human-reviewed`, `machine-confirmed`, and `unverified` are inferred from frontmatter actor signals.
- **Relational Links**: Standard Markdown links (`[Fees](/definitions/fees.md)`) create explicit, traversable graph edges.
- **Attested Computations**: Deterministic formulas (e.g., liability caps, cure periods) are evaluated mathematically rather than guessed.

---

## Architecture

```
langgraph-okf/
├── bundles/
│   └── legal_sample/                 # Fictional OKF demonstration bundle
│       ├── index.md                  # Root progressive disclosure index
│       ├── log.md                    # Bundle update history (§3.1 & §9)
│       ├── definitions/              # Legal definition concepts
│       ├── contracts/                # Agreements & Addenda
│       │   ├── msa/                  # Master Services Agreement & Clauses
│       │   ├── dpa/                  # Data Processing Addendum (2x Supercap)
│       │   └── sla/                  # Service Level Agreement
│       └── computations/             # Attested Computations (Liability, Notice)
├── src/
│   └── langgraph_okf/                # OKF v0.2 Consumer Core
│       │── models.py             # Pydantic models for Concept, Frontmatter, TrustTier
│       │── parser.py             # Permissive YAML+Markdown parser (§4 & §11)
│       │── bundle.py             # Bundle reader, index traversal, link resolution
│       │── trust.py              # Trust tier evaluator & freshness checker
│       ├── agent/                    # LangGraph Workflow Layer
│       │   ├── state.py              # LegalDiscoveryState schema
│       │   ├── llm.py                # OpenRouter ChatOpenAI factory with custom headers
│       │   ├── tools.py              # Attested computation execution tools
│       │   ├── nodes/                # Individual Node Files
│       │   │   ├── plan.py           # Planning & root index evaluation
│       │   │   ├── navigate.py       # Progressive disclosure index traversal
│       │   │   ├── inspect.py        # Concept inspection & trust evaluation
│       │   │   ├── expand.py         # Relational link graph expansion
│       │   │   ├── compute.py        # Deterministic Attested Computation execution
│       │   │   └── synthesize.py     # Grounded legal synthesis with citations
│       │   └── graph.py              # Compiled LangGraph workflow
│       ├── cli.py                    # Interactive query & inspection CLI
│       └── settings.py               # OpenRouter & OKF configuration settings
└── tests/
    ├── test_okf_parser.py            # Permissive parsing conformance tests
    ├── test_trust_evaluator.py       # Trust signal & lifecycle verification tests
    ├── test_bundle_traversal.py      # Progressive disclosure & link resolution tests
    └── test_agent_workflow.py        # End-to-end LangGraph agent discovery tests
```

---

## Setup & Quickstart

### Prerequisites
- Python >= 3.14
- [uv](https://docs.astral.sh/uv/)

### Installation
```bash
git clone https://github.com/ConceptCodes/langgraph-okf.git
cd langgraph-okf
uv sync
```

### Configuration
Create a `.env` file (optional, defaults to deterministic fallback if no API key is provided):
```ini
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemini-2.5-flash
```

---

## Running the CLI

### 1. Run a Legal Discovery Query
```bash
uv run langgraph-okf query 'What is the liability cap under the MSA, what exceptions apply, and how does a data breach affect it with $100,000 in fees?'
```

### 2. Inspect a Concept Document
```bash
uv run langgraph-okf inspect contracts/msa/clauses/limitation_of_liability
```

### 3. List All Concepts in the Legal Bundle
```bash
uv run langgraph-okf list
```

---

## Running Tests

```bash
uv run pytest -v
uv run ruff check src tests
```

Tests force offline mode and use the sample bundle, regardless of local `.env` credentials.

## Consumer behavior and limits

The graph uses [LangGraph runtime context](https://docs.langchain.com/oss/python/langgraph/graph-api#runtime-context).
Every node accepts `Runtime[Context]`. Each invocation supplies one bundle instance,
an optional chat model (`None` means offline), and fixed trust/traversal policy.
Nodes do not read global settings. Query progress and results remain in graph state.

```python
from langgraph_okf.agent import Context, build_legal_discovery_graph
from langgraph_okf.bundle import OKFBundle

graph = build_legal_discovery_graph()
context = Context(bundle=OKFBundle("bundles/legal_sample"), max_traversal_depth=3)
result = graph.invoke(
    {"query": "What is the standard liability cap with $100,000 in fees?"},
    context=context,
    config=context.invocation_config,
)
```

The CLI constructs `Context.from_settings(settings)` once per query. Python callers
must now pass context explicitly; `get_openrouter_llm` also requires an explicit
`Settings` argument. Supply `config=context.invocation_config` so LangGraph's step
limit accommodates the selected traversal depth. One compiled graph can be reused
with different contexts, including concurrent calls.

- Paths and symlinks must remain inside the bundle. Index navigation follows nested
  directories; relational expansion uses `MAX_TRAVERSAL_DEPTH` as a link-hop limit.
- `MIN_TRUST_TIER` selects evidence for this application's workflow. `STRICT_VALIDATION=true`
  additionally excludes stale/deprecated concepts. The underlying parser remains permissive;
  these settings are application policy, not OKF validity checks.
- Verification mappings and lists are supported. Trust is inferred from declared actors;
  identities and signatures are not authenticated.
- Only two registered sample computations run. They require explicit inputs and reject
  unknown executors and invalid numeric values. Query classification is heuristic, with
  assumptions shown in the output. Arbitrary bundle code is never executed.
- Calculation outputs are local results, not independently attested receipts.
- Offline output includes the retrieved text and citations; it is an evidence report,
  not a substitute for legal interpretation. Configuring an API key enables sending
  the query and retrieved evidence to OpenRouter for synthesis.
- The parser supports inline Markdown links, not the full CommonMark link grammar.
  Legacy v0.1 provenance conversion and external computation runtimes are not implemented.
- Run CLI examples from the repository root, or set `BUNDLE_PATH` to an absolute directory.
  The sample bundle is not installed as package data.
