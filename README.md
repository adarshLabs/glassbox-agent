# glassbox-agent

## Eval run 1 — 21 Aug 2026

```
Tasks: 10 (7 expected pass, 3 expected fail)
Harness agreement: 7/10
Expected-pass tasks that passed: 7/7
Expected-fail tasks that failed correctly: 1/3
Median steps on passing tasks: 1
Anything that surprised you: the `matched` formula in run_evals.py inverts
correctness for the hits_step_cap and no_answer assert kinds - a task that
fails exactly as designed (t08 hitting the step cap) gets marked N. Also,
calculator() has no error handling, so when the model tries a non-arithmetic
workaround (e.g. pandas code for the CSV question) instead of the
CANNOT_ANSWER sentinel, eval() raises unhandled and the whole run crashes -
t09/t10 read as "no answer" for that reason, not because the agent declined
gracefully.
```
