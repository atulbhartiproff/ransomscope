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
├── monitor/               # Real-time file + process monitoring
├── feature_engine/        # Sliding window feature extraction
├── model/                 # LSTM model + manager
├── explain/               # Lightweight explainability
├── decision/              # Decision engine (user prompts)
└── forensics/             # SQLite logging + replay
```

Run all commands from the `ransomescope/` directory (where `main.py` lives).

---

### 2. Installation (Fedora / Linux)

```bash
cd ransomescope
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

Use `--verbose` to log every event. Latency per inference should stay under 1000 ms.

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

- **`monitor/`**  
  - Uses `watchdog` (inotify) for file system events.  
  - Uses `psutil` to capture new processes and parent/child relationships.  
  - Computes Shannon entropy and entropy deltas for modified files.  
  - Skips system directories (`/usr`, `/lib`, `/bin`, …).  
  - Emits structured `Event` objects.

- **`feature_engine/`**  
  - Maintains 5-second windows with 2-second overlap.  
  - Keeps the last 10 windows as a sequence.  
  - Features per window:
    - `file_mod_count`, `rename_count`, `delete_count`  
    - `entropy_avg_delta`  
    - `child_process_count`  
    - `privilege_flag`  
    - `user_dir_activity_ratio`

- **`model/`**  
  - PyTorch `RansomScopeLSTM` with:
    - LSTM (`hidden_size=64`)  
    - Fully-connected output + sigmoid for risk score  
  - `ModelManager` for load/save and inference.

- **`explain/`**  
  - Simple thresholds over recent window features.  
  - Produces human-readable summaries:
    - e.g. “High rate of file modifications; strong increase in file entropy”.

- **`decision/`**  
  - Maps risk scores to:
    - `benign` → no action  
    - `suspicious` → log only  
    - `high` → prompt user to kill / quarantine / mark safe  
  - Uses `psutil` to terminate a process if you choose `kill`.

- **`forensics/`**  
  - SQLite timeline with columns:
    - `timestamp`, `event_type`, `process_id`, `file_path`, `entropy`, `risk_score`, `decision`, `incident_id`  
  - `replay_incident()` dumps a chronological narrative for an incident.

---

### 9. How to validate end-to-end

1. **Unit-ish checks**
   - `python test_monitor.py` to ensure events + entropy work.
   - `python dataset_gen.py` and inspect the CSV.
2. **Model training**
   - `python train.py --data ransomescope_dataset.csv`.
   - Confirm `ransomescope_lstm.pt` is created.
3. **Real-time run**
   - `python main.py run --watch /tmp/ransomescope_test --incident demo-incident-1`.
   - Generate benign + encrypted-like activity in `/tmp/ransomescope_test`.
   - Observe changing `risk_score` and explanations.
4. **Forensic replay**
   - `python main.py replay demo-incident-1`.
   - Inspect the reconstructed timeline.

If all of the above behave as expected, RansomScope is working end-to-end for this academic setup.

---

### 10. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Nothing shows in Terminal 1 | You should now see each event as `event #N file_create file=/path`. Risk scores appear only after 10 windows (~35s of activity). | Run the benign script, then keep RansomScope running longer or run the script multiple times. |
| Replay: "No events found" | Wrong `incident_id`. Replay must match `--incident` exactly. | Use the same ID: `python main.py replay benign-test` if you ran with `--incident benign-test`. |
| No file events at all | WSL/inotify sometimes misses events on `/tmp`. | Try watching your home dir: `--watch ~/ransomescope_test`, then run the benign script there. |
| Process suspended | You pressed `Ctrl+Z` instead of `Ctrl+C`. | Use `fg` to resume, then `Ctrl+C` to stop. Prefer `Ctrl+C` to stop cleanly. |

