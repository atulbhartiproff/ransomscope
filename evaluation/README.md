# Evaluation Pipeline Documentation

## Overview

The evaluation pipeline is a comprehensive suite of tools for assessing ransomware detection model performance. It measures accuracy, timing, and generates professional visualizations for presentation to instructors.

## Directory Structure

```
ransomescope/
├── evaluation/
│   ├── __init__.py           # Package initialization
│   ├── metrics.py            # Classification metrics computation
│   ├── timing.py             # Training/inference timing measurement
│   ├── plots.py              # Visualization functions
│   ├── run_evaluation.py     # Main evaluation orchestrator
│   └── results/              # Output directory (auto-created)
│       ├── confusion_matrix.png
│       ├── roc_curve.png
│       ├── precision_recall.png
│       ├── metrics_bar.png
│       └── timing.png
│
├── detection_analysis/
│   └── model/
│       └── lstm_model.pt     # Trained model file
│
├── data/
│   └── processed_sequences.csv  # Dataset (CSV)
│
└── requirements.txt          # Project dependencies
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `scikit-learn` - Metrics computation
- `matplotlib` - Visualization
- `pandas` - Data loading
- `numpy` - Numerical operations
- `torch` - Model loading (PyTorch)

### 2. Prepare Your Data

Ensure your dataset is available at: `data/processed_sequences.csv`

**CSV Format Requirements:**
- CSV delimiter: `,` (comma)
- Last column must be the binary target label (0 or 1)
- All other columns are features
- Example:
  ```
  feature_1,feature_2,feature_3,...,feature_n,label
  0.5,0.3,0.8,...,0.2,0
  0.6,0.4,0.9,...,0.3,1
  ...
  ```

### 3. Ensure Model is Available

Your trained PyTorch model should be at: `detection_analysis/model/lstm_model.pt`

The model should:
- Accept input of shape `(batch_size, num_features)`
- Output logits for binary classification
- Be compatible with `torch.load()`

### 4. Run Evaluation

```bash
python evaluation/run_evaluation.py
```

### 5. View Results

All outputs are saved to `evaluation/results/`:
- `confusion_matrix.png` - Classification confusion matrix
- `roc_curve.png` - Receiver Operating Characteristic curve
- `precision_recall.png` - Precision-Recall tradeoff
- `metrics_bar.png` - Performance metrics comparison
- `timing.png` - Training and inference time visualization

## Module Documentation

### metrics.py - Classification Metrics

Computes classification performance metrics using scikit-learn.

**Key Functions:**

```python
from evaluation.metrics import compute_all_metrics

# Compute all metrics at once
metrics = compute_all_metrics(
    y_true=y_test,
    y_pred=y_pred,
    y_proba=y_proba  # Optional: probability predictions
)

# Access results
print(f"Accuracy: {metrics['accuracy']}")
print(f"Precision: {metrics['precision']}")
print(f"Recall: {metrics['recall']}")
print(f"F1 Score: {metrics['f1']}")
print(f"ROC AUC: {metrics['roc_auc']}")
print(f"FPR: {metrics['fpr']}")
print(f"FNR: {metrics['fnr']}")
print(metrics['confusion_matrix'])

# Get formatted report
from evaluation.metrics import format_metrics_report
report = format_metrics_report(metrics)
print(report)
```

**Individual Metric Functions:**
- `compute_accuracy()` - Overall correctness
- `compute_precision()` - TP / (TP + FP)
- `compute_recall()` - TP / (TP + FN)
- `compute_f1()` - Harmonic mean of precision and recall
- `compute_roc_auc()` - Area under ROC curve
- `compute_confusion_matrix()` - 2×2 classification matrix
- `compute_false_positive_rate()` - FP / (FP + TN)
- `compute_false_negative_rate()` - FN / (FN + TP)

### timing.py - Performance Timing

Measures model training and inference speed.

**Key Functions:**

```python
from evaluation.timing import measure_training_time, measure_inference_time

# Measure training time (in seconds)
train_time = measure_training_time(model, X_train, y_train)
print(f"Training took {train_time:.2f} seconds")

# Measure inference time (in ms per sample)
per_sample_ms = measure_inference_time(model, X_test, samples_only=True)
print(f"Inference: {per_sample_ms:.4f} ms per sample")

# Get both total and per-sample times
total_ms, per_sample_ms = measure_inference_time(model, X_test, samples_only=False)
print(f"Total: {total_ms:.2f} ms, Per sample: {per_sample_ms:.4f} ms")

