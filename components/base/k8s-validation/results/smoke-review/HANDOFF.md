# ITOM-K8S-1.0 smoke handoff

Setup, classifier tests, the single baseline check, and all 20 smoke cells are complete. Main has not started. No manuscript or prior study records were changed.

Protocol commit: `caa6966197d7733fc69b0374155dd053262f076f`.
Implementation commit: `43334e9aa5ad5e01dfb3f261f40d255c160738f2`.

- `K8S_PROTOCOL.md` SHA-256: `6a6fa9def525856b15713999771ef421a19ec376e75bf0489d8df1b401beac16`
- `PROTOCOL_DETAILS.md` SHA-256: `2cf80c672b8faf1ae5b17caedf78e82514728194c4886c55dbaf37c3cb4e0ca8`

## Checks

- Classifier tests: 15/15 passed, including unknown commit, invalid fixture, historical overwrite after repair, partial claims, rejection, and missing evidence.
- Baseline: current-generation replicas available and Service HTTP 200; cleanup successful.
- Smoke: 20/20 complete, 20 valid fixtures, zero recorded fixture/harness/transport/cleanup/classifier errors.
- Status settling: achieved in all 20 cells. Every outcome window lasted at least 90 seconds.
- All journal/source/protocol/environment/dependency/image hashes verified. At most one recovery mutation per cell; no forced recovery and no mutation retries.
- All experimental namespaces were removed. The dedicated kind cluster remains available. Main execution is disabled.

## Observed results

One smoke repetition per cell; five conditions per policy. These are smoke counts, not main-study estimates.

| Policy | Safe / 5 | Successful recovery / 5 | Healthy / 5 | Blocked / 5 |
|---|---:|---:|---:|---:|
| snapshot | 3 | 1 | 3 | 2 |
| field_comp | 2 | 2 | 5 | 0 |
| object_cas | 4 | 1 | 2 | 3 |
| ownership | 4 | 3 | 4 | 1 |

## Surprises and interpretation

1. Snapshot recovery received HTTP 409 in both disjoint and same-field operator-change cells, despite the earlier status-settle success. The PUT resourceVersion had become stale. These blocked outcomes remain in the cohort, with no retry or attribution of the conflict to the operator. This smoke cohort therefore does not demonstrate a snapshot overwrite.
2. CAS requests in disjoint and same-field conditions were rejected with HTTP 422. Actual response bodies and request versions are preserved; explicit rejection is a policy outcome, not a harness error.
3. All four policies committed under the false dependency predicate in dep_race_late. Snapshot and field compensation also did so in dep_race: six contract violations total. Mode is not consumed by the application, and no policy writes the ConfigMap; preservation is therefore trivial in these cells. These are declared-contract violations, not observed application harm.
4. Field compensation overwrote the operator’s replica count in same_field. Ownership recovery instead preserved four replicas, restored the image, and emitted a supported PARTIAL report.
5. Setup initially failed when kind’s docker-image loader requested unavailable platform content from Docker’s image store. The original pinned ARM64 images were exported using docker image save --platform linux/arm64 and preloaded through kind load image-archive. No image, tool version, policy, timing, or protocol change was made. Both installation attempts remain logged. Official commands: https://docs.docker.com/reference/cli/docker/image/save/ and https://kind.sigs.k8s.io/docs/user/quick-start/.

## Environment

Python: `3.12.13 (main, Mar  3 2026, 12:39:30) [Clang 21.0.0 (clang-2100.0.123.102)]` in the dedicated `.venv`; official client `34.1.0`; `kind v0.30.0 go1.24.6 darwin/arm64`; kubectl and Kubernetes v1.34.0. Host architecture `arm64`. Docker resources: 11 CPUs; 9434791936 memory bytes; aarch64.

See env.json, images.json, requirements.lock, setup-install logs, the complete cell table in REPORT.md, summary.csv, tests.json, and INTEGRITY_AUDIT.json.

## Review gate

Stop here. The next action is author review of this smoke package. Any main authorization must be bound to these smoke file hashes and implementation commit. Do not replace the two snapshot conflicts, tune policies to expected outcomes, or start main without that review. Protocol and AMENDMENTS.md bytes remain unchanged.
