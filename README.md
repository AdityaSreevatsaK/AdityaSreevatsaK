<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/signal-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/signal-light.svg">
    <img alt="Aditya Sreevatsa K, Senior AI Engineer. Designing, building and evaluating intelligent systems." src="assets/signal-light.svg" width="100%">
  </picture>
</div>

<p align="center">
  <a href="#selected-engineering-work">Selected work</a> ·
  <a href="#technical-decisions-in-practice">Engineering decisions</a> ·
  <a href="#open-source-collaboration">Open source</a> ·
  <a href="https://www.linkedin.com/in/adityasreevatsak/">LinkedIn</a> ·
  <a href="mailto:krishnan.adityasreevatsa@gmail.com">Contact</a>
</p>

## Hello, I'm Aditya.

I'm a **Senior AI Engineer**, building enterprise AI applications and the engineering foundations behind them. My work combines **agent orchestration, RAG, Text-to-SQL, evaluation, back-end architecture and technical delivery**.

I've worked across enterprise analytics, energy and banking, from production APIs and ML pipelines to multi-agent systems. I care equally about what a system can do and how teams can test, extend and operate it.

### Selected engineering work

| | What I built and why it matters |
| :-- | :-- |
| **[AET · Agentic Engineering Toolkit](https://github.com/AdityaSreevatsaK/agentic-engineering-toolkit)** | A local-first scaffolder for agent applications. It produces configurable LangGraph, AWS Strands and LlamaIndex project starters, with offline mock validation and opt-in model integrations. **Engineering prototype, not production-certified.** |
| **[AEA · Agent Engineering Accelerator](https://github.com/AdityaSreevatsaK/agent-engineering-accelerator)** | An in-progress effort to make agent behaviour testable through evaluation, regression comparisons and quality checks. Public-facing documentation is being rebuilt. |
| **[RAG Foundry](https://github.com/AdityaSreevatsaK/RAG-Foundry)** | Experiments and practical implementations of retrieval-augmented question answering and grounded responses. |
| **[Taiyou's Personal Library](https://github.com/AdityaSreevatsaK/Taiyous-Personal-Library)** | An installable web reader that demonstrates front-end, API, private storage, authentication, offline and deployment engineering. The code is public; reading data remains private. |

### How I think about engineering

| **01 · Architecture** | **02 · Retrieval & tools** | **03 · Evaluation** | **04 · Delivery** |
| :-- | :-- | :-- | :-- |
| Clear boundaries and interfaces | Grounded outputs and explicit dependencies | Reproducible tests and honest evidence | Maintainability, documentation and operational care |

One example of that philosophy is keeping [AET's project scaffolding](https://github.com/AdityaSreevatsaK/agentic-engineering-toolkit) separate from [AEA's evaluation responsibilities](https://github.com/AdityaSreevatsaK/agent-engineering-accelerator). Their responsibilities should remain independently understandable and adoptable.

### Technical decisions in practice

- **Reusability before complexity.** Agent starters should expose clear contracts, configurable providers and understandable application boundaries, not require repeated setup in each new project.
- **Testable without paid inference.** AET's [offline verification matrix](https://github.com/AdityaSreevatsaK/agentic-engineering-toolkit/blob/master/docs/testing/comprehensive-matrix-2026-11-04.md) checks generated templates on Windows and Linux. It is evidence of repeatable checks, not a claim of production readiness or live model performance.
- **Privacy by design.** My [personal library application](https://github.com/AdityaSreevatsaK/Taiyous-Personal-Library) separates public application code from private reading data, with offline access and deliberate cloud-storage boundaries.

### Open-source collaboration

I contribute targeted reliability and compatibility fixes to established open-source projects. These are **selected upstream pull requests**, not activity from my own forks.

Status and dates come from the public GitHub pull-request API. The [scheduled updater](.github/workflows/profile-upstream.yml) will refresh only the reviewed entries after the profile design is approved for the default branch.

<!-- BEGIN:PROFILE_UPSTREAM -->
| Upstream project | Contribution | Status | Date (UTC) |
| :-- | :-- | :-- | :-- |
| rossjrw | [Recover stalled game states (#4934)](https://github.com/rossjrw/rossjrw/pull/4934) | **Merged** | 11 Nov 2026 |
| httpx2 | [Retry failed connection-pool closures (#1330)](https://github.com/pydantic/httpx2/pull/1330) | Open | 12 Nov 2026 |
| httpx2 | [Support an alternative authentication header (#1332)](https://github.com/pydantic/httpx2/pull/1332) | Open | 12 Nov 2026 |
| logfire | [Fix Windows CLI file locking (#2803)](https://github.com/pydantic/logfire/pull/2803) | Open | 12 Nov 2026 |
<!-- END:PROFILE_UPSTREAM -->

### Explore the engineering evidence

For more implementation detail, see the [AET architecture deep dive](https://github.com/AdityaSreevatsaK/agentic-engineering-toolkit/blob/master/PROJECT_DEEP_DIVE.md), [agent scaffolding tests](https://github.com/AdityaSreevatsaK/agentic-engineering-toolkit/tree/master/tests), and [RAG Foundry examples](https://github.com/AdityaSreevatsaK/RAG-Foundry).

<details>
<summary><strong>More about me: education, recognition and technology</strong></summary>

**Education:** M.Tech in Data Science, ML & AI, PES University, **9.9/10 GPA, first in cohort** (2026); B.E. in Mechanical Engineering, CMR Institute of Technology (2021).

**Recognition:** Infosys Gracias Awards; EY User Appreciation Award; Accenture ACE Award and Top Performer recognition; PES University merit scholarship.

**AI & agents:** Python, LangGraph, AWS Strands, LangChain, LlamaIndex, RAG, LLM evaluation, PyTorch, TensorFlow.  
**Software & data:** Java, FastAPI, Spring Boot, SQL, Kafka, PySpark, Neo4j, PostgreSQL, Pinecone.  
**Platforms:** AWS, Azure, Docker, Kubernetes, GitHub Actions, CI/CD.

**More repositories:** [NLP Navigator](https://github.com/AdityaSreevatsaK/NLP-Navigator) · [PySpark Pipeline](https://github.com/AdityaSreevatsaK/PySpark-Pipeline) · [The Neural Nexus](https://github.com/AdityaSreevatsaK/The-Neural-Nexus).
</details>

---

<p align="center"><sub>Thoughtful architecture. Testable systems. Useful software.</sub></p>
