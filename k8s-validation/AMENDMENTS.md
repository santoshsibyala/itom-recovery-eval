# Amendment log

No amendments. ITOM-K8S-1.0-candidate has not been approved or frozen, and no setup validation, smoke, or main run has occurred.

After the author commits the protocol, every change must record UTC date, author approval, reason, exact affected files/semantics, prior and new commit/hash, data already observed, and whether new runs form a separate cohort. Never alter old raw records or silently substitute a policy/version/count.


## A1 — DRAFT ONLY / PENDING AUTHOR APPROVAL

Drafted UTC: 2026-11-01T01:02:26.435165+00:00.
Approval: **NOT APPROVED**. Effective date: none. Applied: **no**. Commit: **not created**. Main: **NOT APPROVED**. No supplementary run is authorized by this draft.

The opening pre-freeze paragraph above is retained as historical text. The protocol was subsequently frozen at `caa6966197d7733fc69b0374155dd053262f076f`; the original 20-cell smoke cohort was completed using implementation `43334e9aa5ad5e01dfb3f261f40d255c160738f2`. This appended proposal does not change those frozen semantics or their execution records.

### Proposed change

Only snapshot will send its single Deployment PUT **without `metadata.resourceVersion`** (the key must be absent, not null or an empty string). Keep baseline full `spec`, the initial predicate gate, the existing fresh metadata GET and its placement, live name/namespace/UID and other non-spec metadata, and omission of top-level status and managedFields. No retry, no force, at most one recovery mutation. Do not use the fresh GET to revise the baseline restoration plan or recheck the predicate.

The smallest proposed implementation change is to remove resourceVersion from the copied live metadata before building the snapshot PUT. The fresh GET remains to preserve all other request preparation and ordering. No source code is changed by this draft.

### Rationale

Author-stated original design intent: snapshot means “replace with the full baseline manifest, without resourceVersion.” The frozen protocol instead included resourceVersion, making snapshot a conditional update and introducing a second version-checked recovery policy. A1 restores the specified unconditional snapshot design intent. This issue was identified from smoke, before main; it is not based on main results. The original policies were not literally identical: snapshot used a fresh RV and only the initial predicate, whereas object_cas tests the original pre-read RV and rechecks the predicate. A1 removes snapshot’s unintended RV precondition without changing object_cas.

Kubernetes v1.34.0’s Deployment strategy permits unconditional update: `AllowUnconditionalUpdate()` returns true. Source: https://github.com/kubernetes/kubernetes/blob/v1.34.0/pkg/registry/apps/deployment/strategy.go#L133-L135 . Omitting RV removes that client version precondition; all observed rejection/error outcomes must still be retained, not retried or forced to succeed.

### Evidence already observed

Original smoke: 20 runs, including snapshot/disjoint (018) and snapshot/same_field (019), both HTTP 409. Their injection acknowledgment, fresh GET, and PUT RVs were respectively 7883/7883/7883 and 8342/8342/8342. Fresh GETs occurred after injection acknowledgments. Post-rejection RVs were 7890 and 8350 with changed controller status and unchanged desired specs. Client journals support a status-update race but do not timestamp the controller’s storage write relative to PUT dispatch. Full diagnosis and event extracts: `results/a1-draft/SNAPSHOT_409_DIAGNOSIS.md` and `SNAPSHOT_409_EVIDENCE.json`.

All original 20 smoke records, journals, schedules, tests, reports, and manifests remain unchanged and will be reported as the original cohort. They must not be relabeled as A1 executions, overwritten, rerun as replacements, or pooled with supplementary smoke to claim an unchanged policy. No main records exist.

### Scope and proposed affected files after approval

- Scientific change: **snapshot only**. No other policy, condition, metric, timeout, main repetition count, or original smoke run count changes.
- `K8S_PROTOCOL.md`, section 3 snapshot row: replace the fresh-RV update-precondition wording with “replace the Deployment’s full specification with its baseline specification using one PUT without metadata.resourceVersion; retain the fresh GET only for live metadata.”
- `PROTOCOL_DETAILS.md`, section B: retain the existing GET order; clarify that snapshot’s live metadata read does not place resourceVersion in its PUT. Observer-only reads still do not alter policy decisions.
- `PROTOCOL_DETAILS.md`, section C snapshot bullet: baseline full spec plus live name/namespace/UID/non-spec metadata, explicitly omitting metadata.resourceVersion, metadata.managedFields, and top-level status. Keep one mutation, no retry/force/fallback, and retain explicit rejection as a blocked outcome.
- `run.py`: remove only snapshot’s copied metadata.resourceVersion; add explicit provenance/phase support and a gate for the separate five-cell supplementary cohort. No live behavior changes now.
- Focused request-construction tests after approval must verify absence of snapshot RV, retention of baseline full spec, unchanged object_cas RV test, and unchanged no-retry/no-force behavior.
- `AMENDMENTS.md` and cohort documentation: record actual approval, amendment/implementation commits, hashes, and separate supplementary cohort identity when available.

