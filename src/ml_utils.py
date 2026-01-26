
import os
import shutil
import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

class TargetEncoder(BaseEstimator, TransformerMixin):
    """
    Target Encoder with smoothing.
    Encodes categorical features based on the mean of the target variable.
    Fits only on training data to prevent leakage.
    Unknown categories in transform() are replaced by the global mean.
    """
    def __init__(self, cols=None, alpha=5.0):
        self.cols = cols # List of columns to encode
        self.alpha = alpha # Smoothing factor
        self.maps = {} # Stores {col: {category: value}}
        self.global_mean = 0.0

    def fit(self, X, y):
        # Allow fitting on DataFrame or numpy array (if cols provided)
        if isinstance(X, pd.DataFrame):
            df = X.copy()
        else:
            df = pd.DataFrame(X, columns=self.cols)
            
        df['target'] = y
        self.global_mean = df['target'].mean()
        
        if self.cols is None:
            self.cols = [c for c in df.columns if c != 'target']
            
        for col in self.cols:
            # Calculate stats
            stats = df.groupby(col)['target'].agg(['count', 'mean'])
            counts = stats['count']
            means = stats['mean']
            
            # Smooth mean = (count * mean + alpha * global_mean) / (count + alpha)
            smooth = (counts * means + self.alpha * self.global_mean) / (counts + self.alpha)
            
            self.maps[col] = smooth.to_dict()
            
        return self

    def transform(self, X):
        check_is_fitted(self, 'global_mean')
        
        if isinstance(X, pd.DataFrame):
            out = X.copy()
        else:
            out = pd.DataFrame(X, columns=self.cols)
            
        for col in self.cols:
            if col in self.maps:
                # Map values, fill unknowns with global_mean
                out[col] = out[col].map(self.maps[col]).fillna(self.global_mean)
                
        return out

class AtomicModelSaver:
    """
    Saves models atomically to prevent file corruption.
    """
    @staticmethod
    def save(model, filepath):
        """
        Saves to .tmp file then renames to target.
        """
        # Create directory if needed
        dirname = os.path.dirname(filepath)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
            
        tmp_path = filepath + ".tmp"
        
        # Save to temp
        joblib.dump(model, tmp_path)
        
        # Atomic rename (replace)
        # On Windows, os.replace is atomic for existing files since Python 3.3
        try:
            os.replace(tmp_path, filepath)
            print(f"[SafeSave] Saved model execution atomic: {filepath}")
        except OSError as e:
            # Fallback for older windows or lock issues: remove then rename
            print(f"[SafeSave] Atomic replace failed ({e}), attempting delete-rename...")
            if os.path.exists(filepath):
                os.remove(filepath)
            os.rename(tmp_path, filepath)

    @staticmethod
    def load(filepath):
        if not os.path.exists(filepath):
            return None
        return joblib.load(filepath)
