# ITOM Kubernetes validation — first-study setup and smoke

Protocol frozen at caa6966197d7733fc69b0374155dd053262f076f. The candidate/DRAFT text is historical; the author approved the committed bytes. Do not edit the protocol or amendment file without approval.

Python 3.12 dedicated .venv; repo-local kind 0.30.0, kubectl 1.34.0; client 34.1.0. Exact dependency lock, binary hashes, image digests, architecture and Docker resources are recorded. Docker context orbstack, dedicated kind cluster itom-k8s-validation and dedicated .kubeconfig only. Setup downloads are permitted. Experiment pods use Never pull policy and images preloaded into the node.

Run `make setup`, `make tests`, `make baseline`, `make smoke` in that order. Setup is first-install only and refuses an existing cluster. Record a unique short alphanumeric SESSION before starting. Existing schedule/raw files are never overwritten. `make all` stops after smoke; `make run` fails deliberately. No main cohort is authorized yet.

Classifiers operate on evidence, not policy-name expectations. Event journals preserve requests, response codes, managedFields and subprocess output. Final records are exclusively created after cleanup. A session journal precedes each scheduled run. Twenty smoke cells use the frozen hash ordering. Each run has a full 90-second outcome window regardless of early health. Bad-state and status-settle timeouts retain the run. No recovery retry or force is allowed.

If interrupted, stop and retain the journal and schedule; do not restart the cohort or rerun its started cell. Mechanical interruption finalization and any continuation must retain the original cell identity. No automatic replacement is implemented. Main analysis and publication insert are deliberately deferred until smoke review.

The dependency mode is not consumed by the application. Dependency-race preservation is trivially expected; a recovery commit under mode v2 measures the declared contract, not observed application harm. These runs use deterministic policies, not LLM agents.

All outputs remain local; neither manuscript nor prior study records are modified.
