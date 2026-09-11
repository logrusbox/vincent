# Historical ISO Testing — August 2026

**Classification:** HISTORICAL implementation/test evidence  
**Authority:** current Vincent requirements, ADRs, `docs/STATUS.md`, issues, source, tests, and accepted `main` always outrank this record.

This note preserves expensive-to-rediscover evidence from the August 2026 ISO rebuild and physical-testing threads without restoring their temporary branches or old execution plan as current authority.

## Reconciliation scope

The work was performed on the temporary `workstream/iso-decisions-reconcile` lineage while Git remained authoritative and destructive media operations retained explicit target/operator gates. That branch is historical; current `main` is the only permanent branch.

## Early build evidence

- Build `0011` was produced from expected workstream source after 109 tests and migration/credential checks passed. The ISO itself was created with volume identity `VINCENT_B0011`, but the inspection gate failed because the inspection script discarded `xorriso` volume-ID diagnostics. This was a tooling/inspection failure rather than evidence that the image had not been created.
- The inspection parser was corrected and the installer advanced through subsequent candidate builds.
- Build `0013` used platform commit `9771c0518ac2ad7c7846431a1f7a8f1fcb26f6fb`. Validation again passed 109 tests. `vincent-debian-13.6.0-amd64-build-0013.iso` built successfully and passed installer inspection. Recorded SHA-256: `c47565023e1858aaaea1fa35cf1ff3076831ce0daf15f341d88ddf1caad30171`.
- The build-0013 USB flash attempt correctly failed closed before any write. The intended target was `/dev/sda`, a removable 57.3 GB SanDisk USB device, but the expected ISO was not present in the invocation directory. The flash gate reported failure and no write occurred. This is retained as evidence that destructive-media gating worked as intended.
- By build `0014`, additional installer corrections included service-account/runuser handling and automated `en_US.UTF-8` / US-keyboard defaults while preserving interactive network and target-disk choices and avoiding creation of an ordinary human runtime account.

## Later physical-test lineage

The ISO work continued through later candidates, including the `0021.2` physical-test sequence. Testing on the expendable laptop and workstation surfaced installer/runtime issues including Wi-Fi/DNS/bootstrap behavior. Work was subsequently stopped pending the documentation/governance rework rather than continuing to layer fixes onto an unreconciled branch structure.

The later consolidation moved useful installer implementation and regression state onto current Vincent Git. Current `docs/STATUS.md` records the authoritative carried-forward state, including:

- transient DNS/bootstrap verification;
- resumable first boot;
- duplicate Wi-Fi SSID handling;
- offline Debian installer behavior on intercepted Wi-Fi;
- Codex companion-runtime verification;
- rootless Podman privilege-boundary verification;
- exact-`main` physical validation gates for the current installer build.

Do not infer that an old build-specific bug remains present. Current issues and physical evidence determine whether each regression is open, fixed, obsolete, or superseded.

## Durable lessons

1. Build success and installer inspection are separate gates; inspection tooling itself must preserve the diagnostics it relies on.
2. Destructive USB flashing must fail closed if either the exact target or exact image cannot be verified.
3. Physical installer validation is required; generated ISO success is not sufficient acceptance evidence.
4. Network failures must be diagnosed by layer so DNS, local association/addressing, repository reachability, and installer defects are not conflated.
5. Temporary ISO branches and exact old build commands are historical evidence, not current development authority.
6. Current accepted source and carried-forward GitHub issues govern all future physical regression testing.
