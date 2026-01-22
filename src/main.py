# src/main.py

from sklearn.model_selection import train_test_split

# Import our custom functions from the other files
from data_preprocessing import load_data, preprocess_data
from model_training import train_model, evaluate_model

def run_pipeline():
    """
    Executes the entire ML pipeline from data loading to evaluation.
    """
    print("--- Starting ML Pipeline ---")

    # 1. Load and process data
    raw_df = load_data(is_dummy=True)
    X, y = preprocess_data(raw_df)

    # 2. Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )
    print(f"Data split: {len(X_train)} training samples, {len(X_test)} testing samples.")

    # 3. Train the model
    model = train_model(X_train, y_train)

    # 4. Evaluate the model
    evaluate_model(model, X_test, y_test)
    
    print("\n--- Pipeline execution finished successfully! ---")


if __name__ == "__main__":
    run_pipeline()