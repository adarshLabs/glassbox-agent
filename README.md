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
- **A refusal convention, not an enforced one.** The prompt asks the model to
  reply `FINAL: CANNOT_ANSWER — <what's missing>` when it lacks a needed
  capability or a verifiable fact. Nothing in the code checks for this string
  or treats it specially — it reaches the harness as ordinary answer text.

## Evaluation

Ten tasks with programmatic assertions. Seven are expected to succeed; three are
expected to fail, each for a different reason. A task is *meant* to count as
agreement when the agent behaves the way the task predicted — so an expected
failure that fails correctly should be a pass for the harness. A scorer bug
(below) currently breaks that for two of the three.

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
Harness agreement:  8/10 true  (7/10 as printed, under a broken scorer)
Expected-pass tasks that passed: 6/7   (t07 hit the step cap)
Expected-fail tasks that failed correctly: 1/3
```

Three defects, all in the harness or the plumbing rather than in the reasoning.
None of them are fixed yet — this is a diagnosis, not a changelog.

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

## Scoring decisions, disclosed

- **t06 sometimes returns `30%`, not `30`.** The arithmetic is right; the `%`
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
- Refusal is prompt-enforced, not structurally enforced: nothing in the code
  stops the model answering something it should decline, or confirms a
  `CANNOT_ANSWER` reply is actually treated as "no answer" downstream.
- The scorer's `matched` calculation inverts correctness for the
  `hits_step_cap` and `no_answer` assert kinds (see Run 1, defect 1).
- Sequential, ~9 s per task on Gemini's free tier. The cost is model latency
  and request throttling, not the loop.

## Run it

```bash
pip install google-genai anthropic python-dotenv pyyaml
# create a .env file with: GEMINI_API_KEY=<your key>
python agent.py
python run_evals.py
```
