# Vincent Recovery Model

Recovery is a product requirement, not a special migration procedure. A worker is replaceable only if authoritative project work and current authority can be reconstructed without relying on terminal history, one machine's undocumented state, or a previous ChatGPT conversation.

## Reboot/interruption reconciliation

After supervisor restart, worker reboot, provider interruption, unexpected power loss, or temporary network loss, Vincent should:

1. validate local worker identity and protected configuration;
2. load durable local operational state using safe/atomic formats where needed;
3. re-establish networking and verify relevant external reachability;
4. fetch/reconcile authoritative project/control state;
5. revalidate task/lease ownership and schema/protocol compatibility;
6. inspect repository remote, branch/worktree and unexpected untracked/dirty state;
7. verify AI-provider authentication/identity health where applicable;
8. classify the interruption/failure;
9. resume only when continuation is deterministic and still authorized;
10. otherwise preserve evidence, block/fail explicitly, and report what human decision or repair is required.

A local `ACTIVE` marker is never sufficient authority to resume work blindly.

## Failure classes

Vincent should distinguish at least the following categories where the underlying provider/tooling permits reliable classification:

- AI-provider process/runtime failure;
- provider authentication/identity mismatch;
- usage/capacity limitation;
- network/link/DHCP/routing/DNS/TLS failure;
- Git authentication or remote divergence/conflict;
- workspace/state inconsistency;
- validation failure;
- project/task failure;
- loss/revocation of task or fleet authority;
- missing human approval/decision;
- update/maintenance failure;
- unknown/unclassified failure.

Retries are bounded/conservative. Repeated unknown failures become blocked/failed rather than entering an infinite restart loop.

## Checkpoint policy

Checkpoint useful coherent progress when doing so materially improves recovery, such as:

- after a coherent implementation milestone;
- before a risky operation or lengthy validation;
- before waiting for a human decision;
- when provider capacity becomes unavailable;
- before a planned drain/shutdown/reboot;
- at task completion.

Avoid meaningless timer-driven commits.

Track the difference among:

- local progress;
- committed progress;
- pushed/published progress;
- reviewed/integrated progress.

Only verified remote publication is safely independent of the worker.

## Worker replacement

Normal replacement should reconstruct a worker from supported Vincent installer/update paths rather than cloning an old worker disk.

A replacement sequence generally includes:

1. preserve/verify all authoritative remote project results;
2. revoke/retire the old worker identity/credentials where applicable;
3. install Vincent on replacement hardware;
4. generate a new worker identity unless a deliberate supported identity-recovery mechanism applies;
5. reconnect/enroll to the required project/control sources;
6. reconstruct project environments from authoritative requirements/fixtures;
7. resume only tasks whose current ownership/authorization is valid.

Stale credentials, expired leases or old local state must not silently regain authority.

## Recovery acceptance

Routine development uses repeated clean installs on expendable hardware to verify reproducibility. A stronger impermanence test is performed later on a worker that has already completed useful work: deliberately destroy/reinstall its local Vincent state and prove that authoritative work was not trapped on the machine and that normal operation can resume from supported external state.

## What is not backed up as authoritative worker state

Vincent workers generally do not require full-system backups as their primary recovery mechanism. Full-disk copies must not become a substitute for reproducible installation and externally durable project state.

Local logs/caches/workspaces may be useful evidence, but the architecture assumes they can be lost. Credentials are protected/revocable state, not Git backup content.

## CIC Station boundary

Managed-fleet recovery, control-plane database/application recovery, leases, worker retirement history and private fleet state belong to CIC Station documentation. Vincent documents only the worker-side recovery behavior and integration requirements.

## Interrupted coordination publication

Before changing a task file, Vincent fsyncs a publication-intent journal inside
the checkout's Git directory. The journal records the exact expected base,
branch, task path, and intended JSON transition. Synchronization stops with a
specific recovery instruction while a journal exists.

Run `mission-control-worker --config /etc/mission-control/worker.toml recover-publication`
as the authorized worker administrator. Recovery either commits the recorded
transition from its unchanged base, pushes the already-created exact checkpoint,
or recognizes a verified push whose acknowledgement was lost. Changed remote
authority, unrelated local changes, and conflicting content remain preserved
for explicit reconciliation. Recovery never resets, force-pushes, or reruns an
AI task. Claim/worker operational-state reconciliation is still a separate gate;
this command does not authorize service restart or clear uncertain ownership.
