# Vincent System Architecture

This document expands the high-level [`../ARCHITECTURE.md`](../ARCHITECTURE.md). Product requirements are normative in [`../REQUIREMENTS.md`](../REQUIREMENTS.md).

## Local layers

1. **Installer/bootstrap** — creates a reproducible Debian/Vincent system without private authority.
2. **System services** — root-owned narrow privileged helpers plus systemd lifecycle.
3. **Vincent supervisor/runtime** — runs as the dedicated `vincent` service identity, reconciles local/remote task state, prepares environments, invokes AI-provider adapters, validates/publishes/reports, and recovers after interruption.
4. **Workspace/environment layer** — isolated Git worktree/checkout plus project-local or containerized tooling and project version constraints.
5. **AI-provider adapter** — installs/configures/invokes the selected provider and implements provider-specific enrollment/authentication health/identity checks.
6. **External project/control source** — authoritative project requirements/instructions/tasks/results for standalone operation, or the CIC Station integration when explicitly enrolled.

## Durable authority model

Vincent does not attempt to make one database or worker filesystem authoritative for everything.

| State | Authority / retention |
|---|---|
| Project source, requirements, repository instructions, durable project artifacts | Project repository/system |
| Vincent product requirements, ADRs, source and releases | Vincent Git/release channel |
| Managed-fleet trust, assignments/leases, approvals/audit | CIC Station when enrolled |
| Local private worker identity and credentials | Protected worker storage; replaceable/revocable |
| Workspace progress not yet pushed | Local and at risk; checkpoint/publish policy limits exposure |
| Live process/session/resource samples | Local/ephemeral |

## Execution path

```text
bounded task / project authority
        ↓
Vincent validates scope + ownership + environment
        ↓
prepare isolated workspace
        ↓
perform deterministic local steps directly
        ↓
invoke selected AI provider through adapter when AI reasoning is required
        ↓
independent validation
        ↓
Git/result publication with remote verification
        ↓
structured completion/block/failure report
```

AI agents are not used for deterministic work the supervisor can perform directly when avoiding the AI call is simpler and more reliable.

## Codex-first provider implementation

Codex is the initial provider, but the legacy `codex exec` ADR is not the permanent top-level architecture. Provider-specific interface choices belong under the AI-provider adapter and must be verified against the actually supported provider tooling/version during implementation.

Terminal keystroke injection is not an acceptable primary automation interface when a supported programmatic/noninteractive interface exists.

## Recovery property

Supervisor restart, worker reboot, abrupt power loss, temporary network loss, provider interruption, or coordinator loss must not cause blind continuation.

Recovery revalidates:

- worker identity and local protected state;
- task/lease ownership where applicable;
- remote Git/project state;
- workspace cleanliness/progress;
- provider authentication health;
- whether continuation/retry is safe.

Ambiguous ownership or authoritative divergence blocks/escalates instead of guessing.

## Replacement property

Loss of a worker should cost only reconstructable caches/environment state, local logs, worker-specific credentials that can be revoked/recreated, and at most bounded unpushed progress. Authoritative completed work must remain external to the worker.

CIC Station, when used, is also designed as a replaceable control-plane service whose durable program/application source and private fleet state are separately recoverable according to its own architecture.

## Provider invocation bounds

The executor consumes `Provider.execute` and provider-neutral results. Codex is
composed in `providers.py`; workspace, validation, publication, and recovery do
not import the Codex adapter. Provisioning/identity-health abstraction remains
tracked separately in #38.

`[provider].execution_timeout_seconds` is an explicit positive operator policy
required before the worker service can run. The sample value is an example,
not a hidden fallback. SIGINT/SIGTERM share the cancellation event with provider
execution. Deadline/cancellation stops the original process group, escalates
TERM to KILL, preserves partial output and workspace, and reports distinct
TIMEOUT/INTERRUPTED reasons as BLOCKED. Automatic retry is prohibited; reconcile
work and publication before restarting. This controls ordinary process
lifecycle; hostile process escape and credential isolation remain #48.
