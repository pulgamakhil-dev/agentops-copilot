\# AgentOps Copilot



\*\*Production-oriented Agentic AI control plane for data operations, incident investigation, and governed remediation.\*\*



AgentOps Copilot is a multi-agent operational assistant designed to investigate data pipeline failures, correlate runtime evidence with operational runbooks, recommend remediation steps, and coordinate controlled actions through human approval and RBAC-enforced execution.



The system is intentionally designed around a core production principle:



> \*\*LLMs can investigate and recommend. Operational changes must cross deterministic authorization and approval boundaries.\*\*



Rather than exposing infrastructure directly to an autonomous agent, AgentOps Copilot separates reasoning, authorization, approval, execution, persistence, and auditing into independent layers.



\---



\## Why This Exists



Operational incidents rarely live in one system.



An engineer investigating a failed data pipeline may need to:



1\. Inspect recent pipeline runs.

2\. Identify the failed execution and error.

3\. Query operational metadata.

4\. Search runbooks for known remediation procedures.

5\. Correlate evidence across multiple sources.

6\. Determine whether remediation is appropriate.

7\. Request an operational action.

8\. Obtain approval from an authorized reviewer.

9\. Execute the approved action.

10\. Preserve an audit trail.



AgentOps Copilot models this workflow as a governed multi-agent system instead of allowing a single LLM to reason and execute infrastructure actions directly.



\---



\## Architecture



```text

&#x20;                        ┌───────────────────────┐

&#x20;                        │      Client / API     │

&#x20;                        └───────────┬───────────┘

&#x20;                                    │

&#x20;                                    ▼

&#x20;                        ┌───────────────────────┐

&#x20;                        │      FastAPI Layer    │

&#x20;                        │ Auth / Request Context│

&#x20;                        └───────────┬───────────┘

&#x20;                                    │

&#x20;                                    ▼

&#x20;                        ┌───────────────────────┐

&#x20;                        │      Supervisor       │

&#x20;                        │ Intent Classification │

&#x20;                        │   Agent Routing       │

&#x20;                        └───────────┬───────────┘

&#x20;                                    │

&#x20;            ┌───────────────────────┼───────────────────────┐

&#x20;            │                       │                       │

&#x20;            ▼                       ▼                       ▼

&#x20;     ┌─────────────┐         ┌─────────────┐        ┌─────────────┐

&#x20;     │ Monitoring  │         │     SQL     │        │     RAG     │

&#x20;     │    Agent    │         │    Agent    │        │    Agent    │

&#x20;     └──────┬──────┘         └──────┬──────┘        └──────┬──────┘

&#x20;            │                       │                       │

&#x20;            │                       │                FAISS / Runbooks

&#x20;            │                       │                       │

&#x20;            └──────────────┬────────┴───────────────────────┘

&#x20;                           │

&#x20;                           ▼

&#x20;                 ┌─────────────────────┐

&#x20;                 │ Investigation Agent │

&#x20;                 │ Evidence Synthesis  │

&#x20;                 │ Read-Only Boundary  │

&#x20;                 └──────────┬──────────┘

&#x20;                            │

&#x20;                            ▼

&#x20;                      Recommendation

&#x20;                            │

&#x20;                 Explicit action request

&#x20;                            │

&#x20;                            ▼

&#x20;                   ┌────────────────┐

&#x20;                   │  Action Agent  │

&#x20;                   └───────┬────────┘

&#x20;                           │

&#x20;                           ▼

&#x20;                 ┌─────────────────────┐

&#x20;                 │ Approval Request    │

&#x20;                 │     PENDING         │

&#x20;                 └──────────┬──────────┘

&#x20;                            │

&#x20;                     Human Reviewer

&#x20;                            │

&#x20;                            ▼

&#x20;                 ┌─────────────────────┐

&#x20;                 │ Authorization / RBAC│

&#x20;                 └──────────┬──────────┘

&#x20;                            │

&#x20;                        APPROVED

&#x20;                            │

&#x20;                            ▼

&#x20;                 ┌─────────────────────┐

&#x20;                 │ Execution Service   │

&#x20;                 │ Executor Abstraction│

&#x20;                 └──────────┬──────────┘

&#x20;                            │

&#x20;                  ┌─────────┴─────────┐

&#x20;                  ▼                   ▼

&#x20;            Simulated Executor   Airflow Executor

&#x20;                                     │

&#x20;                                     ▼

&#x20;                             External Platform



&#x20;         Approval + Execution + Audit State

&#x20;                      │

&#x20;                      ▼

&#x20;               SQLite / Persistence

```



