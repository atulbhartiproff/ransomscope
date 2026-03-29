#!/usr/bin/env python3
"""
Evaluation Pipeline - Setup Verification Script

This script verifies that all required files and packages are installed
before running the main evaluation pipeline.

Usage:
    python evaluation/verify_setup.py
"""

import sys
import os
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
END = '\033[0m'

def print_status(message: str, status: str = "INFO") -> None:
    """Print colored status message."""
    if status == "OK":
        print(f"{GREEN}✓{END} {message}")
    elif status == "FAIL":
        print(f"{RED}✗{END} {message}")
    elif status == "WARN":
        print(f"{YELLOW}⚠{END} {message}")
    else:
        print(f"{BLUE}ℹ{END} {message}")

def check_file_exists(file_path: str, description: str = "") -> bool:
    """Check if a file exists."""
    path = Path(file_path)
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        print_status(f"{description or file_path} ({size_mb:.1f} MB)", "OK")
        return True
    else:
        print_status(f"{description or file_path} NOT FOUND", "FAIL")
        return False

def check_package(package_name: str, import_name: str = None) -> bool:
    """Check if a Python package is installed."""
    import_name = import_name or package_name
    try:
        __import__(import_name)
        print_status(f"Package: {package_name}", "OK")
        return True
    except ImportError:
        print_status(f"Package: {package_name} NOT INSTALLED", "FAIL")
        return False

def main():
    """Main verification routine."""
    print("\n" + "="*70)
    print("EVALUATION PIPELINE - SETUP VERIFICATION")
    print("="*70 + "\n")
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Track results
    all_ok = True
    
    # ===== CHECK REQUIRED FILES =====
    print(f"{BLUE}Checking required files...{END}\n")
    
    files_to_check = [
        ("ransomescope_dataset.csv", "Dataset (CSV)"),
        ("ransomescope_lstm.pt", "Trained model (PyTorch)"),
    ]
    
    for file_path, description in files_to_check:
        full_path = project_root / file_path
        if not check_file_exists(str(full_path), description):
            all_ok = False
    
    print()
    
    # ===== CHECK EVALUATION MODULES =====
    print(f"{BLUE}Checking evaluation modules...{END}\n")
    
    eval_modules = [
        ("evaluation/__init__.py", "Package init"),
        ("evaluation/metrics.py", "Metrics module"),
        ("evaluation/timing.py", "Timing module"),
        ("evaluation/plots.py", "Plots module"),
        ("evaluation/run_evaluation.py", "Main script"),
    ]
    
    for file_path, description in eval_modules:
        full_path = project_root / file_path
        if not check_file_exists(str(full_path), description):
            all_ok = False
    
    print()
    
    # ===== CHECK PYTHON PACKAGES =====
    print(f"{BLUE}Checking installed packages...{END}\n")
    
    required_packages = [
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("scikit-learn", "sklearn"),
        ("matplotlib", "matplotlib"),
        ("torch", "torch"),
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        if not check_package(package_name, import_name):
            missing_packages.append(package_name)
            all_ok = False
    
    print()
    
    # ===== OPTIONAL CHECKS =====
    print(f"{BLUE}Checking optional components...{END}\n")
    
    # Check if results directory exists
    results_dir = project_root / "evaluation" / "results"
    if results_dir.exists():
        print_status("evaluation/results/ directory exists", "OK")
    else:
        print_status("evaluation/results/ directory will be created on first run", "WARN")
    
    print()
    
    # ===== SUMMARY =====
    print("="*70)
    
    if all_ok and not missing_packages:
        print(f"{GREEN}✓ ALL CHECKS PASSED - READY TO RUN{END}\n")
        print("Next steps:")
        print("  1. python evaluation/run_evaluation.py")
        print("  2. View results in evaluation/results/")
        print()
        print("="*70 + "\n")
        return 0
    else:
        print(f"{RED}✗ SETUP INCOMPLETE - ACTION REQUIRED{END}\n")
        
        if missing_packages:
            print(f"{YELLOW}Missing packages:{END}")
            for pkg in missing_packages:
                print(f"  - {pkg}")
            print()
            print(f"{YELLOW}Install with:{END}")
            print(f"  pip install {' '.join(missing_packages)}")
            print()
        
        missing_files = []
        for file_path, description in files_to_check:
            full_path = project_root / file_path
            if not full_path.exists():
                missing_files.append((file_path, description))
        
        if missing_files:
            print(f"{YELLOW}Missing data files:{END}")
            for file_path, description in missing_files:
                print(f"  - {file_path}")
                print(f"    Description: {description}")
            print()
            print(f"{YELLOW}Please ensure these files exist before running evaluation.{END}")
            print()
        
        print("="*70 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
