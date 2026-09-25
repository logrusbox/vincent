# Vincent Requirements

Requirement identifiers in this document are permanent once merged into `main`. An identifier is never reassigned to a different requirement. Requirements that are later replaced remain listed with `Superseded` or `Withdrawn` status and a reference to the replacement/decision.

Unless otherwise stated, `Accepted` requirements are product requirements even when implementation is incomplete. Release targets indicate intended sequencing, not whether the requirement exists.

## Product and authority

### VIN-REQ-0001 — Generic worker platform
**Status:** Accepted  
**Target:** 1.0.0

Vincent must be a reusable worker platform and must not hard-code assumptions for one owner project, one repository, one physical machine, or one AI provider.

### VIN-REQ-0002 — Standalone READY state
**Status:** Accepted  
**Target:** 1.0.0

A fresh Vincent installation must boot, self-test, diagnose itself, maintain the local system, and reach an unassigned READY state without CIC Station or private project credentials.

### VIN-REQ-0003 — Git-backed durable project work
**Status:** Accepted  
**Target:** 1.0.0

Durable source and project artifacts must be published to the project's authoritative Git/project systems. A worker filesystem must not be the only location containing valuable completed work.

### VIN-REQ-0004 — Replaceable worker
**Status:** Accepted  
**Target:** 1.0.0

Loss or reinstallation of a worker must not require reconstructing authoritative project work from memory. Local worker state should be reconstructable wherever practical.

### VIN-REQ-0005 — Bounded execution
**Status:** Accepted  
**Target:** 1.0.0

Vincent must execute bounded assignments with explicit repository/project scope, constraints, acceptance criteria, and completion/reporting behavior rather than treating general machine access as task authority.

### VIN-REQ-0006 — Project authority preservation
**Status:** Accepted  
**Target:** 1.0.0

Project repository instructions, requirements, dependency/version constraints, production policy, and protected integration rules remain authoritative for project work and must not be weakened by Vincent's local privileges.

## Operating system and hardware

### VIN-REQ-0007 — Linux-first Debian reference platform
**Status:** Accepted  
**Target:** 1.0.0

Vincent is Linux-first with Debian 13 as the initial reference operating system. Normal worker operation must support headless use.

### VIN-REQ-0008 — Heterogeneous commodity hardware
**Status:** Accepted  
**Target:** 1.0.0

Vincent must support materially different compatible computers without requiring expensive specialized hardware or a GPU. Capability/resource discovery must represent meaningful machine differences.

### VIN-REQ-0009 — Resource-aware operation
**Status:** Accepted  
**Target:** 1.0.0

Vincent must report useful CPU, memory, storage, network, container/tooling, and agent capabilities and avoid launching work that violates known hard resource constraints.

### VIN-REQ-0010 — Resource conservation
**Status:** Accepted  
**Target:** 1.0.0

Vincent must avoid uncontrolled resource growth, including logs, Docker/container artifacts, obsolete workspaces, and caches, while never deleting unknown or potentially unpushed work merely to reclaim resources.

## Installer and provisioning

### VIN-REQ-0011 — Reproducible installer
**Status:** Accepted  
**Target:** 1.0.0

Vincent installation media must be reproducibly buildable from version-controlled inputs and a documented/validated Debian source. Manual ISO modifications are not authoritative build inputs.

### VIN-REQ-0012 — Universal installation media
**Status:** Accepted  
**Target:** 1.0.0

The same supported Vincent installer image should be usable across multiple compatible machines. Machine-specific permanent identities or credentials must not be baked into the universal image.

### VIN-REQ-0013 — Interactive network and storage choices
**Status:** Accepted  
**Target:** 1.0.0

The installer must preserve normal operator control over network interface/SSID/passphrase choices and target-disk/partitioning/final-write choices. Vincent must not force a network credential, target disk, whole-disk use, LVM, or a fixed partition recipe.

### VIN-REQ-0014 — Active installer media exclusion
**Status:** Accepted  
**Target:** 1.0.0

The active boot/install medium must not be offered as an installation/partitioning target. Excluding the active installer medium must not automatically select or prefer another disk.

### VIN-REQ-0015 — Installer network preflight evidence
**Status:** Accepted  
**Target:** 1.0.0

Installer diagnostics must be capable of preserving non-secret network evidence sufficient to distinguish local DNS/resolver behavior, direct DNS reachability, HTTP(S) interception/reachability, and Debian repository/package-source failures during physical installation testing.

### VIN-REQ-0016 — No reusable secrets on installation media
**Status:** Accepted  
**Target:** 1.0.0

Installation media must not contain personal tokens, permanent worker private keys, reusable enrollment secrets, production credentials, shared fleet credentials, AI-provider credentials, or private fleet configuration.

