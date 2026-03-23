## RansomScope

Real-time, sequence-based, host-level ransomware detector for Linux (Fedora-focused) using:

- **Python 3.11+**
- **PyTorch** (LSTM)
- **watchdog** + **psutil**
- **SQLite** for forensic timelines

No transformers, no heavy frameworks. Everything is modular and kept minimal.

---

### 1. Project layout

```text
ransomescope/
├── config.py              # Global config (window sizes, thresholds, DB path)
├── requirements.txt       # Python dependencies
├── main.py                # Real-time pipeline + CLI (run / replay)
├── train.py               # LSTM training script
├── dataset_gen.py         # Synthetic dataset generator
├── test_monitor.py        # Smoke test for collection layer
├── collection/            # Data collection: file + process event monitoring
│   ├── event_monitor.py   # EventMonitor (watchdog + psutil)
│   ├── event_types.py     # Event dataclass, EventType
│   └── entropy.py         # Shannon entropy computation
├── processing/            # Feature extraction, model, explainability, decision
│   ├── feature_engine/    # Sliding window feature extraction
│   ├── model/             # LSTM model + manager
│   ├── explain/           # Lightweight explainability
│   └── decision/          # Decision engine (user prompts)
├── forensics/             # SQLite logging + replay
└── scripts/               # Test activity generators
    ├── generate_benign_activity.py
    └── generate_ransomware_activity.py
```

Run all commands from the project directory where `main.py` lives.

For your WSL setup, this repo is available at:

```bash
~/ransomscope
```

If you sync from Windows into WSL, use:

```bash
rsync -av --delete \
  --exclude='/venv/' \
  --exclude='/.venv/' \
  --exclude='**/__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache/' \
  --exclude='.mypy_cache/' \
  /mnt/c/Work/Cursor/ransomescope/ ~/ransomscope/
```

---

### 2. Installation (Fedora / Linux)

```bash
cd ~/ransomscope
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

`watchdog` will use inotify on Linux; `psutil` is used for processes.

---

### 3. Quick smoke test (monitoring layer only)

This verifies file + process monitoring and entropy calculation.

```bash
python test_monitor.py
```

You should see:

- The temporary directory being watched.
- Printed events with keys like `event_type`, `file_path`, `entropy`, `process_id`.

If you see these structured events, the monitoring layer works.

---

### 4. Generate a synthetic training dataset

This script:

- Creates a temporary workspace.
- Runs benign scenarios (bulk copy, unzip-like writes).
- Runs ransomware-like scenarios (high-entropy rewrites, renames, deletes).
- Uses the monitoring + sliding window engine to build sequences.
- Writes a CSV that `train.py` can consume.

```bash
python dataset_gen.py --output ransomescope_dataset.csv \
  --benign-runs 15 \
  --ransom-runs 15
```

Check the CSV:

```bash
head -n 5 ransomescope_dataset.csv
```

You should see:

- First column: `label` (0 = benign, 1 = ransomware-like).
- Remaining columns: flattened sequence features.

If the file is non-empty and has numeric rows, dataset generation worked.

---

### 5. Train the LSTM model

Train on the generated CSV:

```bash
python train.py --data ransomescope_dataset.csv \
  --epochs 15 \
  --batch-size 32 \
  --val-ratio 0.2 \
  --model-path ransomescope_lstm.pt
```

You should see epoch logs with train_loss, val_loss, val_acc. The best model (by validation loss) is saved.

**Important:** You must retrain after code changes that affect features (FEATURE_DIM) or model architecture.

This file is loaded automatically by `main.py` via `ModelManager`.

---

### 6. Run the real-time detector

**Recommended:** run inside a Linux/Fedora VM or test machine.

#### 6.1 Start RansomScope

By default it watches your home directory:

```bash
python main.py run
```

Or specify a safer test directory:

```bash
mkdir -p /tmp/ransomescope_test
python main.py run --watch /tmp/ransomescope_test
```

Optional: set a custom incident id (easier for replay later):

```bash
python main.py run --watch /tmp/ransomescope_test \
  --incident demo-incident-1
