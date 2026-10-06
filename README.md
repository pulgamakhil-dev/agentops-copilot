# AgentOps Copilot

**Production-oriented Agentic AI system for data operations, incident investigation, and controlled remediation.**

AgentOps Copilot is a multi-agent system I built to investigate data pipeline failures, retrieve relevant operational knowledge, and safely coordinate remediation actions.

The main idea behind the project is simple: an LLM can help investigate an incident and recommend what to do, but it should not have unrestricted permission to make infrastructure changes.

Operational actions therefore go through deterministic authorization, human approval, execution, persistence, and auditing outside the LLM.

**What it does**

* Investigates failed data pipelines using runtime evidence.
* Routes requests to specialized agents instead of giving one agent access to every tool.
* Uses FAISS-based RAG to retrieve relevant operational runbooks.
* Combines monitoring evidence and runbook context during incident investigation.
* Keeps investigation workflows read-only.
* Separates recommendations from operational actions.
* Requires explicit action intent before creating an approval request.
* Requires human approval for controlled actions.
* Enforces RBAC in application code rather than through prompts.
* Prevents execution while an approval is pending or rejected.
* Tracks requester, reviewer, and executor identities separately.
* Persists approvals, executions, and audit events.
* Uses a simulated executor by default so the complete workflow can be tested safely.
* Includes automated tests, evaluation datasets, Docker support, migrations, and GitHub Actions CI.

**Architecture**

```text
                         ┌───────────────────────┐
                         │      Client / API     │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │      FastAPI Layer    │
                         │ Auth / Request Context│
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │      Supervisor       │
                         │ Intent Classification │
                         │     Agent Routing     │
                         └───────────┬───────────┘
                                     │
             ┌───────────────────────┼───────────────────────┐
             │                       │                       │
             ▼                       ▼                       ▼
      ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
      │ Monitoring  │         │     SQL     │         │     RAG     │
      │    Agent    │         │    Agent    │         │    Agent    │
      └──────┬──────┘         └──────┬──────┘         └──────┬──────┘
             │                       │                       │
             └──────────────┬────────┴───────────────────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │ Investigation Agent │
                  │ Evidence Synthesis  │
                  │ Read-Only Boundary  │
                  └──────────┬──────────┘
                             │
                             ▼
                       Recommendation
                             │
                   Explicit action request
                             │
                             ▼
                    ┌────────────────┐
                    │  Action Agent  │
                    └───────┬────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │ Approval Request    │
                  │       PENDING       │
                  └──────────┬──────────┘
                             │
                       Human Reviewer
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Authorization / RBAC│
                  └──────────┬──────────┘
                             │
                          APPROVED
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Execution Service   │
                  │ Executor Abstraction│
                  └──────────┬──────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
             Simulated Executor   Airflow Executor
                                      │
                                      ▼
                              External Platform

              Approval + Execution + Audit State
                             │
                             ▼
                    SQLite / Persistence
```

**Agents**

* **Supervisor** — classifies requests and routes them to the appropriate agent or workflow.
* **Monitoring Agent** — retrieves pipeline status, failed runs, error information, and operational evidence.
* **SQL Agent** — provides controlled access to structured operational data.
* **RAG Agent** — retrieves relevant troubleshooting information from indexed runbooks.
* **Investigation Agent** — combines monitoring evidence with runbook knowledge and produces a read-only incident assessment.
* **Action Agent** — handles explicit operational action requests and creates approval requests when required.

Keeping these responsibilities separate makes the system easier to test and prevents a general-purpose LLM from receiving unnecessary operational access.

**Incident workflow**

A typical investigation looks like this:

```text
Incident Query
     │
     ▼
Supervisor
     │
     ▼
Investigation Agent
     │
     ├── Monitoring Evidence
     │
     └── Runbook Retrieval
     │
     ▼
Read-Only Recommendation
```

The investigation stops at a recommendation.

For example:

```text
Investigate why customer_ingestion failed.
```

does not create or execute an operational action.

A separate explicit request such as:

```text
Request a rerun of customer_ingestion.
```

can enter the controlled action workflow.

**Approval and execution**

Operational actions follow a deterministic lifecycle:

```text
ACTION REQUESTED
       │
       ▼
PENDING APPROVAL
       │
       ├──────────────► REJECTED
       │
       ▼
    APPROVED
       │
       ▼
EXECUTION STARTED
       │
       ▼
EXECUTION COMPLETED / FAILED
```

Important controls include:

* The requester cannot silently turn an investigation into an execution.
* Approval state is stored independently of the LLM conversation.
* Reviewers must have the required permission.
* Requester and reviewer separation is enforced.
* Execution is blocked unless the approval is in the required state.
* Authorization decisions happen in application code.
* Execution results are persisted.
* Security-sensitive lifecycle events are written to the audit trail.

**RBAC and identity**

Development roles include:

* `viewer`
* `operator`
* `approver`
* `admin`

Permissions control capabilities such as:

* Requesting an operational action.
* Approving an action.
* Executing an approved operation.
* Viewing execution history.
* Accessing audit history.

For local development, identity is passed through:

```text
X-User-ID
X-Username
X-User-Roles
```

This is intentionally a development mechanism.

A production deployment should replace these headers with verified enterprise identity such as OIDC/OAuth2 and signed JWT validation at the application or gateway boundary.

**RAG and runbooks**

Operational runbooks are stored in:

```text
data/runbooks/
```

Current examples cover:

* API timeout remediation.
* Schema drift handling.
* Spark memory troubleshooting.

The retrieval flow is:

