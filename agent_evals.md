# Agent benchmarks, and where `glassbox` sits among them

Three public agent benchmarks read at source, plus my own harness in the same
columns. The point of the fourth row is that it is filled from my own files, not
from a paper.

| Benchmark | Task type | Scoring rule | Known failure mode |
|---|---|---|---|
| **GAIA** · [arXiv:2311.12983](https://arxiv.org/abs/2311.12983) | 466 human-written real-world questions (166 released annotated, 300 held back to power a leaderboard). Plain-text prompt, sometimes with an attached file — 17 filetypes, mostly `xlsx`, `png`, `pdf`, `txt`, `mp3`. Answered **zero-shot** by a tool-using assistant; required capabilities are web browsing (355 questions), coding (154), multi-modality (138), diverse filetype reading (129). Every answer is one short factoid: a number, a few words, or a comma-separated list. Three levels by the annotator's own step and tool count — L1 ≤1 tool and ≤5 steps, L2 roughly 5–10 steps and multiple tools, L3 arbitrarily long. | **Quasi-exact match** of the final answer against a *single* ground truth, with normalisation tied to the ground-truth type (number / string / list). A system prompt forces the shape — `FINAL ANSWER: ...`, no thousands separators, no units or `$`/`%`, no articles, no abbreviations, digits written in plain text — which is what lets the match be strict. **Only the final answer is scored.** Scoring function released alongside the leaderboard. | **The reasoning trace is never graded**, and the authors name this themselves under Limitations: many paths reach the same answer and there is no simple way to grade them. So a right answer by a wrong route scores full marks — and the paper shows it happening, twice: non-tool models score non-zero on multi-modality and filetype-reading questions by solving them differently from the annotator, and non-zero on browsing questions purely by having memorised the intermediate facts. The mirror of it: a correct answer in the wrong format scores zero, so format compliance is load-bearing. Secondary decay risk — the ground truth lives on the open web and can change or vanish. |
| **WebArena** · [arXiv:2307.13854](https://arxiv.org/abs/2307.13854) | A **self-hosted, standalone** environment, not a static dataset: four fully functional sites rebuilt from open-source projects and populated with real data — e-commerce (Magento, ~90k products), a Reddit-style forum (Postmill, 95 subreddits / 127k posts), GitLab (300 repos), and a CMS — plus tools (OpenStreetMap, calculator, scratchpad) and knowledge bases (offline Wikipedia, product manuals). Shipped as Docker images so the whole thing resets to a deterministic initial state. 812 tasks from 241 templates (~3.3 instantiations each), each a high-level NL intent requiring many actions across multiple pages, in three families: information-seeking, site navigation, content & config. Observation = URL + open tabs + page content, renderable as raw DOM, screenshot, or **accessibility tree**; multi-tab. Action space = element ops (`click`/`hover`/`type`/`press`/`scroll`), tab ops, URL navigation. Per-site user roles with different permissions, pre-logged-in via cached cookies. Includes deliberately **unachievable** tasks whose correct answer is `N/A`. | **Two reward functions, and which one applies depends on the task family.** Information-seeking uses `r_info(â, a*)` against an annotated reference, with three implementations: `exact_match`, `must_include` (substring, for unordered lists or key concepts), and `fuzzy_match` (gpt-4-0613 judges semantic equivalence — needed because "2h58min" and "2 hour 58 minutes" are the same answer). Navigation and content/config use `r_prog(s)`, which **programmatically inspects the intermediate states**: an annotated `locator` — a DB query, a site API call, or a JS selection such as `document.querySelector('.submission__inner').outerText` — pulls out the content the intent is about, then annotated keywords are checked against it with the same `exact_match` / `must_include`. The declared target throughout is **functional correctness**, explicitly *not* comparison of the action sequence to a reference sequence. | **It reads states, never the path — and that is the design, not an oversight.** The authors argue outcome-based checking is both more reliable than surface-form action comparison and necessary, because sufficiently complex tasks have many valid routes. The consequence: **an unintended route that lands the right end state scores full marks**, and there is no partial credit for a nearly-correct trajectory and no way to tell a competent completion from a lucky one. Separately, the paper's own error analysis shows how brittle the agents are on things scoring cannot see: with the unachievable hint in the prompt GPT-4 declares **54.9% of feasible tasks impossible**; and in one documented trace it re-issues `type [2430] [DMV area]` to a box the observation already shows as filled, until it hits the step cap. |
| **SWE-bench** · [arXiv:2310.06770](https://arxiv.org/abs/2310.06770) | 2,294 instances mined from **real merged pull requests** across 12 popular Python repos (django 850, sympy 386, scikit-learn 229…), filtered from ~90k PRs by three gates: the PR must be merged, must close a linked issue, and must add tests. **Model receives** a problem statement — the linked issues' titles and bodies plus only those comments written *before* the PR's first commit — and the codebase at a specific `base_commit` (avg **3,010 non-test files / 438K non-test lines**). **Model emits** a single `.patch` file applied with unix `patch`. Reference patches edit 1.7 files, 3.0 functions, 32.8 lines. The repo cannot fit in context, so the input is assembled by BM25 retrieval or an unrealistic **"oracle"** setting that hands over exactly the files the gold patch touched. SWE-bench Lite is a 300-instance subset. | **Apply the patch, then run the repo's own test suite — and check two sets, both cached from a validation run against the gold patch.** (1) **`FAIL_TO_PASS`** — tests that flip fail→pass once the gold patch is applied; at least one per instance, ≥2 in 40% of them. These ask *did you fix the issue*. (2) **`PASS_TO_PASS`** — tests already passing before the change, a **median of 51 extra tests** per instance. These ask *did you break anything else*. **Resolved only if the patch applies AND every test in BOTH sets passes** — a missing test or any non-pass status counts as a failure. Binary, no partial credit. (`FAIL_TO_FAIL` and `PASS_TO_FAIL` are recorded during validation but excluded from scoring.) | **Passing both test sets does not mean the patch is right, and the authors say so in Limitations:** execution-based testing alone *"is insufficient to guarantee reliable performance,"* because model patches are *"frequently less comprehensive, efficient, or readable"* than the human ones. Their own qualitative section is blunter — models write primitive Python, ignore existing library and codebase facilities, and take a greedy approach that solves the stated problem exactly with little regard for style or structure, where gold patches make structural improvements anticipating future issues. Three case studies pass the tests and are still wrong in review: one reimplements a `dtype` cast as a new helper when passing `dtype` to the existing validator was the fix; one uses bare `str()` where the codebase has `builtin_str`, which the authors call *lucky*; one is shorter than gold yet raises the Cyclomatic complexity of a widely-used adapter class from 3 to 5 by putting the branch in the busiest place. ⓘ The other candidate — the real fix being recoverable from the handed context — is the one they engineered against (post-commit comments withheld, `hints_text` unused, disjoint train repos) and have counter-evidence for: resolve rates show no consistent pre-/post-2023 split. |
| **`glassbox`** (this repo) | **10 single-turn natural-language prompts** against a one-tool agent — `calculator(expr)` only — with a hard 5-step cap. **7 expected-pass** (t01–t07), all arithmetic. **3 expected-fail (t08–t10), and each fails for a different designed reason**: t08 needs 8+ tool calls against a cap of 5, t09 asks for a total in `data/sales.csv` when no file-lookup tool and no file exist, t10 asks for 8% of today's USD/INR rate when no web tool exists. Three assertion kinds: `numeric` with a per-task tolerance, `hits_step_cap`, `no_answer`. ⚠ **No held-out split** — the agent has been revised against this same set, so the score is fitted, not earned. | **`matched = ok`**, where `ok` comes from one of three assertion branches: `numeric` normalises the answer (strips commas, `%`, `$`, trailing `.`) then tests `abs(got - value) <= tol`; `hits_step_cap` requires `answer is None and steps >= value`; `no_answer` requires `answer is None`. Reported as `harness agreement: n/10` — **agreement, not pass rate**, because an expected failure that fails as predicted counts in favour. | **The original scorer read `matched = (ok == (t["expect"] == "pass"))`, which double-counts the expectation** — `ok` already means *behaved as the task predicted*. It marked t08 wrong for hitting the cap exactly as designed, and credited t09 and t10 for failing in the wrong way. **Printed 8/10; true value 7/10** — one false negative and two false positives, pointing in opposite directions and nearly cancelling, so the headline number stayed plausible. **A harness bug that moves the total by one is far harder to notice than one that moves it by five.** ⚠ **Live residual: `None` reaches the scorer by three routes** — a refusal, step-cap exhaustion, and an unhandled exception from the bare `eval` at `agent.py:42` swallowed by `run_evals.py:12` — and refusal and crash both surface as `(None, 0)`. Surfacing the caught exception at the point it is caught (21 Oct) confirmed **this** run was refusal: nothing raised. But the crash route is **latent, not absent** — both tasks refused at zero tool calls, so `eval` was never reached, and an earlier run under the same code got t09 to `None` by routing `data/sales.csv` into `eval()` and raising `NameError`. |

## Notes — the thing worth having ready if someone probes

**GAIA.** The single-correct-answer property is what buys the cheap automatic
scoring, and the paper is honest about what it costs: ~2 hours of annotator time
per question, and of 623 crafted questions only **68% were valid as written** —
the rest had to be repaired or thrown out, because ambiguity is subtle and rarely
visible to the person who wrote the question. Human score is 92%, GPT-4 with
plugins 30.3% at Level 1 and **0% at Level 3**. ⚠ That plugin number is an
*oracle* estimate — plugins were selected by hand per question — and the authors
say so rather than letting it stand as a reproducible result.

**WebArena.** Best GPT-4 agent reaches **14.41%** end-to-end against **78.24%**
for humans; GPT-3.5 with chain-of-thought manages 8.75%, text-bison-001 5.05%.
Two numbers from the analysis are worth more than the headline. First, **one line
of the prompt moves the score 2.7 points**: the "stop if the task is impossible"
hint lifts unachievable-task detection from 44.44% to 77.78% but makes GPT-4
abandon 54.9% of *achievable* tasks, so overall success falls from 14.41% to
11.70%. The eval is measuring the instruction as much as the agent. Second, of
61 templates with at least one success, **GPT-4 scored 100% on four** — tasks
from the same template, differing only in instantiation, swing from solved to
unsolved ("fork metaseq" vs "fork all repos from Facebook"), so per-task success
rates are noisier than a single aggregate suggests.

⚠ Also worth carrying: the `fuzzy_match` grader is **an LLM inside the scorer**.
The authors defend it — hand-checked 39/40 agreement, and 100% on 900
programmatically generated date and duration format variants — but the honest
statement is that part of this benchmark's ground truth is a model's judgement,
which is exactly the dependency GAIA's authors refused to take on.

**SWE-bench.** Best model at publication was **Claude 2 at 1.96%** with BM25
retrieval, 4.80% with oracle retrieval; ChatGPT-3.5 managed 0.17%. ★ **The
number worth carrying is not the resolve rate — it is the outcome breakdown.**
Of Claude 2's 1,078 patches that applied cleanly, only **110 resolved**;
**471 were no-ops** (prior behaviour intact, zero `FAIL_TO_PASS` tests passing)
and **436 were regressions** (zero `FAIL_TO_PASS` *and* existing tests broken).
So ~84% of syntactically valid patches fixed nothing, and about half of those
also damaged the repo. Models also under-generate: applied patches average 19.6
lines against 44.1 for the corresponding gold patch, and rarely touch more than
one file.

★ **`PASS_TO_PASS` is the structural idea to steal.** GAIA and WebArena both
score the endpoint and are blind to the route. SWE-bench is also outcome-based —
it never compares your patch to the gold patch — but the second test set is a
**regression guard**: it cannot see *how* you got there, yet it catches what you
damaged on the way. That is the cheapest available fix for the hole the other two
benchmarks leave open, and it is a *separate assertion*, not a smarter one.

## Which one this harness most resembles

**Closest to GAIA.** Both score a returned value against an expected one by
assertion, with normalisation doing the work that a format convention is supposed
to do — GAIA's system prompt forbids units and thousands separators, mine strips
`%`, `$` and commas after the fact, which is the same leniency applied one step
later and less honestly. Neither has world state to inspect, so neither can do
what WebArena does.

**What this harness does that none of the three do: it plants its failures, and
each one fails for a different structural reason.** GAIA has no expected-failure
concept at all. WebArena's unachievable tasks come closest, but they share a
single cause — the environment cannot serve the request — whereas t08 tests a
stopping condition, t09 a missing capability, and t10 a missing fact. The
distinction turned out to matter: a refusal rule written in terms of *tools*
covered t09 and not t10, because "I have no file-lookup tool" reads to the model
as a capability gap while "I don't know today's USD/INR" reads as recall, and
recall feels answerable.

**What it lacks, and the gap is structural rather than cosmetic:** SWE-bench
carries a second, separate test set — `PASS_TO_PASS`, a median of 51 tests per
instance — that asks *did you break anything else*. It cannot see the route
either, but it catches collateral damage on the way. Nothing in this harness
occupies that role, so a change that fixes the task under test and quietly
regresses another has no way of showing up.