### VIN-REQ-0017 — Dedicated Vincent service identity
**Status:** Accepted  
**Target:** 1.0.0

Runtime automation must use a dedicated locked least-privileged `vincent` Unix service identity. Routine operation must not require a conventional human installer account, `nobody`, or unrestricted sudo/root access for the Vincent service identity.

### VIN-REQ-0018 — Explicit destructive boundaries
**Status:** Accepted  
**Target:** 1.0.0

Destructive installation/flashing and other high-impact local operations must have explicit operator gates appropriate to their blast radius. Vincent must never infer authorization to erase every visible device.

### VIN-REQ-0019 — Installer build provenance
**Status:** Accepted  
**Target:** 1.0.0

Every installer image build must have a unique monotonically increasing installer build number consistently represented in filename/media identity, build metadata, manifests/checksums, validation logs, and installed provenance.

### VIN-REQ-0020 — Installer and software identity separation
**Status:** Accepted  
**Target:** 1.0.0

The immutable installer build identity and the currently installed Vincent software version/build are separate lifecycle values. Updating Vincent software must never rewrite original installer provenance.

## Worker identity, credentials, and security

### VIN-REQ-0021 — Unique worker identity
**Status:** Accepted  
**Target:** 1.0.0

A newly installed worker must create a unique local identity rather than receiving a permanent fleet identity from universal installation media. Reinstallation normally creates a new identity unless a deliberate supported recovery mechanism says otherwise.

### VIN-REQ-0022 — Least-privileged external authorization
**Status:** Accepted  
**Target:** 1.0.0

Credentials granted to a worker must be unique/scoped/revocable where the external system permits it. Compromise or retirement of one worker must not require rotating a shared fleet-wide credential.

### VIN-REQ-0023 — Secrets stay out of Git and routine evidence
**Status:** Accepted  
**Target:** 1.0.0

Private keys, passwords, tokens, authentication caches, AI-provider credentials, production secrets, and equivalent reusable secrets must not be committed to Git or emitted in ordinary logs, reports, status screens, diagnostics, or enrollment payloads.

### VIN-REQ-0024 — Protected credential storage
**Status:** Accepted  
**Target:** 1.0.0

Local worker credentials must use appropriate operating-system permissions/protected stores and must not be exposed unnecessarily to project workspaces or containers.

### VIN-REQ-0025 — External blast-radius controls
**Status:** Accepted  
**Target:** 1.0.0

Broad local authority on a disposable worker must not imply authority over production systems, unrelated repositories, DNS, cloud resources, backups, protected branches, or other authoritative external state. High-impact external actions require separate explicit authorization.

### VIN-REQ-0026 — Production is not an implicit completion step
**Status:** Accepted  
**Target:** 1.0.0

Passing development validation must not automatically authorize production deployment. Project-specific production gates remain separate.

## Runtime and work execution

### VIN-REQ-0027 — Managed local services
**Status:** Accepted  
**Target:** 1.0.0

Persistent Vincent components must use conventional Debian service management, normally systemd, with automatic startup, useful status/logging, bounded restart behavior, and explicit health checks.

### VIN-REQ-0028 — Worker supervisor
**Status:** Accepted  
**Target:** 1.0.0

Vincent must provide a maintainable supervisor/runtime capable of loading worker/project configuration, preparing isolated workspaces, invoking the selected AI provider, tracking task state, executing validation, publishing results, reporting failures, and recovering after restart.

### VIN-REQ-0029 — Workspace isolation
**Status:** Accepted  
**Target:** 1.0.0

Concurrent or sequential tasks must use predictable isolated workspaces. Unexpected dirty/untracked state must be detected and preserved/escalated rather than erased unconditionally.

### VIN-REQ-0030 — Safe Git synchronization
**Status:** Accepted  
**Target:** 1.0.0

Before work and publication, Vincent must verify repository/remote/branch state, fetch remote changes, detect divergence and unexpected modifications, avoid routine force-push/destructive reset behavior, and verify that intended remote publication actually succeeded.

### VIN-REQ-0031 — Explicit task ownership
**Status:** Accepted  
**Target:** 1.0.0

Exclusive work must have deterministic ownership semantics so two workers do not unknowingly publish competing results for the same assignment. Vincent must stop or block when authoritative ownership is lost or ambiguous.

### VIN-REQ-0032 — Structured task states
**Status:** Accepted  
**Target:** 1.0.0

The worker/task protocol must distinguish meaningful states such as queued/active/blocked/waiting-for-human/completed/failed/cancelled/superseded/usage-limited as appropriate and define authorized state transitions.