### Approval-dependent supplementary smoke plan

Only after explicit author approval: implement and commit A1, record the author approval and resulting commit/hash values, verify focused tests, then execute **five snapshot-only cells** (clean, disjoint, same_field, dep_race, dep_race_late), one repetition each, in a separate cohort named `smoke-A1`. Keep the seed 20261101 and existing SHA-256 ordering algorithm, with phase string `smoke-A1` and repetition 1. Namespace identifiers must use a DNS-valid lowercase phase spelling while retaining `smoke-A1` in cohort metadata and schedule hashing. Store raw records in `results/smoke-A1/` with separate schedules/journals/manifests; bind every record to original freeze, approved A1, effective protocol hashes, implementation, environment and image digests.

These five supplementary cells are additive diagnostic runs, not replacements or changes to the original 20-cell smoke cohort or the planned 200-cell main cohort. Use the same pinned environment/images, setup, policies apart from snapshot RV omission, conditions, classifiers, and timing. No main run is authorized by A1 approval. Stop after the five cells for author review again.

### Provenance fields (pending approval)

- Original protocol commit: `caa6966197d7733fc69b0374155dd053262f076f`.
- Original K8S_PROTOCOL.md SHA-256: `6a6fa9def525856b15713999771ef421a19ec376e75bf0489d8df1b401beac16`.
- Original PROTOCOL_DETAILS.md SHA-256: `2cf80c672b8faf1ae5b17caedf78e82514728194c4886c55dbaf37c3cb4e0ca8`.
- Original implementation commit: `43334e9aa5ad5e01dfb3f261f40d255c160738f2`.
- Original smoke handoff manifest SHA-256: `afe1a5632c4930f54a9a08a9d180c6bb46b17dfebf2f377c25620e41ffee3934`.
- Author approval / approval UTC: **pending**.
- Approved amendment commit / effective protocol hashes / implementation commit: **pending; not fabricated or assigned in advance**.
- Supplementary cohort status: **not started**.


## A1 — APPROVED / EFFECTIVE PROTOCOL CHANGE

The preceding draft is retained as the reviewed historical proposal. This approval record supersedes its pending/not-applied status.

- Approval: **Santosh Sibyala**, explicitly in this chat: “A1 approved as drafted.”
- Approval recorded UTC: 2026-11-01T01:10:29.691488+00:00 (recording time; the chat did not supply a separate timestamp).
- Authorization: apply A1, add focused tests, commit, execute only the five snapshot smoke-A1 cells, and stop. **Main remains NOT APPROVED.**
- Applied protocol semantics: omit metadata.resourceVersion from snapshot PUT only; preserve the existing fresh metadata GET, full baseline spec, ordering, one mutation, no retry, and no force. All other policies, conditions, metrics, timeouts, and original run counts remain unchanged.
- Original freeze: `caa6966197d7733fc69b0374155dd053262f076f`. Original smoke implementation: `43334e9aa5ad5e01dfb3f261f40d255c160738f2`.
- Effective protocol hashes:
- `K8S_PROTOCOL.md`: `08fd3e7f6f40361b8a7da4a6dec67d5152698bb1d35fcb2e7da13cc5ded11aa2`
- `PROTOCOL_DETAILS.md`: `345300a594b0c8a295623f677b4170ed00760b5a4c0220fcb5aa0be5e094821c`
- Amendment commit: the commit containing this effective protocol change; its resolved ID will be appended in the pre-run receipt after commit creation.
- Implementation commit: to be resolved after the code and focused tests are committed, before supplementary execution. A subsequent provenance-only commit will record both IDs here, avoiding a self-referential commit hash.
- Supplementary cohort: smoke-A1, five snapshot cells, one per condition, additive and stored separately. Original smoke remains unchanged and reportable.

### A1 pre-run commit receipt

