# glassbox-agent

A tool-using agent written from scratch in Python — no LangChain, no LangGraph.
A reason–act–observe loop, a hard step cap, a prompted refusal convention, and
a programmatic evaluation harness that grades against assertions rather than
against how the output looks.

## How it works

`agent.py` runs a single loop. Each turn the model must reply with exactly one of:

```
TOOL: calculator
ARGS: <expression>
```

```
FINAL: <answer>
```

Tool results are appended to the conversation as observations and the loop
continues. It stops on `FINAL` or on the step cap.

- **Arithmetic is meant to go through the tool, never the model.** The prompt
  tells it to always call `calculator` rather than compute internally — this
  is a prompt instruction, not something the code enforces.
- **The expression is `eval`'d**, after normalizing `^` to `**` for exponents.
  Passing model output straight to `eval()` is not sandboxed; see Limitations.
- **A prompted refusal, mapped to `None`.** The prompt asks the model to reply
  `FINAL: None` when the tool can't help. `run()` converts that exact text into
  Python `None`, so a refusal reaches the harness as "no answer". The model is
  only asked to do this; nothing forces it to.

## Evaluation

Ten tasks with programmatic assertions. Seven are expected to succeed; three are
expected to fail, each for a different reason. A task counts as agreement when
the agent behaves the way the task predicted, so an expected failure that fails
correctly is a pass for the harness.

### The three failures are the point

- **t08** — ten Fibonacci numbers, one pair at a time. Needs 8+ calls against a
  cap of 5. Tests that the stopping condition actually stops.
- **t09** — total revenue in `data/sales.csv`. There is no file-lookup tool.
  Tests that a missing *capability* produces a refusal, not a guess.
- **t10** — 8% of today's USD/INR rate. Needs a figure the model cannot verify.
  Tests that a missing *fact* produces a refusal, not a guess.

An agent that "passes" t08 does not have a better planner — it has a broken cap.

---

### Run 1 — 21 Aug 2026

```
Tasks: 10 (7 expected pass, 3 expected fail)
Harness agreement:  8/10 as printed, under a broken scorer  (7/10 true)
Expected-pass tasks that passed: 6/7   (t07 hit the step cap)
Expected-fail tasks that failed correctly: 1/3
```

Three defects, all in the harness or the plumbing rather than in the reasoning.
Run 1 was a diagnosis; see Run 2 for what was fixed.

**1 · The scorer grades itself wrong, in two directions at once.**
`matched = (ok == (expect == "pass"))` double-counts the expectation — `ok`
already means "behaved as predicted." It marks t08 wrong for hitting the cap
exactly as designed, and would credit t09/t10 for *not* failing correctly. The
two errors can cancel into a plausible-looking total. **A harness bug that
moves the headline by one is far harder to notice than one that moves it by
five.** The correct fix is `matched = ok`.

**2 · `calculator()` has no error handling, so a bad expression crashes the
run.** If the model routes something non-arithmetic through the tool (e.g. an
attempted CSV lookup), `eval()` raises and the exception escapes `run()`
entirely. Inside `run_evals.py` that's caught by the outer `try/except` and
scored as a bare `None` — indistinguishable, at the harness boundary, from a
clean refusal. t09 and t10 currently read as "no answer" partly for this
reason, not only because the model declined gracefully.

**3 · A refusal isn't distinguished from any other answer.** `FINAL:
CANNOT_ANSWER — ...` is just text; `run()` doesn't special-case it into
`None`. It happens to score correctly against `run_evals.py`'s `no_answer`
assert (`answer is None`) only because a refusal string isn't `None` either —
the assert and the scorer bug above land right for these two tasks by
coincidence, not by design.

### Run 2 — 21 Oct 2026

```
id   expect  result  steps  secs   match  answer
t01  pass    OK      1      5.9    Y      '821.1'
t02  pass    OK      1      8.9    Y      '12676'
t03  pass    OK      1      9.1    Y      '1402.55'
t04  pass    OK      1      9.1    Y      '1010.0'
t05  pass    OK      1      8.9    Y      '1048576'
t06  pass    OK      1      9.2    Y      '30.0%'
t07  pass    OK      1      8.7    Y      '284.12'
t08  fail    OK      5      22.9   Y      None
t09  fail    OK      0      4.6    Y      None
t10  fail    OK      0      4.3    Y      None

harness agreement: 10/10
```

Changes since Run 1:

- **Defect 1 fixed.** The scorer is now `matched = ok`. t08 hitting the cap now
  counts as agreement.
- **Defect 3 fixed.** The refusal reply is now `FINAL: None`, and `run()` turns
  that text into Python `None`. This mattered: the model's text `"None"` is a
  string, and `"None" is None` is `False`. Before the conversion, t09 and t10
  refused correctly but still scored `N`.
- **Defect 2 not fixed.** `calculator()` still has no error handling, and
  `run_evals.py` still records a crash as `(None, 0)`. In this table a clean
  refusal and a crash on the first step look identical. t09/t10 show `None` at
  0 steps, which fits either. In an earlier run under the same scorer, t09 got
  there by routing `data/sales.csv` into `eval()` and raising `NameError`.
  10/10 is the true score only if both tasks refused rather than crashed.

### Was 10/10 real? — 21 Oct 2026

The outer `except Exception as e` in `run_evals.py` bound `e` and never used it,
so any crash was silently indistinguishable from a refusal. Printing it at the
point it is caught settles the question in one line.

**Nothing raised.** On a re-run with exceptions surfaced, no task printed an
error, so t09 and t10 reached `None` through the prompted refusal path. **The
10/10 stands.**

⚠ But the crash route is **latent, not absent.** Both tasks refused at **0 tool
calls**, which means `eval()` was never reached on this run — not that it is
safe. The same code produced the `NameError` above when the model chose to try
the tool before declining, and nothing makes that choice deterministic. A score
that depends on whether the model happened to reach for the tool is not a stable
instrument, which is the argument for fixing Defect 2 rather than for closing it.

Two further caveats, both visible in the run itself: per-task latency roughly
doubled between runs with no code change (t05 8.9s → 21.2s, t08 22.6s → 38.0s)
on the same free-tier model, and every number here is a single run. GAIA runs
each model three times and averages; this does not.

## Scoring decisions, disclosed

- **t06 sometimes returns `30%` or `30.0%`, not `30`.** The arithmetic is right; the `%`
  breaks a bare-number convention the prompt asks for but doesn't enforce.
  The harness strips `%`, `$` and commas before comparing, so this doesn't
  cost the task — but it's a leniency worth naming.
- **`hits_step_cap` asserts `answer is None and steps >= 5`.** Returning an
  answer at the cap counts as a miss, not partial credit.

## Limitations

- One tool (calculator). No file access, no web access — t09 and t10 exist to
  keep that visible rather than hidden.
- `calculator()` evaluates with `eval()`, not a sandboxed parser, and has no
  error handling — a malformed expression raises instead of returning a
  recoverable observation the model could react to.
- Refusal is only requested in the prompt; nothing in the code stops the model
  answering something it should decline. Only the exact reply `FINAL: None` is
  mapped to "no answer". A variation such as `FINAL: none` or a reason after
  the word stays a string and scores as a wrong answer.
- A crash and a refusal both reach the scorer as `None`, so a `no_answer` pass
  can't show which one happened (see Run 2).
- Sequential, ~9 s per task on Gemini's free tier. The cost is model latency
  and request throttling, not the loop.

## Run it

```bash
pip install google-genai anthropic python-dotenv pyyaml
# create a .env file with: GEMINI_API_KEY=<your key>
python agent.py
python run_evals.py
```