```text
Runbooks
   │
   ▼
Document Loading
   │
   ▼
Chunking
   │
   ▼
Embeddings
   │
   ▼
FAISS
   │
   ▼
Semantic Retrieval
   │
   ▼
Investigation Context
```

The FAISS index is generated at runtime and intentionally excluded from source control.

Retrieved runbook content is treated as evidence for investigation rather than as executable instructions.

**Execution model**

Execution is hidden behind an executor abstraction.

Current implementations include:

* `SimulatedExecutor`
* `AirflowExecutor`

The default development configuration uses:

```text
EXECUTOR_PROVIDER=simulated
```

This lets the complete authorization and execution lifecycle run without changing production infrastructure.

A successful simulated execution can therefore validate:

* Approval enforcement.
* RBAC.
* Requester/reviewer separation.
* Executor authorization.
* Execution persistence.
* Audit events.

without requiring production credentials.

**Audit trail**

The application records lifecycle events such as:

* `ACTION_REQUESTED`
* `APPROVAL_GRANTED`
* `EXECUTION_STARTED`
* `EXECUTION_COMPLETED`

Audit records can include:

* Actor.
* Action.
* Resource.
* Approval ID.
* Execution ID.
* Status or outcome.
* Timestamp.

This provides traceability from the original action request through approval and execution.

**Tech stack**

* Python
* FastAPI
* LangGraph
* LangChain
* Ollama
* Qwen 2.5
* FAISS
* Sentence Transformers
* SQLite
* Alembic
* Pydantic
* Pytest
* Docker
* Docker Compose
* GitHub Actions

**Project structure**

```text
agentops_copilot/
│
├── app/
│   ├── agents/
│   │   ├── supervisor.py
│   │   ├── monitoring_agent.py
│   │   ├── sql_agent.py
│   │   ├── rag_agent.py
│   │   ├── investigation_agent.py
│   │   └── action_agent.py
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
│   └── pipeline_runs.csv
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

**Running locally**

Prerequisites:

* Python
* Docker Desktop
* Docker Compose
* Ollama

The default local model is:

```text
qwen2.5:3b
```

Pull it with:

```bash
ollama pull qwen2.5:3b
```

Create the environment file.

Windows CMD:

```cmd
copy .env.example .env
```

Build the runbook index:

```cmd
python -m app.rag.ingest
```

Seed the local pipeline data:

```cmd
python -m app.db.seed_data
```

Start the application:

```cmd
docker compose up -d --build
```

The API is exposed locally on port `8000`.

Check readiness with:

```text
GET /health/ready
```

**Testing**

The project currently has **80 automated tests** covering both unit and integration behavior.

Coverage includes:

* Authentication and authorization.
* Invalid role rejection.
* Requester/reviewer separation.
* Supervisor routing.
* Action-intent detection.
* Investigation behavior.
* RAG integration.
* Read-only investigation guarantees.
* Approval persistence.
* Execution authorization.
* Execution-before-approval blocking.
* Execution history.
* Audit lifecycle.
* Audit filtering and pagination.
* Cross-agent workflows.

Run the suite with:

```cmd
python -m pytest tests/ -q
```

Current validated result:

```text
80 passed
```

**Evaluation**

The repository also includes evaluation datasets and runners for:

* Agent routing.
* RAG retrieval.
* Groundedness.
* Judge-based groundedness checks.
* Tool-health enrichment.

Generated evaluation results are treated as runtime artifacts and are not committed to the repository.

**Validated end-to-end workflow**

The complete controlled-remediation path has been exercised through the Docker API:

```text
Incident
   │
   ▼
Investigation
   │
   ▼
Runbook + Monitoring Evidence
   │
   ▼
Recommendation
   │
   ▼
Explicit Action Request
   │
   ▼
Pending Approval
   │
   ├── Early execution attempt → HTTP 403
   │
   ▼
Separate Reviewer Approval
   │
   ▼
Authorized Execution
   │
   ▼
Simulated Executor
   │
   ▼
Execution Record
   │
   ▼
Audit Trail
```

During validation, an execution attempt while the approval was still `pending` returned HTTP `403`.

After a separate authorized reviewer approved the request, the same action passed through the simulated executor and the execution was persisted successfully.

That behavior is important to the project: the safety boundary is enforced by application logic rather than relying on the LLM to follow an instruction.

**Current limitations / production hardening**

This repository demonstrates the application architecture and control model. It is not presented as a fully deployed enterprise operations platform.

For a production deployment, I would additionally add:

* Enterprise OIDC/OAuth2 identity integration.
* Signed JWT validation.
* Managed relational database infrastructure.
* Centralized secret management.
* TLS termination.
* Network-level service isolation.
* Centralized metrics, logs, and alerting.
* Distributed tracing.
* Rate limiting.
* Managed vector infrastructure where required.
* Scoped production Airflow service identities.
* Backup and disaster-recovery policies.
* Centralized immutable audit storage.
* Environment-specific policy enforcement.

The local identity headers and simulated executor are deliberate development boundaries. They make it possible to test the complete governed workflow without providing an LLM or local development environment with production infrastructure access.

**Why I built it this way**

A lot of agent demos focus on whether the model can call a tool successfully.

For operational systems, I think the harder problem is deciding what the model should be allowed to do after it has reasoned about an incident.

This project therefore keeps several boundaries explicit:

* Reasoning is not authorization.
* A recommendation is not an action.
* Investigation should remain read-only.
* Sensitive operations need deterministic controls.
* Human approval should exist outside model reasoning.
* Operational state should not depend on conversation memory.
* Every important action should be traceable.
* Infrastructure integrations should be replaceable without redesigning the agent workflow.

The goal is to explore how agentic AI can participate in real operational workflows while keeping execution controlled, testable, and auditable.
