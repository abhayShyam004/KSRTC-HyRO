# src/model_training.py

import joblib
# Import a regression model
from sklearn.ensemble import RandomForestRegressor
# Import a regression metric
from sklearn.metrics import mean_absolute_error

def train_model(X_train, y_train):
    """
    Trains and saves a regression model.
    """
    print("Training RandomForestRegressor model...")
    # We use a Regressor because we are predicting a number (passenger_count)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    print("Model training complete.")
    
    print("Saving model...")
    joblib.dump(model, 'models/trained_demand_model.pkl')
    print("Model saved successfully as 'trained_demand_model.pkl'")
    
    return model

def evaluate_model(model, X_test, y_test):
    """
    Evaluates the regression model using Mean Absolute Error.
    """
    print("Evaluating model...")
    predictions = model.predict(X_test)
    # MAE tells us, on average, how many passengers our predictions are off by.
    mae = mean_absolute_error(y_test, predictions)
    print(f"📊 Model Mean Absolute Error (MAE) on Test Set: {mae:.2f} passengers")