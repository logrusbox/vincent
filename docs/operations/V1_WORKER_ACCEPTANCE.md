# Vincent 1.0 Worker Acceptance

This runbook defines the outcome-level proof required before Vincent can be treated as a trustworthy 1.0 worker platform. It complements the normative requirements in [`../REQUIREMENTS.md`](../REQUIREMENTS.md); it does not replace them.

## Scope

Acceptance proves the supported worker lifecycle:

```text
validated installer
  -> operator-controlled install
  -> standalone READY
  -> project/provider connection
  -> bounded work
  -> independent validation
  -> durable publication/report
  -> maintenance/recovery
```

CIC Station is not required for the basic Vincent 1.0 worker proof. Managed-fleet integration is a separate program/product milestone.

## 1. Exact source and installer evidence

Record and verify:

- exact Vincent source commit;
- installer build number;
- Debian source/version/architecture;
- source and output image verification/checksums;
- repository validation result;
- image inspection result;
- secret/identity/obsolete-name scans applicable to the build.

Do not proceed with a failed validation gate.

## 2. Physical installation proof

On representative expendable hardware prove:

- intended installer media boots;
- operator selects/configures networking;
- active installer USB is not offered as a target disk;
- operator selects the intended target disk;
- normal Debian partitioning choices remain available and Vincent does not force LVM/whole-disk/fixed layout;
- final destructive disk write requires normal operator confirmation;
- installation completes without undocumented repair;
- no conventional human account is required for routine Vincent operation.

Repeat a clean installation after defects are corrected to prove reproducibility.

## 3. First-boot/READY proof

Verify:

- dedicated locked `vincent` service identity and narrow privileged interfaces;
- stable local worker identity;
- self-tests/status/diagnostics start normally;
- immutable installer provenance is displayed/reported;
- current Vincent software version is displayed/reported separately;
- worker reaches READY/unassigned without private CIC Station state or credentials;
- no reusable Git/fleet/provider/production credential was embedded in the installer.

## 4. Network resilience proof

At minimum:

1. establish healthy operation over Ethernet;
2. enumerate wired/wireless interfaces and active route;
3. remove/disconnect Ethernet;
4. reuse a protected existing Wi-Fi profile or configure Wi-Fi through the local SSID/passphrase workflow;
5. verify the worker continues required operation over Wi-Fi;
6. restore Ethernet and verify normal route preference when both paths are healthy.

Diagnostics must provide enough non-secret evidence to distinguish link/association, DHCP/addressing, route, DNS, HTTP(S)/TLS, Debian package-source, Git/project and provider failures.

## 5. Project connection proof

Use a deliberately safe repository/project scope.

Verify:

- operator-selected repository/control source;
- scoped supported authentication;
- expected remote/repository identity;
- project requirements/dependency constraints loaded;
- required environment/tooling prepared without silently violating those constraints;
- no access to unrelated repositories is assumed or granted merely because Vincent is installed.

## 6. AI-provider proof

For the initial Codex provider:

- install/use the supported provider integration through the Vincent provider boundary;
- complete supported provider authentication locally as required;
- keep reusable credentials out of Git/task text/logs/reports;
- verify non-secret effective provider identity/account/project context where the provider exposes it;
- demonstrate that a clear intended-profile mismatch blocks/surfaces instead of silently continuing, where practically testable.

## 7. Bounded work proof

Execute one harmless real bounded task that proves the complete path:

1. obtain an explicit task/objective/scope;
2. establish current task ownership;
3. prepare an isolated clean workspace;
4. record starting revision;
5. perform deterministic local preparation directly where appropriate;
6. invoke the AI provider for the implementation step;
7. execute independent acceptance/validation commands;
8. commit/publish only authorized changes;
9. verify the remote publication actually succeeded;
10. publish a structured result/report identifying starting/ending revisions and validation;
11. return the worker to an idle/READY state.

A local commit or successful AI process exit alone is not task completion.

## 8. Failure/recovery proof

Exercise representative safe failure cases, including where practical:

- supervisor/process restart;
- worker reboot during active work;
- temporary network loss;
- Git publication failure/divergence;
- unexpected dirty/untracked workspace state;
- provider interruption/authentication failure simulation;
- task cancellation/supersession or authority loss.

Verify useful work is preserved, retries are bounded, ownership is revalidated and ambiguous cases block rather than overwrite/duplicate work.

## 9. Maintenance/update proof

Demonstrate representative supported maintenance without reimaging:

- Debian/system maintenance;
- Vincent/runtime/tooling maintenance;
- project version constraints remain respected;
- worker health/status reflects relevant maintenance state.

If minimum safe Vincent in-place self-update is included in 1.0, prove update from the trusted public release mechanism and verify:

- current Vincent software version changes as expected;
- original installer build provenance does not change;
- failure handling/recoverability are documented and tested to the implemented level.

## 10. Reproducibility and evidence

Acceptance evidence should be concise and identify:

- tested source/release and installer build;
- hardware class;
- install/READY/network/project/provider/task/maintenance results;
- defects found and corrective/retest state;
- resulting published Git/project revisions;
- any requirement not yet verified.

Large raw logs/screenshots/build outputs remain Actions/release/local artifacts rather than ordinary Git unless a small excerpt is necessary to understand a durable acceptance conclusion.

## Acceptance rule

Vincent 1.0.0 is not accepted merely because implementation exists. Every requirement targeted to 1.0 must be either verified by appropriate evidence or explicitly resolved through a later accepted requirement/ADR changing the release scope. There must be no undocumented repair step required to reproduce the supported worker path.
