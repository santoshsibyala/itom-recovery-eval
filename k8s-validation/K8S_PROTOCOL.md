# ITOM preliminary Kubernetes control-plane validation

**Protocol:** ITOM-K8S-1.0-candidate. **Prepared:** 2026-10-31. **Status:** DRAFT; not approved, committed, or executed. Target completion: November 8, 2026.

## 1. Question and scope

Do deterministic recovery policies differ in preserving an operator's changes and respecting a dependency predicate on a real Kubernetes API server? This is a controlled mechanism check, not an LLM experiment or a replication of the SQLite transaction guarantee. One single-node kind cluster runs one application Deployment with a ConfigMap dependency, a Service, and a probe pod. Injected writes have prescribed ordering; they are not naturally occurring races. Ten repetitions measure repeatability, not ten independent applications. Existing IAM/ITOM records are untouched.

`PROTOCOL_DETAILS.md` is a normative part of this protocol. Both files must be reviewed and committed before setup validation or experimental runs. Scientific choices, run counts, metrics, and timeouts are frozen by that commit. Changes require dated entries in `AMENDMENTS.md` and author approval; no policy tuning after observing results.

## 2. Environment and workload

Use kind **v0.30.0**, kubectl **v1.34.0**, Kubernetes **v1.34.0**, and Python client **kubernetes==34.1.0**. Pin the node to `kindest/node:v1.34.0@sha256:7416a61b42b1662ca6ca89f02028ac133a309a2a30ba309614e8ec94d976dc5a`. Use `hashicorp/http-echo:1.0.0` and `curlimages/curl:8.16.0`. Setup resolves and records their immutable digests before any workload run; smoke and main must use the same images. No silent version substitution. Python 3.11–3.13 in a dedicated virtual environment; record the exact interpreter. Do not use Python 3.14. Record dependencies, Docker versions, architecture, host resources, and client/server versions in `results/env.json`.

The application starts at two replicas, uses `Recreate`, exposes port 5678 with HTTP readiness, and returns fixed text `itom-k8s-ok`. `APP_MODE` references `app-config.data.mode`, initially `v1`. It is a control-policy predicate, not an application-health oracle. The probe accesses the ClusterIP Service. All application/probe images are preloaded into kind and use `imagePullPolicy: Never`. The deliberately bad image is an absent local tag, also with pull policy Never.

No model inference or external service APIs are used. Setup may download tools, dependencies, and images. Runs use only local Kubernetes and cluster traffic, with no registry pulls. Read-only documentation lookup and code preparation are not experimental execution.

## 3. Design and sequence

Main: **4 policies × 5 conditions × 10 repetitions = 200 runs**. Smoke: one repetition per cell, **20 runs**, stored separately and excluded from main analysis. One additional baseline readiness check belongs to setup, not either cohort. Run sequentially in fresh namespaces, then delete them. Use seed **20261101**, and the SHA-256 ordering rule in the details file to interleave conditions/policies reproducibly.

Each run: establish a healthy baseline; retain the baseline Deployment specification; apply the bad image and three replicas as field manager `agent`; observe whether service becomes unhealthy; read Deployment and ConfigMap; inject the condition; execute the policy once; emit its report; measure for the fixed window; capture final objects and clean up. Ownership transfer during fixture construction is explicit. Only setup/operator injections may force ownership. The ownership recovery policy never forces conflicts.

| Condition | Injected operator action |
|---|---|
| `clean` | None. |
| `disjoint` | Add container environment variable `OPERATOR_NOTE=preserve-me` after the pre-recovery read. |
| `same_field` | Set Deployment replicas to 4 after the pre-recovery read. |
| `dep_race` | Set ConfigMap mode to `v2` after the pre-recovery read, before any policy re-check. |
| `dep_race_late` | Set mode to `v2` after the policy's last predicate check, immediately before recovery dispatch. |

| Policy | Frozen behavior |
|---|---|
| `snapshot` | Use the initial predicate observation; replace the Deployment's full specification with its baseline specification using one PUT without metadata.resourceVersion (A1). Retain the fresh GET only for live metadata. |
| `field_comp` | Use the initial predicate observation; strategic-merge-patch only the named container image and replicas back to baseline. |
| `object_cas` | Re-check mode; if `v1`, JSON Patch with a test of the original Deployment resourceVersion followed by restoration of image and replicas. |
| `ownership` | Re-check mode and inspect current field ownership. Apply only agent-owned target fields as manager `agent`, `force=false`. Leave operator-owned fields unchanged. |

All predicate-check failures block writes. There is no recovery retry, fallback, or automatic policy repair. The local event order establishes the predicate at dispatch only when the injected update is acknowledged and no further ConfigMap writer exists.

## 4. Measurements and reporting

Record image restoration, final/expected replica count (4 for `same_field`, 2 otherwise), operator preservation, unsafe overwrite, commit under false predicate, blocked state, health, policy report/claimed fields, report support, pre/post managedFields, and all API requests/responses/status codes. Record UTC and monotonic timestamps, event order, namespace, repetition, source/protocol hashes, and errors with tracebacks. Unknown evidence yields null plus a reason, never a guessed success.

- **Safety:** no unsafe overwrite and no recovery commit under a false predicate.
- **Successful recovery:** safety, image restored, expected replicas reached, and operator change preserved where applicable. A block is not recovery.
- **Blocked:** no recovery request committed, with sufficient evidence to establish this.
- **Healthy:** the current Deployment generation is Available and the Service probe returns HTTP 200 within the outcome window.
- **Report supported:** claims match observations; a RECOVERED report additionally requires successful recovery. PARTIAL never certifies unclaimed outcomes. Exact rules are in the details file.

The application does not consume mode at runtime, and no policy writes the ConfigMap. In dep_race and dep_race_late, operator_preserved is therefore expected to be trivially true, and committed_under_false_predicate measures a violation of the declared recovery contract, not observed application harm. Paper text must state this explicitly.

Each cell retains its denominator of ten. Summaries show safety/successful-recovery/preserved/healthy counts, plus blocked and unsupported-report counts. Clean preservation is N/A. Report missing/unknown measurements, invalid fixtures, incomplete schedules, and harness errors separately; they never count as successes. No significance testing or production failure-rate estimate is planned.

## 5. Gates, preservation, and deliverables

After author review and protocol commit: setup → classifier unit tests → smoke → author review of smoke → main → analysis. Smoke surprises are findings; changes require approved amendments. Main results are never used to tune policies. No second main attempt replaces a failed run.

The harness writes append-only event journals and creates each final raw JSON once, including failures. Analysis reads raw records without modifying them. `make clean` removes only this experiment's infrastructure, never evidence. The first study's main run is gated on smoke approval; thereafter `make all` reproduces the frozen workflow in a new output directory from a machine with Docker, Git, make, and Python 3.11–3.13 in a dedicated virtual environment available; Python 3.14 must not be used.

Deliverables: immutable main raw records; environment and schedule manifests; `summary.csv`; `table.md`; `PAPER_DRAFT.md` with a setup paragraph ≤120 words, computed table, 2–3 computed result sentences, and a limitation sentence; reproduction README; tests; amendment history. Every numerical result in the paper insert must be generated by `analyze.py`. Expectations are not pass/fail criteria. Do not update the manuscript until observed results have been reviewed.
