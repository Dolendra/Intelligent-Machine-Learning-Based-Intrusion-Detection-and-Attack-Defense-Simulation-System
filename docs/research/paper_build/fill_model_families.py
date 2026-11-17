"""Fill the model-family placeholders in paper.py from research_artifacts/model_family_comparison.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
res = json.loads((ROOT / "research_artifacts" / "model_family_comparison.json").read_text(encoding="utf-8"))
assert not res["quick"], "run the full comparison first"
R = res["results"]
FAMS = ["Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"]
order = sorted(R, key=lambda n: -R[n]["heldout_mean"]["zero_day_recall"])
short = {n: n.replace(" (LightGBM-style)", "").replace(" (PyTorch)", "").replace(" (RBF, Nyström)", " (RBF)") for n in R}

iid_f1 = [R[n]["iid"]["f1"] for n in R]
best = order[0]
nn = [n for n in R if "PyTorch" in n]
trees = ["Decision tree", "Random forest", "XGBoost", "Hist. gradient boosting (LightGBM-style)"]
mean = lambda xs: sum(xs) / len(xs)
nn_mean = mean([R[n]["heldout_mean"]["zero_day_recall"] for n in nn])
tree_mean = mean([R[n]["heldout_mean"]["zero_day_recall"] for n in trees])
best_h = R[best]["heldout_mean"]["zero_day_recall"]

rows = []
for n in order:
    i, h = R[n]["iid"], R[n]["heldout_mean"]
    rows.append([short[n], f"{i['f1']:.3f}", f"{100 * i['fpr']:.2f}", f"{h['zero_day_recall']:.3f}"]
                + [f"{R[n]['heldout'][f]['zero_day_recall']:.2f}" for f in FAMS])
rows_py = ",\n         ".join(repr(r) for r in rows)

section = f'''P.subsection("Would a Different Classifier Solve It?")
P.para("Table XII compares ten classifier families at the same 1% benign false-alarm budget. With every family "
       "seen in training they are hard to tell apart: binary F1 ranged from {min(iid_f1):.3f} to {max(iid_f1):.3f}, and all "
       "tree ensembles, the kernel SVM, the MLP and the CNN scored above 0.98. With one family withheld, the picture "
       "changes. Averaged over the six folds, the best model ({short[best]}) caught {100 * best_h:.1f}% of the withheld family; "
       "the four tree-based models averaged {100 * tree_mean:.1f}% and the three neural networks {100 * nn_mean:.1f}%. No family of "
       "model detected the withheld botnet, and none caught more than a small share of withheld port scans. Deeper or "
       "differently shaped classifiers are therefore not a substitute for open-set detection: under the same budget and "
       "a comparable protocol, Aegis-OSR's 70.6% (Table IV) is well above every closed-set classifier here. (The protocols "
       "differ in detail—this comparison uses one seed and a binary task—so we compare levels rather than exact values.)")
P.table("Ten Classifier Families at a 1% Benign False-Alarm Budget: Seen vs. Withheld Families (Seed 1)",
        ["Model", "IID F1", "IID FPR (%)", "Withheld: mean recall", "Bot", "BruteF.", "DDoS", "DoS", "PortSc.", "WebAtt."],
        [{rows_py}],
        widths=[2.1, 0.7, 0.7, 1.0, 0.55, 0.65, 0.6, 0.55, 0.65, 0.65], label="families", size=7.5,
        notes="Thresholds set on validation benign flows for a 1% false-alarm rate. Histogram gradient boosting is scikit-learn's "
              "LightGBM-style implementation; the CNN and LSTM read the 77 features as a 1-D sequence.")
'''
abstract = (f"ten closed-set classifier families, including SVMs and MLP, CNN and LSTM networks, caught at most "
            f"{100 * best_h:.0f}% of withheld families at the same budget.")

p = Path(__file__).with_name("paper.py")
s = p.read_text(encoding="utf-8")
s = s.replace("##MF_SECTION##", section).replace("##MF_ABSTRACT##", abstract)
assert "##MF" not in s
p.write_text(s, encoding="utf-8")
print(abstract)
print("best", best, round(best_h, 3), "trees", round(tree_mean, 3), "nn", round(nn_mean, 3))
