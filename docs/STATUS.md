# Vincent Current Status

**Status date:** 2026-09-25 (America/Anchorage)

This file records temporary/current implementation and validation state. It is not a product specification or permanent historical archive.

## Repository state

- `main` is the canonical integration branch and the only permanent branch.
- The documentation/governance reset was merged through PR #12 at `fb5c8df423be39d80e0effcfe28e688fd7114810`; its validation completed successfully.
- Installer/ISO implementation from the former ISO workstreams was reconciled onto `main` at `1edbe47a5248ce2a378646decae6ccfaa1c6f1ef` without restoring retired migration/handoff documentation.
- Accepted independent version/build identity is preserved in ADR-0015 as amended by ADR-0018: Vincent `0.1.0` and installer `0.1.0` use independent monotonic build counters whose separation point was `0022`.
- The current QA-cleanup candidate advances both the Vincent runtime and installer counters to build `0023` because the change affects both components. Equal counter values are coincidental and do not make the counters shared.
- ADR-0017 supersedes the earlier private-development visibility policy: Vincent may be developed in a public repository before stable release; repository visibility is separate from release readiness.
- Managed-worker roadmap semantics are aligned with CIC Station ADR-0017: scheduling/availability, liveness/health, execution, and power are independent facts; Working/Available/Offline/Standby are derived operator-facing summaries.

Branch policy: `main` is the only permanent branch; temporary PR branches are deleted after integration or supersession once useful work is preserved.

## Current installer/worker development

The current installer/runtime implementation includes:

- operator-controlled network and storage/partitioning choices;
- active installer USB exclusion from target disks;
- dedicated locked `vincent` runtime service identity;
- rootless Podman for routine container work without root-equivalent Docker-group membership;
- unique installer build provenance and ISO/media identity;
- separate installer provenance versus current Vincent software version/build identity;
- runtime Ethernet/Wi-Fi resilience and network diagnostics;
- installer network-preflight evidence for DNS/interception/Debian-source failures;
- offline Debian installer dependency closure so OS installation does not depend on an Internet package mirror;
- resumable first-boot state for interrupted bootstrap;
- preserved Codex companion-runtime layout and bubblewrap dependency;
- local status/diagnostic/console surfaces and non-secret evidence collection;
- fresh-install worker state/identity paths aligned under `/var/lib/vincent`.

Known implementation/design debt is tracked in GitHub rather than hidden in status prose. Important current items include:

- #5 — rename inherited Mission Control identifiers and active control-plane references for the Vincent/CIC Station boundary;
- #20 — fully wire independent Vincent/installer version and build identifiers through runtime/tooling;
- #27 — implement the approved offline-first Vincent payload path;
- #37 — make standalone READY a real first-boot state independent of optional CIC Station enrollment;
- #38 — introduce the required provider-neutral adapter boundary while retaining Codex as the first implementation;
- #39 — enforce managed-worker authorization/repository scopes before execution;
- #47 — bound provider execution with supervisor deadlines/interruption handling;
- #48 — isolate AI/task execution from CIC Station worker identity, supervisor secrets, and unrelated project/provider credentials;
- #49 — future explicitly authorized zero-touch/PXE-style provisioning mode, intentionally outside the 1.0 interactive installer path.

## Carried-forward physical-test state

Historical bug/test state from the old ISO branch has been transferred into GitHub issues rather than restoring the retired permanent bug-register document.

Current verification work:

- #13 — VINCENT-BUG-0002: Nouveau boot hang; open pending reproduction/current fix.
- #14 — VINCENT-BUG-0003: transient DNS/bootstrap recovery; open pending current verification.
- #15 — VINCENT-BUG-0001: resumable first boot; fixed in code, physical verification pending.
- #16 — VINCENT-BUG-0008: duplicate Wi-Fi SSID suppression; fixed in code, physical verification pending.
- #17 — VINCENT-BUG-0009: offline Debian installer path on intercepted Wi-Fi; fixed in code, physical verification pending.
- #18 — VINCENT-BUG-0011: Codex companion runtime; fixed in code, physical verification pending.
- #28 — rootless Podman privilege boundary; fixed in code, representative physical/workload verification pending.
- #25 — verified historical fixes for BUG-0004, BUG-0005, BUG-0006, BUG-0007, and BUG-0010; retained as closed regression/provenance evidence.