\---



\## Agent Responsibilities



\### Supervisor



The Supervisor acts as the orchestration layer.



It classifies incoming operational requests and routes them to the appropriate specialized capability instead of exposing every tool to a single general-purpose agent.



Responsibilities include:



\* intent classification

\* agent routing

\* investigation routing

\* action-request detection

\* separation of informational and operational workflows



This reduces unnecessary tool exposure and makes agent behavior easier to test and reason about.



\### Monitoring Agent



Retrieves operational evidence about pipeline execution.



Typical responsibilities:



\* inspect recent pipeline runs

\* identify failures

\* surface error codes and failure context

\* retrieve pipeline status information

\* provide evidence to downstream investigation



Monitoring logic is kept separate from final incident reasoning.



\### SQL Agent



Provides structured access to operational data through controlled SQL tooling.



The SQL capability is isolated behind dedicated tools rather than allowing arbitrary database behavior directly from the supervisor.



\### RAG Agent



Retrieves operational knowledge from runbooks.



Current runbook examples include:



\* API timeout remediation

\* schema drift handling

\* Spark memory troubleshooting



Runbooks are embedded and indexed using FAISS.



The RAG layer provides evidence to the reasoning workflow rather than treating retrieved documents as executable instructions.



\### Investigation Agent



Combines runtime evidence with relevant runbook knowledge.



The investigation path is deliberately \*\*read-only\*\*.



It can:



\* inspect monitoring evidence

\* retrieve runbook context

\* correlate incident information

\* identify likely causes

\* recommend remediation



It cannot approve or execute infrastructure changes.



The optimized investigation path performs direct runbook retrieval followed by a consolidated LLM synthesis step, avoiding unnecessary nested agent loops during incident analysis.



\### Action Agent



Handles explicit operational action requests.



An investigation recommendation does not automatically become an action.



The user must explicitly request the operational change before the system creates an approval request.



Example:



```text

Investigate why customer\_ingestion failed.

```



remains read-only.



Whereas:



```text

Request a rerun of customer\_ingestion.

```



enters the controlled action workflow.



\---



\## Governed Action Lifecycle



Operational actions move through an explicit state transition:



```text

REQUEST

&#x20;  │

&#x20;  ▼

PENDING APPROVAL

&#x20;  │

&#x20;  ├──────────────► REJECTED

&#x20;  │

&#x20;  ▼

APPROVED

&#x20;  │

&#x20;  ▼

EXECUTION STARTED

&#x20;  │

&#x20;  ▼

EXECUTION COMPLETED / FAILED

```



Execution is rejected unless the associated approval is in the required state.



This control exists outside LLM reasoning.



The model therefore cannot bypass the approval workflow by generating different text or attempting to invoke an execution path directly.



\---



\## Human-in-the-Loop Approval



AgentOps Copilot implements separation between:



\* requester

\* reviewer

\* executor



Approval requests persist independently of the conversation that created them.



A reviewer must possess the appropriate permission before making an approval decision.



The approval layer also protects against identity spoofing and requester self-approval.



This creates a deterministic control boundary between AI-generated recommendations and operational execution.



\---



\## RBAC



Authorization is enforced by application code rather than model prompts.



Supported development roles include:



```text

viewer

operator

approver

admin

```



Permissions govern capabilities such as:



\* requesting actions

