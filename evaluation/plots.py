"""
Plotting module for visualizing model evaluation results.

This module provides functions to create and save various evaluation plots
using matplotlib only (no seaborn). All plots are saved as PNG files.
"""

import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Union
from pathlib import Path


def plot_confusion_matrix(
    cm: np.ndarray,
    save_path: str = "evaluation/results/confusion_matrix.png",
    figsize: tuple = (8, 6)
) -> None:
    """
    Create and save a confusion matrix visualization.
    
    Args:
        cm: 2x2 confusion matrix [[TN, FP], [FN, TP]]
        save_path: Path to save the PNG file
        figsize: Figure size as (width, height) tuple
    
    Returns:
        None. Saves plot to file.
    
    Example:
        >>> from sklearn.metrics import confusion_matrix
        >>> cm = confusion_matrix(y_true, y_pred)
        >>> plot_confusion_matrix(cm)
    """
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)
    
    # Extract values from confusion matrix
    tn, fp, fn, tp = cm.ravel()
    
    # Create heatmap manually
    im = ax.imshow(cm, cmap='Blues', aspect='auto')
    
    # Add text annotations
    for i in range(2):
        for j in range(2):
            text = ax.text(j, i, cm[i, j],
                          ha="center", va="center", 
                          color="white" if cm[i, j] > cm.max() / 2 else "black",
                          fontsize=16, weight='bold')
    
    # Set labels and title
    ax.set_xlabel('Predicted Label', fontsize=12, weight='bold')
    ax.set_ylabel('True Label', fontsize=12, weight='bold')
    ax.set_title('Confusion Matrix', fontsize=14, weight='bold', pad=20)
    
    # Set tick labels
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(['Negative (0)', 'Positive (1)'])
    ax.set_yticklabels(['Negative (0)', 'Positive (1)'])
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Count', rotation=270, labelpad=20)
    
    # Adjust layout
    plt.tight_layout()
    
    # Create directory if it doesn't exist
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save figure
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_roc_curve(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    save_path: str = "evaluation/results/roc_curve.png",
    figsize: tuple = (8, 6)
) -> None:
    """
    Create and save ROC (Receiver Operating Characteristic) curve.
    
    Args:
        y_true: True binary labels
        y_proba: Predicted probabilities for positive class
        save_path: Path to save the PNG file
        figsize: Figure size as (width, height) tuple
    
    Returns:
        None. Saves plot to file.
    
    Example:
        >>> plot_roc_curve(y_test, y_proba)
    """
    
    from sklearn.metrics import roc_curve, roc_auc_score
    
    # ROC is undefined when only one class exists in y_true.
    unique_classes = np.unique(y_true)
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    if len(unique_classes) < 2:
        # Save an informative placeholder figure instead of raising.
        ax.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Reference line')
        ax.text(
            0.5,
            0.5,
            'ROC curve unavailable\n(only one class in y_true)',
            ha='center',
            va='center',
            fontsize=12,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
        )
        ax.legend(loc="lower right", fontsize=11, framealpha=0.95)
    else:
        # Calculate ROC curve
        fpr, tpr, thresholds = roc_curve(y_true, y_proba)
        roc_auc = roc_auc_score(y_true, y_proba)

        # Plot ROC curve
        ax.plot(fpr, tpr, color='darkorange', lw=2.5,
                label=f'ROC Curve (AUC = {roc_auc:.4f})')

        # Plot diagonal line (random classifier)
        ax.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--',
                label='Random Classifier (AUC = 0.5000)')
    
    # Set labels and title
    ax.set_xlabel('False Positive Rate', fontsize=12, weight='bold')
    ax.set_ylabel('True Positive Rate', fontsize=12, weight='bold')
    ax.set_title('ROC Curve', fontsize=14, weight='bold', pad=20)
    
    # Set axis limits
    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.02])
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add legend
    if len(unique_classes) >= 2:
        ax.legend(loc="lower right", fontsize=11, framealpha=0.95)
    
    # Adjust layout
    plt.tight_layout()
    
    # Create directory if it doesn't exist
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save figure
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_precision_recall(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    save_path: str = "evaluation/results/precision_recall.png",
    figsize: tuple = (8, 6)
) -> None:
    """
    Create and save Precision-Recall curve.
    
    Args:
        y_true: True binary labels
        y_proba: Predicted probabilities for positive class
        save_path: Path to save the PNG file
        figsize: Figure size as (width, height) tuple
    
    Returns:
        None. Saves plot to file.
    
    Example:
        >>> plot_precision_recall(y_test, y_proba)
    """
    
    from sklearn.metrics import precision_recall_curve, average_precision_score
    
    # PR can be plotted with one class, but average precision is not meaningful.
    unique_classes = np.unique(y_true)
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    if len(unique_classes) < 2:
        ax.text(
            0.5,
            0.5,
            'Precision-Recall summary is limited\n(only one class in y_true)',
            ha='center',
            va='center',
            fontsize=12,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
        )
    else:
        # Calculate precision-recall curve
        precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
        avg_precision = average_precision_score(y_true, y_proba)

        # Plot precision-recall curve
        ax.plot(recall, precision, color='darkgreen', lw=2.5,
                label=f'Precision-Recall Curve (AP = {avg_precision:.4f})')
    
    # Set labels and title
    ax.set_xlabel('Recall', fontsize=12, weight='bold')
    ax.set_ylabel('Precision', fontsize=12, weight='bold')
    ax.set_title('Precision-Recall Curve', fontsize=14, weight='bold', pad=20)
    
    # Set axis limits
    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.02])
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add legend
    if len(unique_classes) >= 2:
        ax.legend(loc="best", fontsize=11, framealpha=0.95)
    
    # Adjust layout
    plt.tight_layout()
    
    # Create directory if it doesn't exist
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save figure
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_metrics_bar(
    metrics_dict: Dict[str, float],
    save_path: str = "evaluation/results/metrics_bar.png",
    figsize: tuple = (10, 6)
) -> None:
    """
    Create and save a bar chart of evaluation metrics.
    
    Args:
        metrics_dict: Dictionary of metric names and values
        save_path: Path to save the PNG file
        figsize: Figure size as (width, height) tuple
    
    Returns:
        None. Saves plot to file.
    
    Example:
        >>> metrics = {'accuracy': 0.95, 'precision': 0.92, 'recall': 0.89, 'f1': 0.90}
        >>> plot_metrics_bar(metrics)
    """
    
    # Filter out non-numeric metrics (like confusion matrix)
    numeric_metrics = {}
    for key, value in metrics_dict.items():
        if isinstance(value, (int, float)) and not np.isnan(value):
            numeric_metrics[key] = value
    
    # Sort by value for better visualization
    sorted_metrics = dict(sorted(numeric_metrics.items(), key=lambda x: x[1], reverse=True))
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create bar chart
    names = list(sorted_metrics.keys())
    values = list(sorted_metrics.values())
    
    # Use color gradient based on values
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(values)))
    bars = ax.bar(names, values, color=colors, edgecolor='black', linewidth=1.5)
    
    # Add value labels on top of bars
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.4f}',
                ha='center', va='bottom', fontsize=10, weight='bold')
    
    # Set labels and title
    ax.set_ylabel('Score', fontsize=12, weight='bold')
    ax.set_title('Model Evaluation Metrics', fontsize=14, weight='bold', pad=20)
    
    # Set y-axis limits
    ax.set_ylim([0, 1.1])
    
    # Add horizontal line at y=0.5 for reference
    ax.axhline(y=0.5, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Random Baseline')
    
    # Rotate x-axis labels for readability
    plt.xticks(rotation=45, ha='right')
    
    # Add grid for y-axis
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # Add legend
    ax.legend(fontsize=10)
    
    # Adjust layout
    plt.tight_layout()
    
    # Create directory if it doesn't exist
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save figure
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_timing(
    train_time: float,
    inference_time: float,
    save_path: str = "evaluation/results/timing.png",
    figsize: tuple = (10, 6)
) -> None:
    """
    Create and save a visualization of timing metrics.
    
    Args:
        train_time: Training time in seconds
        inference_time: Inference time in milliseconds per sample
        save_path: Path to save the PNG file
        figsize: Figure size as (width, height) tuple
    
    Returns:
        None. Saves plot to file.
    
    Example:
        >>> plot_timing(45.5, 0.25)
    """
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    
    # --- Subplot 1: Training Time ---
    # Convert training time to hours if needed
    if train_time >= 3600:
        train_display = train_time / 3600
        train_unit = "hours"
    elif train_time >= 60:
        train_display = train_time / 60
        train_unit = "minutes"
    else:
        train_display = train_time
        train_unit = "seconds"
    
    bars1 = ax1.bar(['Training'], [train_display], color='steelblue', 
                    edgecolor='black', linewidth=2, width=0.5)
    
    # Add value label
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{train_display:.2f} {train_unit}',
                ha='center', va='bottom', fontsize=11, weight='bold')
    
    ax1.set_ylabel('Time', fontsize=11, weight='bold')
    ax1.set_title('Training Time', fontsize=12, weight='bold', pad=15)
    ax1.set_ylim([0, train_display * 1.2])
    ax1.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # --- Subplot 2: Inference Time ---
    # Calculate throughput
    throughput = 1000.0 / inference_time if inference_time > 0 else 0
    
    bars2 = ax2.bar(['Inference'], [inference_time], color='darkgreen', 
                    edgecolor='black', linewidth=2, width=0.5)
    
    # Add value label
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{inference_time:.4f} ms/sample\n({throughput:.1f} samples/s)',
                ha='center', va='bottom', fontsize=10, weight='bold')
    
    ax2.set_ylabel('Time (ms)', fontsize=11, weight='bold')
    ax2.set_title('Inference Time (per sample)', fontsize=12, weight='bold', pad=15)
    ax2.set_ylim([0, inference_time * 1.5])
    ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # Overall title
    fig.suptitle('Performance Timing Metrics', fontsize=14, weight='bold', y=0.98)
    
    # Adjust layout
    plt.tight_layout()
    
    # Create directory if it doesn't exist
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save figure
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_model_comparison(
    model_names: list,
    metrics: Dict[str, list],
    save_path: str = "evaluation/results/model_comparison.png",
    figsize: tuple = (12, 6)
) -> None:
    """
    Create and save a comparison chart for multiple models.
    
    Args:
        model_names: List of model names
        metrics: Dictionary where keys are metric names and values are lists
                of metric values per model
        save_path: Path to save the PNG file
        figsize: Figure size as (width, height) tuple
    
    Returns:
        None. Saves plot to file.
    
    Example:
        >>> metrics = {
        ...     'accuracy': [0.95, 0.92, 0.90],
        ...     'precision': [0.93, 0.90, 0.88],
        ...     'recall': [0.94, 0.91, 0.89],
        ...     'f1': [0.94, 0.90, 0.88]
        ... }
        >>> plot_model_comparison(['Model A', 'Model B', 'Model C'], metrics)
    """
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Setup x-axis
    x = np.arange(len(model_names))
    width = 0.2
    
    # Plot each metric
    colors = plt.cm.Set2(np.linspace(0, 1, len(metrics)))
    
    for idx, (metric_name, values) in enumerate(metrics.items()):
        offset = (idx - len(metrics)/2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=metric_name, 
                     color=colors[idx], edgecolor='black', linewidth=1.5)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}',
                   ha='center', va='bottom', fontsize=8)
    
    # Set labels and title
    ax.set_xlabel('Model', fontsize=12, weight='bold')
    ax.set_ylabel('Score', fontsize=12, weight='bold')
    ax.set_title('Model Comparison', fontsize=14, weight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(model_names)
    ax.set_ylim([0, 1.1])
    
    # Add grid
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # Add legend
    ax.legend(loc='lower left', fontsize=10, ncol=2, framealpha=0.95)
    
    # Adjust layout
    plt.tight_layout()
    
    # Create directory if it doesn't exist
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save figure
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
