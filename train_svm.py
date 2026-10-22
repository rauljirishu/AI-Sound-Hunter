# ============================================================
#  AI Sound Hunter – train_svm.py
#  Standalone script to train and evaluate the SVM classifier
#  Run: python train_svm.py
# ============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sound_system import SVMAudioClassifier
import numpy as np


def main():
    print("=" * 60)
    print("  AI Sound Hunter – SVM Audio Classifier Training")
    print("=" * 60)

    clf = SVMAudioClassifier()

    if not clf.available:
        print("\n[ERROR] scikit-learn is not installed.")
        print("Install it with:  pip install scikit-learn")
        return

    print("\nGenerating training data (simulated MFCC-like features)…")
    X, y = SVMAudioClassifier.generate_training_data(n_samples=2000)
    print(f"  Dataset: {len(X)} samples, {X.shape[1]} features")
    print(f"  Classes: {sorted(set(y))}")

    print("\nTraining SVM (RBF kernel, C=10)…")
    clf.train(n_samples=2000)

    print("\n--- Sample Predictions ---")
    test_cases = [
        (2.0,  "walk", 0.5, 5,  "Expected: silence or footstep"),
        (10.0, "walk", 2.0, 10, "Expected: footstep"),
        (22.0, "run",  4.0, 3,  "Expected: running"),
        (40.0, "door", 3.0, 1,  "Expected: door"),
        (70.0, "key",  5.0, 0,  "Expected: alert"),
    ]
    for intensity, src, amb, age, note in test_cases:
        pred = clf.predict(intensity, src, amb, age)
        print(f"  intensity={intensity:5.1f}  src={src:8s}  -> {pred:12s}  ({note})")

    print("\nTraining complete! Model saved to models/svm_classifier.pkl")
    print(f"Classifier accuracy: {clf.accuracy*100:.1f}%")


if __name__ == "__main__":
    main()