\* approving actions

\* executing approved operations

\* viewing execution history

\* accessing audit history



The current development environment uses identity headers:



```text

X-User-ID

X-Username

X-User-Roles

```



These headers are intended for local development and testing.



A production deployment should replace this mechanism with verified enterprise identity such as OIDC/OAuth2/JWT validation at the application or gateway boundary.



\---



\## Execution Boundary



Execution is abstracted behind an executor interface.



Current implementations include:



```text

SimulatedExecutor

AirflowExecutor

```



The default development configuration uses:



```text

EXECUTOR\_PROVIDER=simulated

```



A successful execution therefore confirms the complete authorization and execution workflow without changing production infrastructure.



Example simulated result:



```json

{

&#x20; "success": true,

&#x20; "action\_name": "rerun\_pipeline",

&#x20; "resource\_name": "customer\_ingestion",

&#x20; "status": "simulated",

&#x20; "message": "Pipeline rerun simulated successfully for customer\_ingestion. No production action was executed."

}

```



This boundary makes it possible to test agent behavior, approval logic, RBAC, persistence, and auditability without giving the development environment production credentials.



\---



\## Auditability



Security-sensitive lifecycle transitions generate persistent audit events.



Examples include:



```text

ACTION\_REQUESTED

APPROVAL\_GRANTED

EXECUTION\_STARTED

EXECUTION\_COMPLETED

```



Audit records capture relevant context such as:



\* actor

\* action

\* resource

\* approval identifier

\* execution identifier

\* status/outcome

\* timestamp



Audit history can be filtered by attributes including actor, event type, approval ID, execution ID, and resource.



This provides traceability across the complete operational lifecycle.



\---



\## Persistence



SQLite is used for local persistence.



Persistent domain state includes:



\* pipeline execution information

\* approval requests

\* execution records

\* audit events

\* authenticated execution identity



Database schema evolution is managed through Alembic migrations.



The persistence layer is intentionally separated from agent reasoning so operational state does not depend on LLM conversation memory.



\---



\## RAG Pipeline



Operational documentation is stored under:



```text

data/runbooks/

```



Current examples:



```text

api\_timeout.md

schema\_drift.md

spark\_memory.md

```



The ingestion pipeline:



```text

Runbooks

&#x20;  │

&#x20;  ▼

Document Loading

&#x20;  │

&#x20;  ▼

Chunking

&#x20;  │

&#x20;  ▼

Embedding

&#x20;  │

&#x20;  ▼

FAISS Index

&#x20;  │

&#x20;  ▼

Semantic Retrieval

&#x20;  │

&#x20;  ▼

Investigation Context

```



Generated FAISS artifacts are intentionally excluded from source control and can be rebuilt from the source runbooks.



\---



\## Evaluation



The repository includes an evaluation harness rather than relying exclusively on manual prompt testing.



Evaluation datasets cover areas including:



```text

evals/datasets/

├── action\_safety\_cases.json

├── rag\_cases.json

├── rag\_single\_test.json

└── routing\_cases.json

```



Evaluation runners cover:



\* routing behavior

\* RAG quality

\* groundedness

\* judge-based groundedness review

\* tool-health enrichment



Generated evaluation outputs are excluded from Git because they are runtime artifacts.



This keeps evaluation methodology and reproducible datasets versioned without accumulating generated result files in the repository.



\---



\## Testing Strategy



The automated suite currently contains \*\*80 tests\*\* covering unit and integration behavior.



Major coverage areas include:



\### Security



\* authentication requirements

\* invalid role rejection

\* permission enforcement

\* reviewer identity protection

\* requester/reviewer separation

\* action authorization

\* audit endpoint authorization



\### Agent Behavior



\* supervisor routing

\* action-intent detection

\* investigation routing

\* monitoring evidence retrieval

\* RAG integration

\* read-only investigation guarantees



\### Approval \& Execution



\* approval persistence

\* approval separation

\* execution authorization

