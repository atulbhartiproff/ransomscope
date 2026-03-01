"""RansomScope configuration.

Central configuration for monitoring paths, excluded directories,
window parameters, and model settings.
"""
from pathlib import Path

# Paths to exclude from file monitoring (system directories)
EXCLUDED_PREFIXES: tuple[str, ...] = (
    "/usr",
    "/lib",
    "/lib64",
    "/bin",
    "/sbin",
    "/var/cache",
    "/var/lib",
    "/run",
    "/proc",
    "/sys",
    "/dev",
)

# Sliding window parameters
WINDOW_SIZE_SEC: float = 5.0
WINDOW_OVERLAP_SEC: float = 2.0
SEQUENCE_LENGTH: int = 10

# Feature dimensions (must match feature engine output)
FEATURE_DIM: int = 8  # file_mod, rename, delete, entropy_delta, child_proc, privilege, user_dir_ratio, file_create

# Model parameters
LSTM_HIDDEN_SIZE: int = 128
LSTM_NUM_LAYERS: int = 2
LSTM_DROPOUT: float = 0.2

# Risk thresholds
THRESHOLD_BENIGN: float = 0.4
THRESHOLD_SUSPICIOUS: float = 0.7

# Forensics
FORENSICS_DB_PATH: Path = Path("ransomescope_forensics.db")