# Get formatted timing report
from evaluation.timing import format_timing_report
report = format_timing_report(
    train_time_seconds=train_time,
    inference_time_ms=per_sample_ms,
    n_test_samples=len(X_test)
)
print(report)
```

**Other Functions:**
- `measure_prediction_speed()` - Average time over multiple iterations
- `measure_prediction_with_probability()` - Time for probability predictions

### plots.py - Visualizations

Creates publication-quality plots using matplotlib (no seaborn).

**Key Functions:**

```python
from evaluation.plots import (
    plot_confusion_matrix,
    plot_roc_curve,
    plot_precision_recall,
    plot_metrics_bar,
    plot_timing
)

# Confusion Matrix
plot_confusion_matrix(
    cm=metrics['confusion_matrix'],
    save_path="evaluation/results/confusion_matrix.png"
)

# ROC Curve
plot_roc_curve(
    y_true=y_test,
    y_proba=y_proba,
    save_path="evaluation/results/roc_curve.png"
)

# Precision-Recall Curve
plot_precision_recall(
    y_true=y_test,
    y_proba=y_proba,
    save_path="evaluation/results/precision_recall.png"
)

# Metrics Bar Chart
plot_metrics_bar(
    metrics_dict={
        'accuracy': 0.95,
        'precision': 0.93,
        'recall': 0.94,
        'f1': 0.94,
        'roc_auc': 0.97
    },
    save_path="evaluation/results/metrics_bar.png"
)

# Timing Visualization
plot_timing(
    train_time=45.5,
    inference_time=0.25,
    save_path="evaluation/results/timing.png"
)

# Model Comparison (multiple models)
plot_model_comparison(
    model_names=['LSTM', 'Random Forest', 'SVM'],
    metrics={
        'accuracy': [0.95, 0.92, 0.90],
        'precision': [0.93, 0.90, 0.88],
        'recall': [0.94, 0.91, 0.89],
        'f1': [0.94, 0.90, 0.88]
    },
    save_path="evaluation/results/model_comparison.png"
)
```

## Example Output Format

### Console Output

When running `python evaluation/run_evaluation.py`:

```
======================================================================
RANSOMWARE DETECTION - MODEL EVALUATION PIPELINE
======================================================================

[1/6] LOADING DATASET
----------------------------------------------------------------------
Loading dataset from: c:\Work\Cursor\ransomescope\data\processed_sequences.csv
✓ Dataset loaded: 5000 samples, 128 columns
  Features shape: (5000, 127)
  Labels shape: (5000,)
  Label distribution: [3500  1500]

[2/6] LOADING MODEL
----------------------------------------------------------------------
Loading model from: c:\Work\Cursor\ransomescope\detection_analysis\model\lstm_model.pt
✓ Model loaded successfully
  Model type: LSTM

[3/6] PREPARING DATA
----------------------------------------------------------------------
Preparing dataset...
✓ Dataset split complete:
  Training set: 4000 samples (80%)
  Test set: 1000 samples (20%)
✓ Features normalized using StandardScaler

[4/6] MEASURING PERFORMANCE
----------------------------------------------------------------------
Training time measurement:
✓ Training completed in 45.23 seconds

Inference time measurement:
✓ Inference time: 0.2534 ms per sample
  Throughput: 3946.27 samples/second

[5/6] COMPUTING METRICS
----------------------------------------------------------------------
✓ Metrics computed successfully:
  - Accuracy: 0.9520
  - Precision: 0.9324
  - Recall: 0.9400
  - F1 Score: 0.9362
  - ROC AUC: 0.9876

[6/6] GENERATING VISUALIZATIONS
----------------------------------------------------------------------
Generating plots...
  - Confusion matrix... ✓
  - ROC curve... ✓
  - Precision-Recall curve... ✓
  - Metrics bar chart... ✓
  - Timing chart... ✓

============================================================
MODEL EVALUATION METRICS REPORT
============================================================

Accuracy:        0.9520
Precision:       0.9324
Recall:          0.9400
F1 Score:        0.9362

ROC AUC:         0.9876

False Positive Rate: 0.0129
False Negative Rate: 0.0600

Confusion Matrix:
  True Negatives:  689
  False Positives: 9
  False Negatives: 6
  True Positives:  296

============================================================

============================================================
TIMING PERFORMANCE REPORT
============================================================

Training Time:     45.23 seconds