\* execution history

\* authenticated executor identity

\* blocked execution before approval



\### Audit Lifecycle



\* action-request events

\* approval events

\* execution-start events

\* execution-completion events

\* rejected approvals

\* failed executions

\* audit filtering and pagination



\### End-to-End Workflow



Integration tests validate the controlled path from incident investigation through authorized execution.



Run the suite with:



```bash

python -m pytest tests/ -q

```



Current validated result:



```text

80 passed

```



\---



\## Validated End-to-End Scenario



The project has been exercised through the live Docker API using the following workflow:



```text

Incident Query

&#x20;    │

&#x20;    ▼

Supervisor

&#x20;    │

&#x20;    ▼

Investigation Agent

&#x20;    │

&#x20;    ├── Monitoring Evidence

&#x20;    │

&#x20;    └── Runbook Retrieval

&#x20;    │

&#x20;    ▼

Read-Only Recommendation

&#x20;    │

&#x20;    ▼

Explicit Action Request

&#x20;    │

&#x20;    ▼

Pending Approval

&#x20;    │

&#x20;    ├── Attempted early execution → HTTP 403

&#x20;    │

&#x20;    ▼

Separate Reviewer Approval

&#x20;    │

&#x20;    ▼

Authorized Execution

&#x20;    │

&#x20;    ▼

Simulated Executor

&#x20;    │

&#x20;    ▼

Execution Record

&#x20;    │

&#x20;    ▼

Audit Trail

```



The validation specifically confirmed that execution attempted while an approval remained `pending` was rejected.



After approval by a separate authorized reviewer, the same action was successfully processed through the simulated executor and persisted to execution history.



\---



\## Technology Stack



| Area                | Technology              |

| ------------------- | ----------------------- |

| API                 | FastAPI                 |

| Agent orchestration | LangGraph               |

| LLM integration     | LangChain               |

| Local LLM           | Ollama / Qwen 2.5       |

| Retrieval           | FAISS                   |

| Embeddings          | Sentence Transformers   |

| Database            | SQLite                  |

| Migrations          | Alembic                 |

| Validation          | Pydantic                |

| Testing             | Pytest                  |

| Containerization    | Docker / Docker Compose |

| CI                  | GitHub Actions          |

| Language            | Python                  |



\---



\## Repository Structure



```text

agentops\_copilot/

│

├── app/

│   ├── agents/

│   │   ├── supervisor.py

│   │   ├── monitoring\_agent.py

│   │   ├── sql\_agent.py

│   │   ├── rag\_agent.py

│   │   ├── investigation\_agent.py

│   │   └── action\_agent.py

│   │

│   ├── api/

│   │   ├── agent.py

│   │   ├── approvals.py

│   │   ├── audit.py

│   │   ├── executions.py

│   │   ├── health.py

│   │   └── monitoring.py

│   │

│   ├── core/

│   │   ├── auth.py

│   │   ├── authorization.py

│   │   ├── permissions.py

│   │   ├── guardrails.py

│   │   ├── security.py

│   │   └── config.py

│   │

│   ├── executors/

│   │   ├── base.py

│   │   ├── factory.py

│   │   ├── simulated.py

│   │   └── airflow.py

│   │

│   ├── rag/

│   │   ├── ingest.py

│   │   └── retriever.py

│   │

│   ├── services/

│   ├── tools/

│   ├── db/

│   ├── models/

│   └── main.py

│

├── data/

│   ├── runbooks/

│   └── pipeline\_runs.csv

│

├── evals/

│   ├── datasets/

│   └── runners/

│

├── migrations/

├── tests/

│   ├── unit/

│   └── integration/

│

├── .github/workflows/

├── Dockerfile

├── docker-compose.yml

├── alembic.ini

├── requirements.txt

└── README.md

```



\---



\## Local Development



\### Prerequisites



\* Python

\* Docker Desktop

\* Docker Compose

\* Ollama



The default model configuration uses:



```text

qwen2.5:3b

```



