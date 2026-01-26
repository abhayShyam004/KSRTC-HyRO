
# ML Configuration & Thresholds

# --- Feature Engineering ---
MIN_CATEGORY_SAMPLE_SIZE = 10  # Minimum samples to trust a route/stop encoding
SMOOTHING_ALPHA = 5.0          # Smoothing factor for Target Encoding (Balanced: 5.0)

# --- Traffic Model ---
TRAFFIC_FREQ_CUTOFF = 10       # Minimum route occurrences to learn specific duration
DEFAULT_CITY_SPEED_KMPH = 30   # Fallback speed

# --- Auto-Categorization ---
AUTO_CAT_MIN_SAMPLES = 50      # Minimum samples to consider upgrading category
AUTO_CAT_CV_THRESHOLD = 0.5    # Max Coefficient of Variation (Std/Mean) to consider "stable"
PROTECTED_TAGS = {'airport', 'transport_hub', 'terminal', 'hospital'}
HUB_DEMAND_THRESHOLD = 20      # Mean demand to upgrade to transport_hub
COMMERCIAL_DEMAND_THRESHOLD = 10 # Mean demand to upgrade to commercial

# --- Demand Model ---
DEMAND_MODEL_RETENTION = 5     # Keep last 5 versions of models

# --- Training ---
TRAINING_TIMEOUT_SEC = 300     # 5 minutes max training time
