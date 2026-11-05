# Smoke-only interpretation note; not a manuscript change

No main results are available. In dep_race_late, injection occurs after the agent decides to write, so it cannot observe the change before dispatch. Any committed write is expected to commit under the false predicate regardless of agent behavior. This cell tests the residual check-to-write window, not agent judgment. The application does not consume mode at runtime; the violation concerns the declared recovery contract rather than observed application harm.