Pull the model:



```bash

ollama pull qwen2.5:3b

```



Create the local environment file:



```bash

cp .env.example .env

```



On Windows CMD:



```cmd

copy .env.example .env

```



Build the RAG index:



```bash

python -m app.rag.ingest

```



Seed local pipeline data:



```bash

python -m app.db.seed\_data

```



Start the application:



```bash

docker compose up -d --build

```



Verify readiness:



```text

GET /health/ready

```



The API is exposed locally on port `8000`.



FastAPI's generated API documentation is available through the application while it is running.



\---



\## Docker Runtime



The Docker environment persists application state using a mounted storage volume.



The application container connects to the host Ollama service using:



```text

http://host.docker.internal:11434

```



Runtime-generated state such as databases, logs, vector indexes, caches, and local environment secrets is excluded from source control.



\---



\## Security Model



The project follows several defensive design principles:



\*\*Least privilege\*\*

Agents receive specialized responsibilities rather than unrestricted operational access.



\*\*Read-only investigation\*\*

Incident reasoning cannot silently become infrastructure execution.



\*\*Explicit action intent\*\*

Recommendations and questions do not create operational actions.



\*\*Human approval\*\*

Sensitive operations require an independent approval transition.



\*\*Separation of duties\*\*

Requester, reviewer, and executor identities are independently tracked.



\*\*Deterministic authorization\*\*

RBAC decisions occur in application code rather than LLM prompts.



\*\*Execution gating\*\*

Pending or rejected actions cannot be executed.



\*\*Persistent auditing\*\*

Security-sensitive lifecycle transitions are recorded outside the conversation.



\*\*Replaceable execution providers\*\*

Infrastructure integrations sit behind executor abstractions.



\---



\## Production Hardening



This repository demonstrates the application architecture and control model. A production deployment would additionally require environment-specific infrastructure controls such as:



\* enterprise OIDC/OAuth2 identity integration

\* signed JWT validation

\* managed relational database

\* centralized secret management

\* TLS termination

\* network-level service isolation

\* production observability and alerting

\* distributed tracing

\* rate limiting

\* managed vector infrastructure where required

\* production Airflow credentials and scoped service identities

\* backup and disaster-recovery policies

\* centralized immutable audit storage

\* deployment-specific policy enforcement



The local header-based authentication and simulated executor are deliberate development boundaries and should not be interpreted as production identity or infrastructure configuration.



\---



\## Design Principles



AgentOps Copilot is built around five principles:



1\. \*\*Reasoning is not authorization.\*\*

2\. \*\*Recommendations are not actions.\*\*

3\. \*\*Operational execution requires deterministic controls.\*\*

4\. \*\*AI workflows must be observable, testable, and auditable.\*\*

5\. \*\*Infrastructure integrations should be replaceable without redesigning agent reasoning.\*\*



These boundaries allow agentic systems to participate in operational workflows without giving an LLM unrestricted control over production infrastructure.



\---



\## Current Status



Implemented and validated:



\* Multi-agent routing

\* Monitoring Agent

\* SQL Agent

\* RAG Agent

\* Investigation Agent

\* Action Agent

\* FAISS runbook retrieval

\* Explicit action-intent detection

\* Human-in-the-loop approval

\* RBAC

\* Requester/reviewer separation

\* Execution gating

\* Simulated execution

\* Airflow executor abstraction

\* Execution persistence

\* Audit lifecycle

\* Alembic migrations

\* Evaluation framework

\* Docker deployment

\* GitHub Actions CI

\* Unit and integration testing

\* End-to-end controlled remediation workflow



\*\*Automated test suite: 80 passing tests.\*\*



\---



\## Disclaimer



AgentOps Copilot is a portfolio/reference implementation demonstrating production-oriented patterns for governed Agentic AI operations.



The default executor is intentionally configured for simulation. No production infrastructure action is performed unless an environment is explicitly configured with an appropriate external executor and its required security controls.



