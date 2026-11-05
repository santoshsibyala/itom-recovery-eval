# ITOM-LLM-K8S-1.1 staged extension package

Prepared for v25; local staging only. The underlying 1.0 and 1.1 records and v24 are unchanged.

## Included

- Frozen 1.1 protocol, native-transport mapping, prompt, schemas, classifier, harness and tests.
- Approval and freeze receipts, amendment 1.1-A1 and repair execution bindings.
- `results/main/`: invalid first launch. It skipped agent execution, made zero model requests and is excluded from results. Original scheduled runs 016–050 were not continued.
- `results/canary/`: real-cluster stub-agent lifecycle check; no model calls; excluded from analysis.
- `results/smoke/` and `results/smoke-analysis/`: ten smoke cells and their analyses.
- `results/main-b/` and `results/journals/`: the fresh 50-run cohort and original request/response and lifecycle evidence.
- `results/main-b-analysis/`: computed outcomes, behavioral measures, ordered reads, trigger/failure categories, model-ID audit, paper insert and verification.
- `comparison/gpt/` and `comparison/haiku/`: summary.csv, behavior.csv and ordered_reads.csv for each cohort. GPT ordered reads were derived additively from its preserved journals for v25 because the earlier package did not contain that file. The source cohort was not changed.

The manuscript uses only the combined outcome table. The behavior table and detailed read sequences remain here. Native model and transport changed together; the comparison does not isolate a model effect. Late-race injection occurs after the decision to write and tests the check-to-write window. The application does not consume ConfigMap mode at runtime, so false-precondition commits are contract violations, not measured application harm.

## Reproduction and provenance

Read LLM_K8S_PROTOCOL.md, TRANSPORT_MAPPING.md and AMENDMENTS.md before using the harness. Frozen source files retain their original local-path provenance and references to the 1.0 package and deterministic Kubernetes fixture. An execution environment needs those dependencies, pinned tools, a local cluster and separately supplied credentials. None are provisioned by opening this package. Protocol deadlines and approvals are historical records, not authorization to rerun experiments.

See EXCLUSIONS.md for omitted private/environmental files. SHA-256 hashes for this exact staged copy are in PACKAGE_MANIFEST.json. Raw and journal copies match source bytes.
