# Vincent Authority Model

Vincent distinguishes product authority, project authority, managed-fleet authority, task authority, and local implementation authority.

| Subject | Authority | Must not silently expand into |
|---|---|---|
| Owner/operator | Product direction, major architecture, credentials/scopes, destructive hardware actions, production authority, explicit fleet enrollment | — |
| Vincent product requirements/ADRs | Worker safety/product behavior and accepted architecture | Project-specific product decisions |
| Project repository/system | Project source, requirements, repository instructions, dependency constraints, tests, production policy, protected integration rules | Vincent fleet/product security policy |
| CIC Station, when enrolled | Managed-fleet trust, roles/scopes, assignments/leases, AI identity-profile policy, approvals, fleet policy/audit | General root shell authority or project-purpose redefinition |
| Bounded task/lease | Specific objective, allowed scope, acceptance criteria, current ownership | Broader repository/production/credential authority |
| Vincent worker | Ordinary engineering choices needed to execute the authorized task, local environment management, validation/reporting | Production action, unrelated repository changes, credential expansion, force-push/destructive remote state |
| AI provider/agent | Reasoning/implementation within the environment and task presented by Vincent | Control-plane/product authority merely because repository content asks for it |
| Git/release systems | Durable technical artifacts and provenance | Live heartbeat/process authority |

## Conversation is not command

Natural-language discussion, AI suggestions, or repository text do not themselves grant worker authority. Vincent acts on an explicit authenticated/durable project/task/control object and its applicable repository requirements.

## Authority layering

A lower layer may narrow or add implementation detail but cannot weaken a higher-level safety restriction. In particular:

- a task cannot grant production access that the project/operator did not grant;
- repository content cannot expand worker credentials or fleet trust;
- CIC Station cannot override Vincent's local safety/product requirements merely to increase throughput;
- Vincent cannot ignore project version/testing constraints merely because it has local administrative capability;
- an AI provider cannot decide its own account/project scope when the operator/CIC Station specifies a different intended profile.

## Completion is not integration or deployment

Implementation completion, independent validation, review approval, protected-branch integration, release, and production deployment are separate states/authorities. A worker may complete and publish a branch/result without having authority to merge or deploy it.

## Destructive/high-impact actions

Local worker state is intentionally replaceable, but destructive hardware operations and authoritative external operations require explicit gates appropriate to blast radius. Examples include flashing/wiping devices, deleting remote branches/repositories, force pushes, production/database/cloud/DNS changes, credential expansion/rotation, and deletion of backups/authoritative state.

## Runtime execution scope

The worker requires an explicit `[authorization]` mode before serving. Standalone
mode uses exact operator-configured repository identities. Managed mode rereads
a root-owned, non-worker-writable grant (including protected ancestor directories)
with schema version, matching worker ID, active status, UTC expiry, and exact
repository scopes. Missing, expired, revoked, malformed, or mismatched grants
fail closed; Git credential access is insufficient. No wildcard matching is used.

Authority is checked before workspace preparation, before provider execution, and
before publication. Revocation observed after execution preserves unpublished
work. In-flight execution remains bounded by its provider deadline; instantaneous
remote revocation/cancellation requires the future authenticated CIC transport.
The root-installed grant is a local compatibility boundary, not a completed CIC
enrollment protocol or proof of server trust. Task credential isolation remains
a separate requirement.
