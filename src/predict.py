# src/predict.py

import joblib
import numpy as np
import pandas as pd # Import pandas

def make_prediction(new_data):
    """
    Loads the trained model and makes a prediction on new data.
    """
    try:
        model = joblib.load('models/trained_model.pkl')
        print("✅ Model loaded successfully.")
    except FileNotFoundError:
        print("❌ Error: Model file not found. Please run main.py to train and save it first.")
        return

    # Use a DataFrame with column names to avoid the warning
    prediction = model.predict(new_data)
    result = prediction[0]

    print("\n--- Prediction Result ---")
    # Access data using column names for clarity
    print(f"Input Data: Age={new_data['age'].iloc[0]}, Salary={new_data['salary'].iloc[0]}")
    if result == 1:
        print("Outcome: [1] -> This person is LIKELY to purchase insurance.")
    else:
        print("Outcome: [0] -> This person is UNLIKELY to purchase insurance.")

if __name__ == "__main__":
    # Create a DataFrame for the new sample data
    # The column names MUST match the ones used in training
    sample_data = pd.DataFrame({
        'age': [48],
        'salary': [72]
    })
    
    make_prediction(sample_data)