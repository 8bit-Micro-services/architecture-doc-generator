# SDLC workflow, roles, inputs/outputs and gates

Two-week Scrum sprints with quality gates. Each board column is an SDLC phase; each phase has an
accountable (A) and responsible (R) role, inputs, outputs, entry (gate-in) and exit (gate-out) criteria.
Process names align to ISO/IEC/IEEE 12207 (life-cycle processes), 29148 (requirements),
42010 (architecture description) and 29119 (testing).

```
Requirement Intake -> Refinement -> Design -> Development -> Integration/E2E Test -> UAT -> Release -> Operation/Retrospective
```
Failed gates send work back to Design or Development; retrospective output feeds Refinement.

## Phases
| # | Phase | A / R | Inputs | Outputs | Gate-in | Gate-out |
|---|---|---|---|---|---|---|
| 1 | Requirement Intake | Product Owner / Business Analyst | Stakeholder request, sample files | BRD, user journey, initial backlog | Clear business request | PO confirms value and scope |
| 2 | Refinement | Product Owner / Business Analyst | BRD, backlog | Prioritised backlog, acceptance criteria, test scenarios | Requirement confirmed | Stories meet Definition of Ready |
| 3 | Design | Solution Architect / Technical Lead | Approved stories, constraints | Architecture doc, ADRs, contracts, test strategy, threat model | Sprint backlog ready | Architect + TL approve; QA reviewed testability |
| 4 | Development | Technical Lead / Developer | Approved design, test cases | Code, unit tests, build artifact | Design gate passed | PR approved, CI green |
| 5 | Integration/E2E Test | QA Engineer / QA Engineer | CI build, test data | Test report, defects | Unit tests pass | No critical/high defects, E2E pass |
| 6 | UAT | Product Owner / QA Engineer | Staging, QA report | UAT sign-off | QA gate passed | PO accepts |
| 7 | Release | DevOps Engineer / DevOps Engineer | UAT sign-off, release notes | Deployment evidence, release tag, runbook | UAT passed | Smoke test passes, monitoring active |
| 8 | Operation/Retrospective | Scrum Master / Scrum Master | Metrics, incidents, feedback | Improvement backlog, incident report | Release completed | Lessons have owners |

## Roles
| Role | Responsibility |
|---|---|
| Product Owner | Business value, priority, acceptance; signs off requirements and UAT |
| Business Analyst | Requirements analysis, user stories, process flows |
| Scrum Master | Scrum facilitation, blocker removal, sprint readiness |
| Solution Architect | Architecture, integration, security design, ADRs |
| Technical Lead | Module/API design, code standards, test strategy, PR approval |
| Developer | Parsers, IR model, generators, tests, evidence |
| QA Engineer | Test design/execution, E2E validation, defects |
| DevOps Engineer | CI/CD, environments, deployment, monitoring |
| Security Reviewer | Threat model, dependency/secret scanning, security gate |
| Technical Writer | README, user guide, API docs, runbooks |

## Board workflow
1. Create a task in a phase with accountable/responsible roles; status starts at **Backlog**.
2. The responsible role posts updates (`update`, `blocker`, `decision`) and keeps *current work* current.
3. Gate-in/out checklist items are toggled on the task page. **Blocked** requires a blocker description;
   **Done** requires every gate-out item checked.
4. A **handoff** moves responsibility to the next role, logs it in the handoff history and the feed.
5. Record test evidence, risks and the ADR reference on the task; the Overview shows per-phase gate readiness
   (gate-out items done / total; *Ready* when all tasks are Done, *At Risk* when any is Blocked).

## Architecture artifact job (placeholder)
A job records input document names and the expected outputs `architecture.drawio`, `architecture.png` and
`architecture-presentation.pptx`, plus a test state (`Not Run`, `Running`, `Passed`, `Failed`).
Parsers and generators are future work tracked on the board (OpenAPI parser, Draw.io generator, PPTX generator).
