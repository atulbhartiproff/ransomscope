"""
Evaluation package initialization module.

This module provides easy access to all evaluation components:
- metrics: Classification metrics computation
- timing: Model performance timing measurements
- plots: Visualization functions for results
"""

from .metrics import (
    compute_all_metrics,
    compute_accuracy,
    compute_precision,
    compute_recall,
    compute_f1,
    compute_roc_auc,
    compute_confusion_matrix,
    compute_false_positive_rate,
    format_metrics_report,
)

from .timing import (
    measure_training_time,
    measure_inference_time,
    measure_prediction_speed,
    measure_prediction_with_probability,
    format_timing_report,
)

from .plots import (
    plot_confusion_matrix,
    plot_roc_curve,
    plot_precision_recall,
    plot_metrics_bar,
    plot_timing,
    plot_model_comparison,
)

__all__ = [
    # Metrics
    "compute_all_metrics",
    "compute_accuracy",
    "compute_precision",
    "compute_recall",
    "compute_f1",
    "compute_roc_auc",
    "compute_confusion_matrix",
    "compute_false_positive_rate",
    "format_metrics_report",
    # Timing
    "measure_training_time",
    "measure_inference_time",
    "measure_prediction_speed",
    "measure_prediction_with_probability",
    "format_timing_report",
    # Plots
    "plot_confusion_matrix",
    "plot_roc_curve",
    "plot_precision_recall",
    "plot_metrics_bar",
    "plot_timing",
    "plot_model_comparison",
]

__version__ = "1.0.0"
