# Diagnosis of the two original snapshot HTTP 409s

Prepared UTC: 2026-11-01T01:02:26.435165+00:00. Read-only diagnosis; no additional run or policy change.

| Original cell | Operator acknowledgment RV (seq 51) | Fresh snapshot GET RV (seq 53) | Observer GET RV (seq 56) | PUT RV (seq 59) | Post-rejection RV (seq 62) |
|---|---|---|---|---|---|
| 18: snapshot/disjoint | 7883 | 7883 | 7883 | 7883 | 7890 |
| 19: snapshot/same_field | 8342 | 8342 | 8342 | 8342 | 8350 |

Both fresh GET requests (seq 52) follow the successful operator PATCH responses (seq 51). The PUT uses the fresh GET’s RV, not the earlier policy pre-read RV. The two observer-only reads between preparation and dispatch do not refresh the prepared PUT. Each PUT received HTTP 409 / Conflict; no recovery retry or second mutation occurred.

## Timing and controller evidence

### disjoint

- Injection acknowledged: 2026-11-01T00:29:26.060165+00:00 (seq 51).
- Fresh GET requested: 2026-11-01T00:29:26.060637+00:00; returned: 2026-11-01T00:29:26.064066+00:00 (seq 52–53).
- PUT logged for dispatch: 2026-11-01T00:29:26.076318+00:00; HTTP 409 returned: 2026-11-01T00:29:26.088835+00:00 (seq 59–60).
- Fresh GET response to PUT request log: 12.245 ms.
- First post-rejection GET returned: 2026-11-01T00:29:26.098347+00:00 (seq 62).
- Deployment generation remains 3; full desired spec is unchanged between the fresh GET and post-rejection GET.
- status.observedGeneration changes 2 → 3.
- kube-controller-manager/status managedFields time changes 2026-11-01T00:29:19Z → 2026-11-01T00:29:26Z.

Status delta:
```diff
--- fresh-GET/status
+++ post-rejection-GET/status
@@ -17,8 +17,6 @@
       "type": "Progressing"
     }
   ],
-  "observedGeneration": 2,
-  "replicas": 3,
-  "unavailableReplicas": 3,
-  "updatedReplicas": 3
+  "observedGeneration": 3,
+  "replicas": 3
 }
```

### same_field

- Injection acknowledged: 2026-11-01T00:31:10.958208+00:00 (seq 51).
- Fresh GET requested: 2026-11-01T00:31:10.958872+00:00; returned: 2026-11-01T00:31:10.968572+00:00 (seq 52–53).
- PUT logged for dispatch: 2026-11-01T00:31:10.982062+00:00; HTTP 409 returned: 2026-11-01T00:31:11.002098+00:00 (seq 59–60).
- Fresh GET response to PUT request log: 13.467 ms.
- First post-rejection GET returned: 2026-11-01T00:31:11.008284+00:00 (seq 62).
- Deployment generation remains 3; full desired spec is unchanged between the fresh GET and post-rejection GET.
- status.observedGeneration changes 2 → 3.
- kube-controller-manager/status managedFields time changes 2026-11-01T00:31:04Z → 2026-11-01T00:31:10Z.

Status delta:
```diff
--- fresh-GET/status
+++ post-rejection-GET/status
@@ -17,8 +17,8 @@
       "type": "Progressing"
     }
   ],
-  "observedGeneration": 2,
+  "observedGeneration": 3,
   "replicas": 3,
-  "unavailableReplicas": 3,
+  "unavailableReplicas": 4,
   "updatedReplicas": 3
 }
```

## What can and cannot be established

The last pre-dispatch Deployment GET still returned the PUT’s RV. The 409 establishes that the version supplied by the client was stale when the server checked the update. The immediately following GET shows a newer RV, unchanged desired spec/generation, and updated status owned by kube-controller-manager. This is strong evidence consistent with controller status activity invalidating the conditional PUT. There is no additional operator or harness Deployment mutation between the injection acknowledgment and the recovery request.

The client journals do not capture the controller’s own API requests, storage transaction times, or a continuous watch stream. Consequently, they cannot identify every intervening RV or prove the precise controller write time, whether it preceded client PUT dispatch or occurred while the PUT was in flight, or whether a single update explains the entire RV gap. managedFields timestamps have only second precision. Resource versions are opaque identifiers, not counts of Deployment writes. Do not present a directly observed controller write strictly between the fresh GET and PUT dispatch.

The status-settle wait preceded the operator injection. Both injections raised Deployment generation from 2 to 3, so they could trigger new controller status work after that earlier settle condition passed. This explains why pre-injection settling did not guarantee a stable RV through the subsequent PUT; it does not justify attributing a later write to the operator.

## A1 technical check

Kubernetes v1.34.0 Deployment strategy returns true from AllowUnconditionalUpdate(). This supports a PUT without metadata.resourceVersion for this resource type; it is not a guarantee that every future update must succeed. No live probe/update was executed for this check. Source: https://github.com/kubernetes/kubernetes/blob/v1.34.0/pkg/registry/apps/deployment/strategy.go#L133-L135
