# Debian USB Installer Architecture

The reference Vincent installer remasters a verified official Debian 13 amd64 installer image and adds Vincent's reproducible installer/bootstrap payload and validation metadata.

## Product boundary

The installation image is public-equivalent bootstrap/recovery material. Possession of the image must not grant private project/fleet authority, a permanent worker identity, Git credentials, AI-provider credentials, or production access.

The installer produces a Vincent worker capable of reaching standalone READY without CIC Station.

## Interaction and destructive boundary

Vincent automates safe appliance defaults but leaves deployment-specific network and storage choices to the operator.

The Debian Installer must present normal interactive choices for:

- network interface selection;
- Wi-Fi SSID/passphrase when applicable;
- target disk;
- partitioning method/layout;
- final disk-write confirmation.

Vincent must not force guided partitioning, LVM, whole-disk use, a fixed partition recipe, target disk, network interface, SSID, or passphrase.

The active Vincent boot/install medium is a special exception: it is not a legitimate installation destination and must be excluded from the disks offered for partitioning. The exclusion must not automatically select any remaining disk.

## Account boundary

Installation creates/uses the dedicated locked `vincent` service identity for runtime automation. A conventional human account is not required for routine worker operation. Root/human recovery access is separately controlled.

## Build and provenance boundary

Every installer build has a unique monotonically increasing installer build number. Build validation correlates:

- exact Vincent source commit used for the image;
- Debian source/version/architecture and verified source hashes/signatures as applicable;
- installer build number;
- ISO filename and supported volume/media identity;
- build manifest/checksums;
- image inspection/validation evidence;
- installed immutable installer provenance.

Installer build identity is not the Vincent software Semantic Version. Vincent may update later while preserving the original installer provenance.

## Network preflight and physical-test evidence

Installer development may collect sanitized preflight evidence needed to diagnose physical-network failures, including resolver configuration, direct DNS reachability, Debian mirror HTTP(S) reachability/interception signals, and package-source availability.

Preflight evidence must never print Wi-Fi passphrases, tokens, private keys, provider credentials, or other reusable secrets.

## Bootstrap sequence

```text
verified Debian installer source
  -> reproducible remaster from exact Git commit
  -> image inspection + manifests/checksums + secret/obsolete-name scans
  -> exact-device operator-authorized USB flash
  -> interactive network configuration
  -> active-media exclusion
  -> interactive target disk/partitioning/final write confirmation
  -> Debian base + Vincent prerequisites
  -> Vincent first-boot/runtime installation
  -> dedicated locked vincent service identity
  -> local worker identity generation
  -> self-tests/status/diagnostics
  -> standalone READY / unassigned
```

Provider/project/CIC Station authentication occurs after the public bootstrap boundary through the appropriate supported operator/enrollment workflow.

## Bundled source verification

Installer build 0024 embeds `platform.tar.gz`, `payload-manifest.json`, and the verifier. Debian installation copies them to `/opt/vincent-installer`. First boot verifies SHA-256, the Git archive commit, and independent runtime/installer metadata before extracting or executing the source. This is integrity checking within the trusted installer image, not a replacement for authenticating the complete installer image.

The bundled package installs with no package index or Git fetch. A resumed installation verifies existing source and preserves unexpected modifications for explicit recovery. Optional toolchain/provider provisioning remains online pending the standalone READY work in #37/#44. Physical acceptance of build 0024 remains pending.

## Online installer evolution

A proposed Vincent 1.1 path (ADR-0010) allows a compatible online installer to fetch the current approved Vincent software release from the trusted public release channel while retaining deterministic fallback to its validated bundled payload. Until that ADR is accepted/implemented, the installer uses its validated bundled Vincent payload followed by supported in-place Vincent updates.

## Physical acceptance

Installer correctness is demonstrated through reproducible clean installs on representative hardware. Current development intentionally uses expendable hardware for repeated destructive installer testing while keeping a persistent worker available for useful development; that temporary lab strategy belongs in `STATUS.md`/test evidence rather than the permanent product architecture.
