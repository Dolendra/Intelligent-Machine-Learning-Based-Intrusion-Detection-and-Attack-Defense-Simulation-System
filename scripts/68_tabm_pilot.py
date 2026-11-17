"""R3 Stage 0 — TabM cost pilot (small workload; NOT a result).

Trains the official TabM (``tabm`` 0.0.3, Gorishniy et al., ICLR 2025) with piecewise-linear embeddings
for a fixed number of steps on a CICIDS2017 pilot split (seed 0) and measures time per step, memory and
inference cost on CPU or GPU, then extrapolates to the R3 LOAFO training size (~600k rows).

Settings follow the official README / paper: AdamW lr 2e-3, weight decay 3e-4, k = 32, n_blocks 3,
d_block 512, dropout 0.1, batch 1024, gradient clipping 1.0, probabilities = mean of the k members' softmax.

    .venvs/r3-cuda/Scripts/python.exe scripts/68_tabm_pilot.py --device cuda --steps 200
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--batch-size", type=int, default=1024)
    ap.add_argument("--n-train", type=int, default=120_000)
    ap.add_argument("--arch", default="tabm", choices=["tabm", "tabm-mini"])
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    import numpy as np
    import psutil
    import rtdl_num_embeddings as rne
    import tabm
    import torch as T

    from research.artifact_guard import assert_writable
    from research.data import cap_per_family, dedup_float32, feature_columns, load_cic2017, stratified_split
    from research.features import SignedLogScaler

    T.manual_seed(a.seed)
    np.random.seed(a.seed)
    dev = T.device(a.device)
    if a.device == "cuda":
        T.cuda.reset_peak_memory_stats()
    df, _ = dedup_float32(load_cic2017())
    df = df[~df["family"].isin(["Infiltration", "Heartbleed"])]
    feats = feature_columns(df)
    tr, _, te = stratified_split(df, (0.6, 0.1, 0.3), a.seed)
    tr = cap_per_family(tr[tr["family"] != "Bot"], {"BENIGN": a.n_train // 2, **{f: a.n_train // 10 for f in df["family"].unique()
                                                                                 if f != "BENIGN"}}, a.seed)
    te = cap_per_family(te, 10_000, a.seed)
    classes = ["BENIGN"] + sorted(set(tr["family"].astype(str)) - {"BENIGN"})
    lut = {c: i for i, c in enumerate(classes)}
    const = [f for f in feats if tr[f].nunique() < 2]  # piecewise-linear bins need ≥ 2 distinct values (training split)
    feats = [f for f in feats if f not in const]
    sc = SignedLogScaler().fit(tr[feats].to_numpy())
    Xtr = T.tensor(sc.transform(tr[feats].to_numpy()), dtype=T.float32)
    ytr = T.tensor([lut[c] for c in tr["family"].astype(str)])
    Xte = T.tensor(sc.transform(te[feats].to_numpy()), dtype=T.float32)

    bins = rne.compute_bins(Xtr, n_bins=48)
    emb = rne.PiecewiseLinearEmbeddings(bins, d_embedding=16, activation=False, version="B")
    model = tabm.TabM.make(n_num_features=len(feats), cat_cardinalities=[], d_out=len(classes), num_embeddings=emb,
                           k=32, n_blocks=3, d_block=512, dropout=0.1, arch_type=a.arch).to(dev)
    opt = T.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=3e-4)
    k = 32
    proc = psutil.Process()
    rss = proc.memory_info().rss
    times, losses = [], []
    g = T.Generator().manual_seed(a.seed)
    model.train()
    for step in range(a.steps):
        idx = T.randint(0, len(Xtr), (a.batch_size,), generator=g)
        x, y = Xtr[idx].to(dev), ytr[idx].to(dev)
        t = time.time()
        out = model(x_num=x)                       # (B, k, n_classes)
        loss = T.nn.functional.cross_entropy(out.flatten(0, 1), y.repeat_interleave(k))
        opt.zero_grad()
        loss.backward()
        T.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if a.device == "cuda":
            T.cuda.synchronize()
        times.append(time.time() - t)
        losses.append(float(loss.item()))
        rss = max(rss, proc.memory_info().rss)

    model.eval()
    t = time.time()
    with T.no_grad():
        probs = T.cat([T.softmax(model(x_num=Xte[i:i + 4096].to(dev)), dim=-1).mean(1).cpu() for i in range(0, len(Xte), 4096)])
    infer_s = time.time() - t
    yte = np.array([lut.get(c, -1) for c in te["family"].astype(str)])
    known = yte >= 0
    acc = float((probs.argmax(1).numpy()[known] == yte[known]).mean())

    st = np.array(times[5:] or times)
    steps_epoch = int(np.ceil(600_000 / a.batch_size))
    res = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "R3 Stage 0 TabM cost pilot — not a result",
        "device": a.device, "torch": T.__version__, "cuda": T.version.cuda,
        "gpu": T.cuda.get_device_name(0) if a.device == "cuda" else None, "threads": T.get_num_threads(),
        "python": platform.python_version(), "tabm": tabm.__version__ if hasattr(tabm, "__version__") else "0.0.3",
        "config": {"arch": a.arch, "k": k, "n_blocks": 3, "d_block": 512, "dropout": 0.1, "batch": a.batch_size,
                   "embeddings": "PiecewiseLinear(48 bins, d=16, version B)", "lr": 2e-3, "wd": 3e-4},
        "dropped_constant_columns": const,
        "data": {"n_train": int(len(Xtr)), "n_eval": int(len(Xte)), "d": len(feats), "classes": classes},
        "steps": a.steps, "loss_first10_mean": float(np.mean(losses[:10])), "loss_last10_mean": float(np.mean(losses[-10:])),
        "smoke_known_accuracy_after_pilot_steps": acc,
        "step_seconds": {"median": float(np.median(st)), "p90": float(np.quantile(st, 0.9))},
        "inference_ms_per_1k_flows": round(1000 * infer_s / len(Xte) * 1000, 2),
        "extrapolation": {"steps_per_epoch_at_600k": steps_epoch,
                          "epoch_minutes": float(np.median(st) * steps_epoch / 60),
                          "fit_hours_if_30_epochs": float(np.median(st) * steps_epoch * 30 / 3600),
                          "note": "TabM trains until early stopping (patience 16); 30 epochs is an assumption"},
        "memory": {"peak_rss_gb": round(rss / 2**30, 2),
                   "cuda_peak_allocated_gb": round(T.cuda.max_memory_allocated() / 2**30, 2) if a.device == "cuda" else None},
    }
    out = ROOT / "research_artifacts" / "r3" / "pilots" / f"tabm_{a.device}_{a.arch}.json"
    assert_writable(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("step_seconds", "extrapolation", "memory", "loss_first10_mean",
                                          "loss_last10_mean", "smoke_known_accuracy_after_pilot_steps")}, indent=1))


if __name__ == "__main__":
    main()