A historical bug is not assumed to remain present. Each applicable issue is verified against the current build and then either retained/reopened, closed as verified fixed, or closed as obsolete/superseded with evidence.

## Physical development strategy

- **Large workstation:** persistent first useful Vincent worker; keep online for real bounded work and CIC Station development rather than repeatedly reimaging it for routine installer regression testing, except where workstation-specific regression verification is required.
- **Old laptop:** expendable physical installer test target for repeated clean installations, networking/storage/first-boot changes, and destructive failure-path testing.

Later, after the persistent workstation has performed useful work and required durable state exists elsewhere, deliberately destroy/reinstall its local worker state as the worker-impermanence/recovery acceptance test.

This is temporary lab strategy, not permanent product architecture.

## Documentation/governance state

The documentation cleanup/reorganization gate is complete on `main`:

- Vincent is the component name; no acronym/backronym.
- MPL-2.0 license is established.
- conventional `PRODUCT.md` and numbered `REQUIREMENTS.md` are authoritative;
- all 260 historical specification sections have an explicit disposition in `docs/history/SPECIFICATION_TRACEABILITY_2026-08-27.md`;
- the monolithic historical specification has been removed from the active tree;
- ADRs replace the old mixed decision register;
- permanent project-start, continuation-handoff, planned-feature, and permanent bug-register documents are retired;
- GitHub issues are the unscheduled backlog and current bug/verification tracker;
- `logrusbox/fleet` owns the overall Fleet roadmap, cross-component integration issues, and Fleet governance; Vincent roadmap is component-specific;
- migration/reset/prototype reports have been removed from the active tree after distillation;
- independent SemVer, `CHANGELOG.md`, contribution workflow, PR template, and trunk/squash conventions are established;
- repository validation checks canonical documents, requirement/ADR IDs, links, release-safety boundaries, historical traceability, and credential patterns;
- credential scanning includes high-confidence private-key, GitHub, OpenAI, AWS, and Slack credential patterns;
- active canonical documentation contains no `GitBoy` references.

## Validation

PR #46 QA-cleanup validation on build-0023 candidate source passed:

- 139 unit/integration/regression tests: PASS;
- credential-pattern scan: PASS;
- canonical documentation validation: PASS;
- Python package build: PASS;
- GitHub Actions validation runs on Node-24-compatible current action majors.

The immediately preceding build-0022 ISO path successfully built and passed `INSTALLER_INSPECTION=PASS`; its CI job then failed only because checksum verification changed into `dist/` while the checksum file already contained a `dist/...iso` path. PR #46 corrects that workflow-path defect. The build-0023 ISO workflow subsequently passed on current `main` commit `1f440a8c332374d15974939a20caaf70a898968a`: [Actions run 34644256063](https://github.com/logrusbox/vincent/actions/runs/34644256063), 2026-09-11. Automated image construction/inspection is verified; physical acceptance remains pending.

Physical validation of installer build `0023` remains pending and must correspond to the exact accepted source retained on `main`.

## Next technical gates

1. Complete physical installer/runtime acceptance from exact accepted source; the build-0023 ISO workflow is already green.
2. Resolve #27 and #37 so the bundled Vincent payload and standalone READY lifecycle no longer require unnecessary GitHub/fleet enrollment dependencies.
3. Resolve the pre-1.0 runtime architecture/authority blockers, including #38, #39, #47, and #48.
4. Build the next physical-test candidate from an exact accepted `main` commit and execute the carried-forward laptop/workstation regression issues.
5. Close, retain, or reclassify each historical bug based on current physical evidence.

Documentation/consolidation status alone does not authorize destructive flashing/reinstallation, production actions, credential expansion, protected releases, or other high-impact operations that retain separate operator gates.