### VIN-REQ-0033 — Validation contracts
**Status:** Accepted  
**Target:** 1.0.0

Assignments must be able to define executable acceptance/validation commands. Vincent must record validation outcomes independently of an AI agent merely asserting success.

### VIN-REQ-0034 — Structured results and failure reports
**Status:** Accepted  
**Target:** 1.0.0

Vincent must produce durable structured results identifying worker/task/project/repository/starting and ending revisions, changes, validation, publication state, unresolved items, and human-decision needs without embedding large raw logs.

### VIN-REQ-0035 — No silent success
**Status:** Accepted  
**Target:** 1.0.0

Critical operations must verify the intended outcome. Local commit, process exit, package installation, container start, or test invocation alone must not be reported as higher-level success without the corresponding verification.

### VIN-REQ-0036 — Human-readable failures
**Status:** Accepted  
**Target:** 1.0.0

Failures must identify the operation, expected/actual state, preserved work, retry safety, and any human decision required instead of exposing only an unexplained exit code.

### VIN-REQ-0037 — Bounded retry and interruption recovery
**Status:** Accepted  
**Target:** 1.0.0

Supervisor/agent/network failures must be classified before retry. Automatic retries must be bounded/conservative, preserve work, and avoid duplicate publication or endless restart loops.

### VIN-REQ-0038 — Checkpoint and reboot recovery
**Status:** Accepted  
**Target:** 1.0.0

Vincent must preserve coherent progress and reconstruct safe continuation after supervisor restart, AI-agent interruption, reboot, unexpected power loss, or temporary network loss. Resume must revalidate remote task ownership and Git state.

## Networking and diagnostics

### VIN-REQ-0039 — Runtime wired/Wi-Fi resilience
**Status:** Accepted  
**Target:** 1.0.0

A worker must enumerate available network interfaces, prefer healthy wired Ethernet by default, and remain operable through a previously configured working Wi-Fi profile when Ethernet disappears. If no usable Wi-Fi profile exists, a local console workflow must permit SSID selection and secure passphrase entry without converting the `vincent` service account into a human login.

### VIN-REQ-0040 — Protected Wi-Fi credentials
**Status:** Accepted  
**Target:** 1.0.0

Stored Wi-Fi credentials must use the normal protected system network configuration mechanism and must not appear in Git, status, logs, diagnostic bundles, reports, or enrollment data.

### VIN-REQ-0041 — Layered network diagnostics
**Status:** Accepted  
**Target:** 1.0.0

Vincent diagnostics must distinguish interface/link, association/authentication, addressing/DHCP, routing, DNS, HTTP(S)/TLS reachability, package-source, and repository/provider-specific access failures without exposing credentials.

## Maintenance and updates

### VIN-REQ-0042 — System and toolchain maintenance
**Status:** Accepted  
**Target:** 1.0.0

Vincent owns maintenance of the underlying Debian installation, Vincent software, runtime dependencies, broadly required development tools, and project tooling while honoring active project version constraints.

### VIN-REQ-0043 — Trusted public Vincent update channel
**Status:** Accepted  
**Target:** 1.0.0

Installed workers must obtain approved Vincent software updates from the public Vincent release channel using validated release metadata/artifacts rather than blindly executing arbitrary current `main` contents. Routine application updates must not require reimaging.

### VIN-REQ-0044 — Update recoverability
**Status:** Accepted  
**Target:** 1.0.0 / strengthened in 1.1.x

Vincent updates must preserve recoverability and report the resulting software version. More advanced rollback, staged rollout, maintenance-window, and channel policy may be implemented after the minimum safe update path.

### VIN-REQ-0045 — Compatible network-installer path
**Status:** Planned  
**Target:** 1.1.x

A compatible installer may, when online, fetch and validate the current approved Vincent release instead of being limited to its bundled payload. It must preserve deterministic fallback to a validated bundled offline payload and must never install an incompatible newer Vincent release.

## AI-provider architecture

### VIN-REQ-0046 — Provider-neutral adapter boundary
**Status:** Accepted  
**Target:** architecture now; multi-provider implementation later

Vincent must isolate provider-specific installation, authentication/enrollment, capability, health, update, and runtime behavior behind an adapter/provider boundary so the core worker lifecycle is not permanently coupled to Codex.

### VIN-REQ-0047 — Codex-first implementation without permanent coupling
**Status:** Accepted  
**Target:** 1.0.0

Initial implementation may optimize for OpenAI Codex, but provider-specific assumptions must remain sufficiently isolated to permit future Gemini, Copilot, Ollama/local-model, and custom-agent integrations.

