# Related-artifact inspection and claim boundary

Inspected before held-out model calls. This is a targeted comparison, not an exhaustive novelty search or a performance replication.

RAC repository tree pinned to `068c327ab3f9b79a86a39503946e26320b74b97a`. Exact inspected blob hashes and URLs are in `artifacts/RELATED_ARTIFACT_INSPECTION.json`.

- The recovery manager constructs a rollback plan, extracts compensation arguments, invokes the configured executor, and records compensation success/failure. This makes compensation-handler semantics relevant to preservation under external writes.
- The sequential execution lock serializes compensatable calls sharing that lock. Its inspected implementation is an in-process lock; this inspection does not establish coordination with unrelated external writers.
- The example inventory handler returns reservation/release confirmations. It is not a versioned configuration-store implementation. No claim is made that this example represents every RAC adapter.
- The actual `LICENSE` file contains Apache License 2.0; the README's final licensing sentence differs. No upstream code was copied or executed, so this package does not assert a license interpretation for redistribution of that library.

These observations motivate an explicit external-writer preservation contract; they do not show RAC is unsafe or inferior. The present baseline names are conventional techniques implemented here, not RAC, Atomix, Cordon, Kubernetes, or any other named system.

The guard-precision paper's inspected version specifies scheduler, pipeline, storage, and IAM mutation templates, including rollback and schema migration; it promises a code release but supplies no repository link in the inspected reproducibility section. Therefore a source-code comparison of that artifact could not be completed from the linked paper. Its atomic guard and predicate-precision results substantially overlap the present mechanism discussion. Our narrower extension evaluates fresh, multi-step recovery trajectories after commitment, preserved external obligations, report citations, and a small running HTTP data plane. No priority or new-concurrency-primitive claim is warranted.

Primary sources: [RAC paper](https://arxiv.org/html/2605.03409v1), [RAC pinned repository](https://github.com/wso2-incubator/research-rac/tree/068c327ab3f9b79a86a39503946e26320b74b97a), [guard-precision paper](https://arxiv.org/html/2609.29522v1), [compensating transactions](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction), [Kubernetes Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/).
