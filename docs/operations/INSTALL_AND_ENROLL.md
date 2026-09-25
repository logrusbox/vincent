# Install and Connect a Vincent Worker

This document describes the supported trust boundary after Vincent software is installed. It does not authorize destructive installation/flashing and does not grant project/fleet authority merely because a worker exists.

See [`BUILD_AND_FLASH_USB.md`](BUILD_AND_FLASH_USB.md) for image/media operations and [`../decisions/ADR-0001-standalone-generic-worker.md`](../decisions/ADR-0001-standalone-generic-worker.md) for the standalone READY model.

## Expected post-install state

A successful fresh Vincent installation should establish:

- Debian and Vincent runtime prerequisites;
- dedicated locked `vincent` Unix service identity;
- local worker identity/provenance;
- self-tests, status and diagnostics;
- network state/recovery interfaces;
- no private project/fleet/AI-provider authority by default;
- **READY / unassigned** state independent of CIC Station.

A conventional human installer account is not required for normal Vincent operation.

## Standalone project connection

For Vincent V1 standalone operation, the operator selects the project/Git/control source after installation.

The connection workflow must preserve these boundaries:

1. Operator supplies/selects the intended repository/project source.
2. Authentication uses a supported interactive/scoped mechanism appropriate to that source.
3. Vincent verifies the intended repository/remote and records only non-secret connection metadata.
4. Project requirements/dependency constraints are loaded before environment preparation.
5. A bounded assignment identifies objective, allowed scope, acceptance criteria, and result/report destination.
6. Vincent prepares an isolated workspace/environment, performs the task, validates results, publishes durable project artifacts, verifies remote publication, and reports outcome.

Do not place repository credentials/tokens/private keys in Git, task text, status output or ordinary reports.

## AI-provider enrollment

AI-provider authentication is separate from Git/project authorization.

Vincent performs provider-specific enrollment through the selected provider adapter. For human-bound accounts, use the provider's supported device/interactive authorization when available rather than copying reusable credentials through Git or project instructions.

Where supported, verify/report non-secret effective provider identity/account/organization/tenant/project context and authentication health before executing work. If the active provider identity clearly does not match the intended profile, stop/surface the mismatch instead of silently continuing.

Provider credentials remain in protected provider/OS credential storage and are excluded from logs/diagnostics/reports/Git.

## CIC Station fleet enrollment

CIC Station is optional. A standalone READY worker does not contact/trust the private fleet automatically.

When the operator chooses managed-fleet enrollment:

1. Vincent exposes/generates the worker enrollment identity/request required by the current protocol.
2. Operator/CIC Station verifies and explicitly approves the worker identity.
3. Scoped/revocable fleet authorization is delivered outside ordinary Git state.
4. Vincent establishes authenticated outbound control-plane communication.
5. CIC Station may assign roles/scopes, bounded tasks/leases, and desired AI-provider identity/profile policy.
6. Vincent continues to enforce its local product/safety requirements and project requirements while following valid managed-fleet authority.

Revoking/suspending a worker must not require distributing or rotating a shared fleet-wide credential.

## Protected local identity and reinstallation

Do not casually delete or regenerate a currently authorized worker identity during troubleshooting.

A deliberate reinstall normally creates a new local worker identity. The old identity/credentials should be revoked/retired according to the relevant project/CIC Station procedure unless a separately designed supported identity-recovery mechanism explicitly restores it.

Worker replacement is preferred over copying an entire old worker disk as a normal recovery mechanism.

## Verification before bounded work

Before starting real work, verify at least:

- worker self-test/health/status;
- installer provenance and current Vincent software version are visible separately;
- network/DNS/HTTPS/project/provider diagnostics are healthy enough for the assignment;
- selected project remote/source is correct;
- project constraints are loaded;
- required Git authorization works at the intended scope;
- selected AI provider is installed/enrolled and effective identity is acceptable where verifiable;
- task ownership/authorization is current;
- workspace is clean/isolated or unexpected state has been explicitly preserved/escalated.

Do not interpret a successful local setup command as authorization to perform production, destructive external, credential-expanding or protected integration actions.


## Build-0025 standalone lifecycle

First boot installs the verified bundled payload and configures bundled local
runtime dependencies without contacting GitHub, a model provider, or a registry.
The locked Vincent identity is generated locally. No enrollment request is
created automatically and the coordination execution service remains disabled.
A passing local self-test writes a READY/unassigned snapshot; `vincent status`
(or `vincent`) displays it without network access. Provider availability is a
separate capability and never grants authority. A restart of first-boot recovery
invalidates the previous READY snapshot until local checks pass again.

`vincent enroll`, run under the Vincent service identity or the authorized local
administrator, explicitly exports a public enrollment request using the existing
installation identity. This does not contact CIC Station, grant managed authority,
or enable execution. The authenticated CIC enrollment transport remains #35/#36.

Provider installation/authentication and operator-selected standalone project
configuration are later explicit steps. The legacy online
`bootstrap/provision-worker-baseline.sh` is no longer a first-boot dependency;
its mutable Codex installer remains under review in #42. Use the documented
administrative recovery path for privileged maintenance; do not give task
processes unrestricted sudo. Physical acceptance remains required.