### VIN-REQ-0048 — Provider enrollment is local to Vincent
**Status:** Accepted  
**Target:** 1.0.0

Vincent must perform provider-specific enrollment/authentication through the relevant adapter. For human-bound accounts, supported device/interactive authorization is preferred over copying reusable credentials through Git or task text.

### VIN-REQ-0049 — Provider identity/scope verification
**Status:** Accepted  
**Target:** 1.0.0 where provider interfaces permit

Vincent should verify and report non-secret effective provider identity/account/organization/tenant/project context and authentication health where supported, and must surface/block clear mismatches instead of silently using an unintended identity.

### VIN-REQ-0050 — No shared fleet-wide AI credential
**Status:** Accepted  
**Target:** 1.0.0

AI-provider credentials must not be shared as a single fleet-wide secret. Any future unattended provider credential delivery must use a separately protected mechanism with unique/scoped/revocable credentials where applicable.

## CIC Station integration

### VIN-REQ-0051 — Explicit fleet enrollment
**Status:** Accepted  
**Target:** integration milestone

CIC Station becomes authoritative for managed-fleet policy only after explicit worker enrollment/trust. A standalone worker must not automatically contact or trust a private fleet repository/service merely because Vincent is installed.

### VIN-REQ-0052 — Outbound authenticated control-plane communication
**Status:** Accepted  
**Target:** CIC Station integration milestone

Normal Vincent-to-Mission-Control communication should be initiated outbound by Vincent over an authenticated protocol so managed workers do not require general inbound management exposure.

### VIN-REQ-0053 — CIC Station identity-profile boundary
**Status:** Accepted  
**Target:** CIC Station integration milestone

CIC Station may specify the desired AI provider and intended non-secret identity/profile/policy. Vincent remains responsible for provider-specific local installation/enrollment and credential-health verification.

## Quality, observability, and release

### VIN-REQ-0054 — Status surface
**Status:** Accepted  
**Target:** 1.0.0

Vincent must provide a concise local status surface showing worker identity, READY/health state, network state, supervisor/agent state, immutable installer provenance, and current Vincent software version without exposing secrets.

### VIN-REQ-0055 — Operational logging
**Status:** Accepted  
**Target:** 1.0.0

Vincent services must emit bounded useful logs through standard Linux mechanisms. Durable task outcomes belong in structured project/control-plane results rather than only in local logs.

### VIN-REQ-0056 — Idempotent/repeatable maintenance
**Status:** Accepted  
**Target:** 1.0.0

Provisioning and routine maintenance operations should be idempotent wherever practical and must explicitly detect operations that cannot safely be repeated.

### VIN-REQ-0057 — Physical clean-install acceptance
**Status:** Accepted  
**Target:** 1.0.0

Vincent 1.0 acceptance requires reproducible physical installation evidence on representative hardware, including installer-media exclusion, operator-controlled storage/network choices, READY state, networking/diagnostics, service identity, bounded work, and repeat installation without undocumented repair.

### VIN-REQ-0058 — Worker recovery/impermanence acceptance
**Status:** Accepted  
**Target:** program recovery milestone

The project must prove that a previously useful worker can be destroyed/reinstalled or otherwise lose local state and be reconstructed without loss of authoritative project work or silent restoration of stale authority.

### VIN-REQ-0059 — Versioned protocols
**Status:** Accepted  
**Target:** 1.0.0

Machine-readable schemas/protocols crossing component boundaries must carry explicit versions and reject unsupported incompatible versions rather than silently guessing semantics.

### VIN-REQ-0060 — Semantic Versioning and release history
**Status:** Accepted  
**Target:** immediately

Vincent software releases use independent SemVer (`0.x.y` before 1.0.0), Git tags/GitHub Releases, and a concise repository `CHANGELOG.md`. Installer build numbers remain separate provenance identifiers.

### VIN-REQ-0061 — Documentation is implementation
**Status:** Accepted  
**Target:** immediately

Current product intent, requirements, architecture, ADRs, operations, protocols, roadmap, and status must be maintained in Git so a fresh human/agent can continue without relying on chat history. Permanent handoff/start-here/planned-feature documents are not authoritative.

### VIN-REQ-0062 — Evidence retention discipline
**Status:** Accepted  
**Target:** immediately

Git should retain concise durable acceptance/release evidence when operationally useful, but large raw logs, screenshots, generated images/build products, and CI bundles should use Actions/release artifacts or another appropriate artifact store instead of turning the repository into a log archive.

### VIN-REQ-0063 — Open-source distribution boundary
**Status:** Accepted  
**Target:** immediately

Reusable Vincent source and public documentation must remain safe for public distribution under MPL-2.0 and must not require owner-specific private configuration or secrets.
