# Outcome Analytics & Learning Loop

AI Job Agent records application states, match scores and immutable application
events. This provides an outcome-analysis boundary without pretending that a
trained learning model already exists.

## v1 metrics

- Application funnel: Discovered -> Matched -> Approved -> Applied / Rejected
- Transition rates between states
- Apply rate by match-score bucket
- Apply rate by job source
- Future explicit outcomes: interview, response and offer rates

The pure analytics implementation is backend/evaluation/outcome_metrics.py.

## Safe learning loop

1. Export anonymized application outcomes.
2. Freeze the ranking configuration/version used for each outcome.
3. Segment by source, role family and score bucket.
4. Review false positives and false negatives.
5. Propose ranking changes offline.
6. Re-run the frozen golden benchmark.
7. Ship only if offline metrics improve without unacceptable regressions.
8. Record the new ranking version and evaluation report.

v1 does not automatically retrain or change ranking weights from user outcomes;
that avoids an uncontrolled feedback loop and selection bias.
