# ITOM public-release artifact v19

Prepared for the AGENT 2027 manuscript. Repository URL: https://github.com/santoshsibyala/itom-recovery-eval. This repository is private pending author review. It has no DOI. No package-wide redistribution license is assigned here; upstream RAC retains its included license.

## Contents

- `manuscript/`: v19 PDF and editable Markdown/LaTeX, the IEEE builder and the vector-only failure diagram.
- `heldout_v03/`: initial held-out and running-service source, protocol manifests, synthetic traces, provider request/response journals, baseline records and analysis outputs.
- `followup_v05/`: stronger-evidence and atomic-runtime study, conventional controls, typed and native-function sensitivity cohorts, initial/calibration sources, source manifests, raw records and analysis outputs. Its report directory contains initial and corrected RAC integrations, frozen upstream source/license and evidence-specificity diagnostics.
- `critical_review_v04/`: post-hoc scientific audit source and results. Private review materials are excluded.
- `prototype_v02/itom/`: original utility modules imported by held-out code. Development-pilot records and live billing ledgers are excluded.
- `k8s-validation/`: frozen protocols, amendment A1, implementation, environment/image records, original smoke, smoke-A1 and 200 main records, computed tables, classifiers, analysis and original provenance manifests. No policy identifiers were renamed.
- `human_review/`: published aggregate confusion matrix and resolution counts only.
- `supplement/`: tables moved from the paper and record-level computation of the three offline comparison counts.

## Read-only validation

Use Python 3.11–3.13. From the package root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 verify_public.py
PYTHONDONTWRITEBYTECODE=1 python3 verify_public.py --replay
```

The first command verifies every release hash, recomputes the Kubernetes summary from the 200 stored main records, reclassifies those records using the preserved classifier, checks the service-control headline, and recomputes human agreement from the aggregate matrix. The optional second command additionally replays archived initial and follow-up traces using the preserved engines and scorers. Replay uses temporary files and makes no provider, Docker or Kubernetes calls. These checks are internal artifact verification, not external reproduction or new experimental runs.

Original scripts that check private account ledgers, local approval files, Git commits, or host-specific tools cannot all run unchanged in this filtered release. Use `verify_public.py` for release validation. Runtime scripts such as `study.py`, `run.py`, `setup.py` and `main_runner.py` are included for inspection/reproduction planning; they are not invoked by these checks. Do not mistake replay for a new experiment.

## Policy names

Kubernetes raw `field_comp` maps to **Field patch** in the paper: a field-level strategic-merge patch without ownership or predicate checks at recovery dispatch, after the shared initial mode gate. Offline raw `field` is the different **field compensator**, which checks ownership and predicates. The raw names are unchanged.

The three offline condition-level comparisons are reproduced from the record list and formulas in `supplement/SOURCE_VERIFICATION.json`. Object CAS blocks full recovery in all 12 disjoint offline runs, but six make safe partial commits; Kubernetes B specifically means no commit.

## Privacy and source integrity

Read `EXCLUSIONS.md` for the complete exclusion policy and withheld record classes. Original reviewer forms, identities, individual disclosures and blinding keys are not included. `PRIVACY_CHECK.json` records the scan and its scope. The paper retains its approved aggregate review disclosures and AI-assistance acknowledgment.

`PUBLIC_MANIFEST.json` is authoritative for this filtered release. Older manifests describe the original experiment workspace and may include excluded administrative files. Original selected source/data bytes remain unchanged. The manuscript build uses standard IEEE conference typography; its already-built vector PDF is portable, while regenerating the figure helper requires ReportLab and the specified Times New Roman font files (or an explicitly supplied metrically appropriate local font).

## Manuscript version

v19 includes the approved final wording fixes and the private repository URL. Scientific records remain unchanged.