Inference Time:    0.2534 ms per sample
Throughput:        3946.27 samples/second

Total inference time for 1000 samples: 0.25 seconds

============================================================

======================================================================
EVALUATION COMPLETE
======================================================================

Results saved to: c:\Work\Cursor\ransomescope\evaluation\results

Generated files:
  - confusion_matrix.png
  - roc_curve.png
  - precision_recall.png
  - metrics_bar.png
  - timing.png

======================================================================
```

## Advanced Usage

### Custom Evaluation Loop

```python
from evaluation import (
    compute_all_metrics,
    measure_inference_time,
    plot_confusion_matrix,
    plot_roc_curve
)
import numpy as np

# Your data
y_true = np.array([0, 1, 0, 1, 0, 1])
y_pred = np.array([0, 1, 1, 1, 0, 0])
y_proba = np.array([0.1, 0.9, 0.7, 0.85, 0.2, 0.4])

# Compute metrics
metrics = compute_all_metrics(y_true, y_pred, y_proba)

# Generate visualizations
plot_confusion_matrix(metrics['confusion_matrix'])
plot_roc_curve(y_true, y_proba)

# Print results
print(f"Accuracy: {metrics['accuracy']:.4f}")
print(f"F1 Score: {metrics['f1']:.4f}")
```

### Batch Evaluation of Multiple Models

```python
from evaluation import compute_all_metrics, plot_model_comparison

models = [model1, model2, model3]
model_names = ['LSTM', 'GRU', 'CNN-LSTM']

results = {}
for name, model in zip(model_names, models):
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    metrics = compute_all_metrics(y_test, y_pred, y_proba)
    results[name] = metrics

# Compare models
metrics_dict = {
    'accuracy': [results[name]['accuracy'] for name in model_names],
    'precision': [results[name]['precision'] for name in model_names],
    'recall': [results[name]['recall'] for name in model_names],
    'f1': [results[name]['f1'] for name in model_names],
}

plot_model_comparison(model_names, metrics_dict)
```

## Troubleshooting

### FileNotFoundError: Dataset not found
- **Solution:** Ensure `data/processed_sequences.csv` exists and path is correct
- Check: `ls data/processed_sequences.csv`

### FileNotFoundError: Model not found
- **Solution:** Ensure `detection_analysis/model/lstm_model.pt` exists
- Check: `ls detection_analysis/model/lstm_model.pt`

### ValueError: Shapes don't match
- **Solution:** Ensure predictions have same length as true labels
- Verify: `len(y_true) == len(y_pred) == len(y_proba)`

### RuntimeError: CUDA out of memory
- **Solution:** Reduce batch size or move model to CPU
- For CPU: Ensure model is on CPU before evaluation

### ImportError: No module named 'sklearn'
- **Solution:** Install scikit-learn
- Run: `pip install scikit-learn matplotlib pandas numpy torch`

## Performance Metrics Explained

| Metric | Formula | Interpretation |
|--------|---------|-----------------|
| **Accuracy** | (TP+TN)/(TP+TN+FP+FN) | Overall correctness |
| **Precision** | TP/(TP+FP) | Of positive predictions, how many are correct? |
| **Recall** | TP/(TP+FN) | Of actual positives, how many were found? |
| **F1 Score** | 2×(P×R)/(P+R) | Harmonic mean of precision and recall |
| **ROC AUC** | Area under ROC | Overall discrimination ability (0.5-1.0) |
| **FPR** | FP/(FP+TN) | False alarm rate |
| **FNR** | FN/(FN+TP) | Miss rate |

**For Ransomware Detection:**
- High **Recall** is critical (catch all ransomware)
- High **Precision** reduces false alarms
- **ROC AUC** shows overall discrimination quality

## File Summary

```
evaluation/
├── __init__.py (250 lines)           - Package exports
├── metrics.py (400+ lines)           - Metric computation functions
├── timing.py (350+ lines)            - Timing measurement functions
├── plots.py (600+ lines)             - Visualization functions  
└── run_evaluation.py (450+ lines)    - Main evaluation orchestrator

Total: 2000+ lines of well-documented code
```

## Requirements

```
scikit-learn>=1.0.0
matplotlib>=3.5.0
pandas>=1.3.0
numpy>=1.20.0
torch>=1.10.0
```

## License

Part of the RansomeScope ransomware detection project.

## Support

For issues or questions, consult the individual module docstrings:
```python
from evaluation import metrics
help(metrics.compute_all_metrics)
```
