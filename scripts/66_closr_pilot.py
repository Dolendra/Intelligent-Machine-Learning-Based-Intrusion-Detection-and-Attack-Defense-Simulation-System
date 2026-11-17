"""R3 Stage 0 — CLOSR execution and cost pilot (NOT a reproduction of the paper's numbers).

Runs the *official* CLOSR implementation (github.com/jackwilkie/CLOSR @ 79da4d1, imported unmodified
from --closr-dir) on a small CICIDS2017 workload, because the authors' dataset (LycoS-IDS2017) is
not yet approved for download. It answers only: does the code run here, how long does a training
step take on CPU vs GPU at the paper's batch size, how much memory does it need, and does the
loss decrease. Metrics after a few epochs are smoke checks, not results.

Deviations from the authors' scripts (all forced by the data, recorded in the output):
  * d_in = number of our features (77) instead of the hard-coded 72;
  * n_classes = BENIGN + known families of the pilot split (instead of 12);
  * seeds are set (the official scripts set none);
  * nothing is written to the repository's weights/ folder (train_closr.py would overwrite the
    released weights/closr.pt.tar).

    python scripts/66_closr_pilot.py --closr-dir <clone> --device cuda --epochs 2
"""
from __future__ import annotations

import argparse
import json
import platform
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--closr-dir", required=True, type=Path)
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--batch-size", type=int, default=4096)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--n-train", type=int, default=120_000, help="pilot training rows (balanced sampler draws this many per epoch)")
    ap.add_argument("--max-steps", type=int, default=0, help="stop each epoch after this many steps (0 = full epoch)")
    ap.add_argument("--held-out", default="Bot", help="family withheld as the pilot's zero-day class")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    # CLOSR's packages (data, model, losses, util) must win over this repository's data/ folder
    sys.path.insert(0, str(a.closr_dir.resolve()))
    sys.path.insert(1, str(ROOT))
    import numpy as np
    import psutil
    import torch as T

    from data.loaders import tabular_dl
    from data.utils import ZNormaliser
    from eval_closr import closr_eval
    from losses.closr_loss import CLOSRLoss
    from model.model import CLOSRMLP
    from util.schedules import LRSchedule, WarmupCosineSchedule

    from research.artifact_guard import assert_writable
    from research.data import cap_per_family, feature_columns, load_cic2017, stratified_split

    random.seed(a.seed)
    np.random.seed(a.seed)
    T.manual_seed(a.seed)
    if a.threads:
        T.set_num_threads(a.threads)
    dev = T.device(a.device)
    if a.device == "cuda":
        T.cuda.reset_peak_memory_stats()

    # ---- small LOAFO-style split from CICIDS2017 (pilot seed 0; never a reporting seed)
    df = load_cic2017()
    df = df[~df["family"].isin(["Infiltration", "Heartbleed"])]
    feats = feature_columns(df)
    tr, va, te = stratified_split(df, (0.6, 0.1, 0.3), a.seed)
    per = max(a.n_train // 6, 1)
    train = cap_per_family(tr[tr["family"] != a.held_out], {"BENIGN": a.n_train // 2, **{f: per // 2 for f in df["family"].unique() if f != "BENIGN"}}, a.seed)
    test = cap_per_family(te[te["family"] != a.held_out], 5_000, a.seed)
    zd = cap_per_family(te[te["family"] == a.held_out], 2_000, a.seed)
    classes = ["BENIGN"] + sorted(set(train["family"].astype(str)) - {"BENIGN"})
    lut = {c: i for i, c in enumerate(classes)}
    # official get_data() drops all-zero columns (computed on the whole file); here: on the training split only
    zero_cols = [f for f in feats if (train[f] == 0).all()]
    feats = [f for f in feats if f not in zero_cols]
    norm = ZNormaliser(train[feats].to_numpy(np.float64))
    to_x = lambda d: norm.normalise(d[feats].to_numpy(np.float64)).astype(np.float32)  # noqa: E731
    x_tr, y_tr = to_x(train), np.array([lut[c] for c in train["family"].astype(str)])
    x_te, y_te = to_x(test), np.array([lut[c] for c in test["family"].astype(str)])
    x_zd, y_zd = to_x(zd), np.full(len(zd), len(classes))

    # ---- official model / loss / sampler / schedule, paper defaults except the deviations above
    model = CLOSRMLP(d_in=len(feats), n_classes=len(classes), d_out=64, neurons=[1024, 1024, 1024], dropout=0.1,
                     residual=False).to(dev)
    criterion = CLOSRLoss(m=1.0, squared=True, n_classes=len(classes))
    dl = tabular_dl(x=x_tr, y=y_tr, batch_size=a.batch_size, balanced=True, collate_fn=None, drop_last=True, num_workers=0)
    total_epochs_for_schedule = 200
    opt = T.optim.AdamW(model.parameters(), lr=1e-6, betas=(0.9, 0.999), weight_decay=0.0403709)
    sched = LRSchedule(opt, schedule=WarmupCosineSchedule(start_val=1e-6, end_val=1e-6, ref_val=1e-5,
                                                         T_max=total_epochs_for_schedule * len(dl),
                                                         warmup_steps=int(20 * len(dl))))
    proc = psutil.Process()
    rss_peak = proc.memory_info().rss
    epochs, step_times, status = [], [], "ok"
    try:
        for ep in range(1, a.epochs + 1):
            model.train()
            t_ep, losses = time.time(), []
            for i, (x, y) in enumerate(dl):
                if a.max_steps and i >= a.max_steps:
                    break
                t = time.time()
                x, y = x.to(dev), y.to(dev)
                loss = criterion(x=model(x), y=y)
                opt.zero_grad()
                loss.backward()
                opt.step()
                sched.step()
                if a.device == "cuda":
                    T.cuda.synchronize()
                step_times.append(time.time() - t)
                losses.append(float(loss.item()))
                rss_peak = max(rss_peak, proc.memory_info().rss)
            epochs.append({"epoch": ep, "seconds": round(time.time() - t_ep, 2), "steps": len(losses),
                           "loss_first": losses[0], "loss_last": losses[-1], "loss_mean": float(np.mean(losses))})
            print(f"epoch {ep}: {epochs[-1]}", flush=True)
    except T.cuda.OutOfMemoryError as e:  # recorded, not hidden
        status = f"cuda_oom at batch {a.batch_size}: {str(e).splitlines()[0]}"
        print(status, flush=True)

    smoke = None
    if status == "ok":
        model.eval()
        t = time.time()
        smoke = closr_eval(model=model, x_train=T.tensor(x_tr, device=dev), y_train=T.tensor(y_tr, device=dev),
                           x_test=T.tensor(x_te, device=dev), y_test=T.tensor(y_te, device=dev),
                           x_zd=T.tensor(x_zd, device=dev), y_zd=T.tensor(y_zd, device=dev),
                           opt=SimpleNamespace(chunk_size=1024))
        smoke = {k: float(v) for k, v in smoke.items()}
        smoke["eval_seconds"] = round(time.time() - t, 2)

    st = np.array(step_times[1:] or step_times or [float("nan")])  # first step includes warm-up/allocation
    steps_full = int(np.ceil(600_000 / a.batch_size))  # LOAFO train size ≈ 300k benign + 5 × 60k
    res = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "R3 Stage 0 CLOSR execution/cost pilot — not a reproduction of published numbers",
        "closr_commit": "79da4d1", "device": a.device, "torch": T.__version__,
        "cuda": T.version.cuda, "gpu": T.cuda.get_device_name(0) if a.device == "cuda" else None,
        "python": platform.python_version(), "threads": T.get_num_threads(),
        "data": {"source": "CICIDS2017 MachineLearningCVE (pilot seed 0)", "n_train": int(len(x_tr)),
                 "n_test_known": int(len(x_te)), "n_zero_day": int(len(x_zd)), "held_out": a.held_out,
                 "classes": classes, "d_in": len(feats)},
        "dropped_zero_columns": zero_cols,
        "deviations": [f"d_in={len(feats)} (official 72; all-zero columns dropped on the training split, not the whole file)", f"n_classes={len(classes)} (official 12)", "seeds set (official: none)",
                       "no checkpoint written (official overwrites weights/closr.pt.tar)",
                       "pilot data CICIDS2017, not LycoS-IDS2017"],
        "batch_size": a.batch_size, "status": status, "epochs": epochs,
        "step_seconds": {"median": float(np.median(st)), "p90": float(np.quantile(st, 0.9)), "n": int(len(st))},
        "extrapolation": {"steps_per_epoch_at_600k_rows": steps_full,
                          "epoch_seconds_at_600k_rows": float(np.median(st) * steps_full),
                          "hours_200_epochs_one_fit": float(np.median(st) * steps_full * 200 / 3600)},
        "memory": {"peak_rss_gb": round(rss_peak / 2**30, 2),
                   "cuda_peak_allocated_gb": round(T.cuda.max_memory_allocated() / 2**30, 2) if a.device == "cuda" else None},
        "smoke_metrics_after_pilot_epochs": smoke,
    }
    out = a.out or (ROOT / "research_artifacts" / "r3" / "pilots" / f"closr_{a.device}_b{a.batch_size}.json")
    assert_writable(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("status", "step_seconds", "extrapolation", "memory")}, indent=1))


if __name__ == "__main__":
    main()
