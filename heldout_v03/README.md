# ITOM structural holdout and running-service validation v0.3

Start with [the completion report](COMPLETION_REPORT.md) and [paper draft](paper/ITOM_Research_Draft_v01.pdf). The editable manuscript is `paper/ITOM_Research_Draft_v01.md`; verified results are `analysis_final/results.json`.


This package extends the v0.2 development study without changing IAM. All model calls use the original ledger at `../prototype_v02/live_state/budget.sqlite3`; its $15 cap includes every earlier ITOM attempt. The preserved v0.2 ZIP remains the historical snapshot. Its working ledger necessarily changes as new authorized attempts append; do not reset it or describe its old release checksum as a current ledger checksum.

## Frozen studies

- `study/manifest.json`: 216 structural held-out model episodes, six new template structures, three operational families, six interference/failure variants, two prompt arms, three models, one draw per cell. Also 108 deterministic baseline trajectories.
- `service_study/manifest.json`: 42 fresh model episodes and 63 baseline runs on seven conditions of one route/proxy application. Real loopback HTTP requests execute in separate proxy and backend processes. A distinct operator process triggers dependency interference at a controlled barrier.
- The running-service control plane reuses the configuration engine. Application response digests and network execution are separate from that engine. This is a local data-plane demonstration, not Kubernetes, ServiceNow, production validation, or independent validation of the entire simulator.

Service health requires at least 19 correct HTTP-200 SHA256 responses out of 20 in each of three terminal workload windows. Requests have 10ms spacing; these are short bounded windows, not a production SLO. The `tls` field is illustrative protected configuration metadata; this HTTP test does not implement TLS. Agents see the same synthetic configuration-health tool as the simulator; measured data-plane health is out-of-band. Configuration and operational recovery are reported separately.

## Reproduce without model charges

Use Python 3.11 or newer from this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_core.py -v
# Local sockets and subprocesses are needed for these tests, but no paid APIs:
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_service.py -v
# After all cohorts complete, verify traces and rebuild analysis in a fresh directory:
PYTHONDONTWRITEBYTECODE=1 python3 -m analysis.results --output analysis_reproduction
```

`recovery.study heldout` and `service_lab.study models` are PAID commands. They check source freezes and the shared budget, preserve journals, and never automatically retry an attempted call. `service_lab.study baselines` makes no model calls. Existing trace IDs are not rerun. Do not rename IDs or reset the ledger to bypass preserved attempts.

## Baselines and interpretation

Snapshot restoration is a negative control that knows the pre-remediation `tls='strict'` default and overwrites it along with target fields. It is not an information-matched agent arm. Object CAS uses the version recorded immediately after remediation and blocks an object if intervening writes change that version. Field compensation checks public ownership, predicates, recovery ordering, and current versions. Only per-resource CAS is available; no baseline receives a global transaction. The three policies are distinct, unlike the v0.2 public-runbook alias.

The two LLM arms share a safety-oriented base prompt; verify adds a checklist. Prompts, scenario structures, sources, limits, and the analysis unit were frozen before held-out model responses. Scenario authors know the contracts; this is a structural holdout relative to v0.2 model development, not a blind benchmark. One call sequence per cell does not establish robustness to sampling seeds.

The primary contrast is within-model verify-minus-ordinary unsupported completion, equally averaged over six template clusters. The predeclared secondary recovery contrast uses clean/disjoint variants. Bootstrap intervals use 10,000 paired template resamples stratified by three families. Six clusters and two templates per family provide weak generalization; intervals are descriptive, not evidence of adequate power or a provider ranking.

The paper draft must keep the pilot, held-out, deterministic, and service denominators separate. Independent human review remains pending. The blinded materials contain blank forms, not fabricated judgments. See `ARTIFACT_COMPARISON.md` for inspected prior art and the limits of the novelty comparison.
