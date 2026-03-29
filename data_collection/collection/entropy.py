"""Shannon entropy computation for file contents."""

import logging
import math
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def compute_shannon_entropy(file_path: str | Path) -> Optional[float]:
    """Compute Shannon entropy of file contents.

    H(X) = -sum(p(x) * log2(p(x))) for each byte value x.

    Returns:
        Entropy value in bits (0-8 range), or None if file cannot be read.
    """
    path = Path(file_path) if isinstance(file_path, str) else file_path

    if not path.exists() or not path.is_file():
        return None

    try:
        data = path.read_bytes()
    except (PermissionError, OSError, IOError) as e:
        logger.debug("Cannot read file %s: %s", path, e)
        return None

    if len(data) == 0:
        return 0.0

    # Count byte frequencies
    freq: dict[int, int] = {}
    for byte_val in data:
        freq[byte_val] = freq.get(byte_val, 0) + 1

    n = len(data)
    entropy = 0.0

    for count in freq.values():
        p = count / n
        if p > 0:
            entropy -= p * math.log2(p)

    return round(entropy, 2)