```

You should see logs like:

- `Watching: /tmp/ransomescope_test`
- `Windows: N/10 (need 10 for inference)` periodically
- When inference runs: `RISK=0.xx | LEVEL=BENIGN|SUSPICIOUS|HIGH | RANSOM_SIGNALS=[...] | BENIGN_SIGNALS=[...]`
- For suspicious/high risk: a detailed feature breakdown

Use `--verbose` for compact activity snapshots (counts, entropy delta, latest risk/level).
Latency per inference should stay under 1000 ms.

For a guaranteed demo prompt path (high-risk flow):

```bash
python main.py run --watch /tmp/ransomescope_test \
  --incident demo-1 \
  --verbose \
  --demo-force-high-risk
```

Optional threshold tuning (must keep suspicious > benign):

```bash
python main.py run --watch /tmp/ransomescope_test \
  --incident demo-1 \
  --verbose \
  --benign-threshold 0.01 \
  --suspicious-threshold 0.02 \
  --demo-force-high-risk
```

#### 6.2 Trigger benign behaviour

In another terminal:

```bash
cd /tmp/ransomescope_test
for i in {1..20}; do echo "hello $i" > "file_$i.txt"; done
```

Expected:

- Mostly **benign** or low risk scores.
- Explanations mentioning mild file modification bursts at most.

#### 6.3 Trigger ransomware-like behaviour (use throwaway dir only)

**WARNING:** Use the ransomware script only in a throwaway test directory. It modifies and renames files.

```bash
python scripts/generate_ransomware_activity.py /tmp/ransomescope_test
```

Or manually (careful):

In the same watched directory (still **only use a throwaway test path**):

```bash
python - << 'EOF'
import os, pathlib, secrets
base = pathlib.Path("/tmp/ransomescope_test/victims")
base.mkdir(parents=True, exist_ok=True)
for i in range(30):
    p = base / f"doc_{i}.txt"
    p.write_text("example data " * 100)

for i, p in enumerate(sorted(base.glob("*.txt"))):
    p.write_bytes(secrets.token_bytes(4096))
    enc = p.with_suffix(".enc")
    p.rename(enc)