- Approved by: **Santosh Sibyala**; approval recorded UTC: `2026-11-01T01:10:29.691488+00:00`.
- Amendment commit: `9e5e04e7ac6591035f51f7bf5b4727fe1a9fb01c`.
- Implementation commit (snapshot change, focused tests and cohort gate): `0ff095f2db1bdf45e6c4b003c0714658fd623f88`.
- Effective `K8S_PROTOCOL.md` SHA-256: `08fd3e7f6f40361b8a7da4a6dec67d5152698bb1d35fcb2e7da13cc5ded11aa2`.
- Effective `PROTOCOL_DETAILS.md` SHA-256: `345300a594b0c8a295623f677b4170ed00760b5a4c0220fcb5aa0be5e094821c`.
- Machine-readable approval: `A1_APPROVAL.json`, SHA-256 `d9952ec87aee4ab388eee7be0060fab2243741e3af09cad751fb528db7380de8`.
- This receipt is committed separately without changing implementation; each run records its execution commit as well as the implementation commit.
- Authorized execution: the five-cell snapshot-only smoke-A1 cohort, then stop. **Main remains NOT APPROVED.**
- Original smoke artifacts remain unchanged; supplementary status at this pre-run receipt: not started.


## Main cohort — AUTHOR APPROVAL (no scientific amendment)

- Approved by: **Santosh Sibyala** in this chat: “Main run approved.”
- Approval recorded UTC: `2026-11-01T01:57:31.252211+00:00` (recording time; no separate message timestamp supplied).
- This supersedes prior main-not-approved statements for the one authorized `m20261101` main cohort only.
- Bound original freeze: `caa6966197d7733fc69b0374155dd053262f076f`.
- Bound A1 amendment: `9e5e04e7ac6591035f51f7bf5b4727fe1a9fb01c`.
- Bound implementation: `0ff095f2db1bdf45e6c4b003c0714658fd623f88`; reviewed execution/provenance commit: `9a55e7f2e347ff64aa85bb8fccdce19e892a09fb`.
- Effective `K8S_PROTOCOL.md` SHA-256: `08fd3e7f6f40361b8a7da4a6dec67d5152698bb1d35fcb2e7da13cc5ded11aa2`.
- Effective `PROTOCOL_DETAILS.md` SHA-256: `345300a594b0c8a295623f677b4170ed00760b5a4c0220fcb5aa0be5e094821c`.
- Reviewed smoke manifest `results/smoke-review/HANDOFF_MANIFEST.json` SHA-256: `afe1a5632c4930f54a9a08a9d180c6bb46b17dfebf2f377c25620e41ffee3934`.
- Reviewed smoke manifest `results/smoke-A1-review/MANIFEST.json` SHA-256: `ae605c1acd2a0f04a1171423a67c75e3abffe9a008a2f6f7e9a3027a56ef7a48`.
- Approved work: 4 policies × 5 conditions × 10 repetitions = 200 main runs, fixed seed 20261101 and existing SHA-256 within-repetition order; all policies, timings and metrics unchanged.
- Resume: preserve every started cell; mechanically finalize interrupted journal evidence without replacing or repeating that cell; continue only not-started cells in saved order. Preserve all unknowns, failures and denominator counts.
- After completion: generate summary.csv, table.md, provenance manifest and PAPER_DRAFT.md, then stop for review. **Do not edit the manuscript.**
- The bound A1 experiment/classifier files remain byte-identical. New main-only orchestration routes records to results/raw, records repetition metadata, implements the frozen resume rules, and generates read-only analysis. This is not a policy, timing, condition, schedule or metric amendment.
- Main approval receipt: `MAIN_APPROVAL.json`. The main execution commit and source hashes are recorded in each schedule and run; resolved orchestration commit is appended below after commit creation.
- Prior approval statements in this log remain historical. Their archived bytes are available at the bound reviewed commit, so the original smoke manifests remain verifiable.

### Main pre-run orchestration receipt

- Main approval/orchestration commit: `62aee24f24819111271438756f6443fb61883537`.
- Bound scientific implementation remains `0ff095f2db1bdf45e6c4b003c0714658fd623f88`; no approved experiment or classifier file changed.
- Main approval receipt SHA-256: `e329ed2c2fa666d0d91dd53dbab3f087c5994095e9915067960faf4a602464c8`.
- This provenance-only follow-up commit is recorded as execution_commit in the saved main schedule and every run.
- Status at receipt: main authorized, not yet started; tests and read-only preflight precede launch.
