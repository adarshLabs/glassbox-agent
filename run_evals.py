
import time, yaml
from agent import run

tasks = yaml.safe_load(open("evals/tasks.yaml"))
rows, passed = [], 0

for t in tasks:
    t0 = time.time()
    try:
        answer, steps = run(t["prompt"])
    except Exception as e:
        answer, steps = None, 0
    secs = round(time.time() - t0, 1)

    kind = t["assert"]
    if kind == "numeric":
        try:
            cleaned = str(answer).replace(",", "").replace("%", "").replace("$", "").strip().rstrip(".")
            got = float(cleaned)
            ok = abs(got - float(t["value"])) <= float(t["tol"])
        except (TypeError, ValueError):
            ok = False
    elif kind == "hits_step_cap":
        ok = (answer is None and steps >= int(t["value"]))
    elif kind == "no_answer":
        ok = (answer is None)

    matched = (ok == (t["expect"] == "pass"))
    passed += matched
    rows.append((t["id"], t["expect"], "OK" if ok else "no", steps, secs, matched, repr(answer)[:40]))

print(f"{'id':<5}{'expect':<8}{'result':<8}{'steps':<7}{'secs':<7}{'match':<7}answer")
for r in rows:
    print(f"{r[0]:<5}{r[1]:<8}{r[2]:<8}{r[3]:<7}{r[4]:<7}{'Y' if r[5] else 'N':<7}{r[6]}")
print(f"\nharness agreement: {passed}/{len(tasks)}")