EOF
```

Expected:

- Higher `risk_score` values.
- Explanations referencing entropy spikes, renames, and user-directory activity.
- For high risk, the decision engine will prompt:
  - `Kill process?`
  - `Quarantine?` (no-op placeholder)
  - `Mark as safe?`

If `k` targets the same PID as the running monitor, RansomScope now refuses self-termination and keeps monitoring alive.

**Nothing is auto-deleted**, and quarantine is intentionally a no-op in this academic project.

Press `Ctrl+C` in the main window to stop RansomScope when done.

**Important:** Use `Ctrl+C` to stop. Do **not** use `Ctrl+Z` (suspends the process).

---

### 7. Forensic replay

All events, risk scores and decisions are written to an SQLite DB:

- Default path: `ransomescope_forensics.db`
- Table: `timeline`

Replay must use the **same incident_id** you passed to `--incident`. Example: if you ran with `--incident benign-test`:

```bash
python main.py replay benign-test
```

You should see a time-ordered timeline:

- Timestamps
- Event types (`file_modify`, `file_rename`, `process_create`, …)
- `file_path`, `entropy`
- `risk_score`, `decision`

This gives you a forensic view of what RansomScope observed and how it reacted.

---

### 8. Module overview

- **`collection/`** – Data collection  
  - Uses `watchdog` (inotify) for file system events.  
  - Uses `psutil` to capture new processes and parent/child relationships.  
  - Computes Shannon entropy and entropy deltas for modified files.  
  - Skips system directories (`/usr`, `/lib`, `/bin`, …).  
  - Emits structured `Event` objects.

- **`processing/`** – Feature extraction, model, explainability, decision  
  - **feature_engine/** – 5-second windows with 2-second overlap; features: `file_mod_count`, `rename_count`, `delete_count`, `entropy_avg_delta`, `child_process_count`, `privilege_flag`, `user_dir_activity_ratio`.  
  - **model/** – PyTorch LSTM; `ModelManager` for load/save and inference.  
  - **explain/** – Human-readable summaries from window features.  
  - **decision/** – Maps risk to actions: benign → none; suspicious → log; high → prompt (kill/quarantine/safe).

- **`forensics/`**  
  - SQLite timeline with columns:
    - `timestamp`, `event_type`, `process_id`, `file_path`, `entropy`, `risk_score`, `decision`, `incident_id`  
  - `replay_incident()` dumps a chronological narrative for an incident.

---

### 9. How to see if it works (verification steps)

Use these checks to confirm RansomScope is working:

| Step | Command | Expected result |
|------|---------|-----------------|
| **1. Collection layer** | `python test_monitor.py` | Prints events with `event_type`, `file_path`, `entropy`, `process_id`. No errors. |
| **2. Dataset generation** | `python dataset_gen.py --output ransomescope_dataset.csv --benign-runs 5 --ransom-runs 5` | Creates CSV. `head ransomescope_dataset.csv` shows rows with label + numeric features. |
| **3. Model training** | `python train.py --data ransomescope_dataset.csv --epochs 5` | Epoch logs with train_loss, val_loss, val_acc. File `ransomescope_lstm.pt` is created. |
| **4. Real-time run** | `python main.py run --watch /tmp/ransomescope_test --incident demo-1` | Logs "Watching: ...", "Windows: N/10", then RISK/LEVEL lines once 10 windows fill. |
| **4b. Demo high-risk run** | `python main.py run --watch /tmp/ransomescope_test --incident demo-1 --verbose --demo-force-high-risk` | Prints compact activity snapshots and reliably reaches high-risk prompt when ransomware signals appear. |
| **5. Trigger benign activity** | In another terminal: `mkdir -p /tmp/ransomescope_test; for i in {1..20}; do echo "hello $i" > /tmp/ransomescope_test/f_$i.txt; done` | RISK values mostly low; BENIGN_SIGNALS in explanations. |
| **6. Trigger ransomware-like** | `python scripts/generate_ransomware_activity.py /tmp/ransomescope_test` | RISK values rise; RANSOM_SIGNALS appear; possible high-risk alert. |
| **7. Forensic replay** | `python main.py replay demo-1` | Prints chronological timeline with timestamps, event types, risk scores, decisions. |

**Summary:** Steps 1–3 validate installation and training. Steps 4–7 validate the real-time pipeline. If step 1 fails (e.g. on Windows without inotify), use WSL or a Linux VM. If steps 2–3 succeed, the processing pipeline is intact.

---

### 10. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Only activity lines, no risk line yet | Sequence not ready yet (needs 10 windows) unless demo mode is enabled. | Keep monitoring longer, generate more activity, or run with `--demo-force-high-risk`. |
| Replay: "No events found" | Wrong `incident_id`. Replay must match `--incident` exactly. | Use the same ID: `python main.py replay benign-test` if you ran with `--incident benign-test`. |
| No file events at all | WSL/inotify sometimes misses events on `/tmp`. | Try watching your home dir: `--watch ~/ransomescope_test`, then run the benign script there. |
| Process suspended | You pressed `Ctrl+Z` instead of `Ctrl+C`. | Use `fg` to resume, then `Ctrl+C` to stop. Prefer `Ctrl+C` to stop cleanly. |
| `unrecognized arguments: --demo-force-high-risk` | You are running an older WSL copy of `main.py`. | Re-sync from `/mnt/c/Work/Cursor/ransomescope/` to `~/ransomscope/`, then run `python main.py run -h` to confirm flags. |

