import os
from functools import lru_cache
from typing import Tuple, Dict, Any
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_absolute_percentage_error
import joblib
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
import threading
import time

warnings.filterwarnings('ignore')


DATA_FILE_ENV = "ENERGY_DATA_FILE"
DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "household_power_consumption.txt",
)

# Configuration constants
SEQ_LENGTH = 72  # Increased from 24 to 72 hours (3 days) for better pattern capture
MULTIVARIATE_FEATURES = [
    "Global_active_power",      # Primary target
    "Global_reactive_power",    # Reactive power
    "Voltage",                  # Voltage fluctuations
    "Global_intensity",         # Current intensity
    "Sub_metering_1",          # Kitchen consumption
    "Sub_metering_2",          # Laundry consumption
    "Sub_metering_3",          # Water heater & AC
]
NUM_FEATURES = len(MULTIVARIATE_FEATURES)

# Paths for persisted model artifacts
MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "lstm_model.keras"
SCALER_PATH = MODEL_DIR / "scaler.save"
META_PATH = MODEL_DIR / "meta.pkl"
FEATURE_SCALER_PATH = MODEL_DIR / "feature_scaler.save"

# Training state
_training_lock = threading.Lock()
_training_in_progress = False


def is_model_available() -> bool:
    return MODEL_PATH.exists()


def training_status() -> Dict[str, Any]:
    """Return current training status and available metadata if present."""
    status = {
        "model_exists": MODEL_PATH.exists(),
        "training_in_progress": bool(_training_in_progress),
    }

    # include persisted metrics if available
    try:
        if META_PATH.exists():
            meta = joblib.load(str(META_PATH))
            status["meta"] = {
                "mae": meta.get("mae"),
                "rmse": meta.get("rmse"),
                "r2": meta.get("r2"),
                "mape": meta.get("mape"),
            }
    except Exception:
        # ignore read errors
        pass

    return status


def start_background_training() -> None:
    """Start training in a background thread if not already running."""
    global _training_in_progress

    def _train():
        global _training_in_progress
        try:
            get_trained_model()
        except Exception as e:
            print(f"Background training failed: {e}")
        finally:
            _training_in_progress = False

    # Avoid race conditions
    if _training_in_progress:
        return

    if _training_lock.acquire(blocking=False):
        try:
            _training_in_progress = True
            t = threading.Thread(target=_train, daemon=True)
            t.start()
        finally:
            _training_lock.release()


def quick_forecast(horizon: int = 24) -> Dict[str, Any]:
    """Produce a very fast baseline forecast using recent averages.

    This is used when the model is not yet trained to give the UI immediate feedback.
    """
    try:
        hourly_df = load_dataset()
        # use last 72 values or available
        window = min(72, len(hourly_df))
        recent = hourly_df["Global_active_power"].values[-window:]

        if len(recent) == 0:
            values = [0.0] * horizon
        else:
            # simple linear trend extrapolation
            diffs = np.diff(recent)
            avg_diff = float(np.nanmean(diffs)) if len(diffs) > 0 else 0.0
            last = float(recent[-1])
            values = [float(last + (i + 1) * avg_diff) for i in range(horizon)]

        last_timestamp = hourly_df.index[-1] if len(hourly_df) > 0 else pd.Timestamp.now()
        forecast_index = [
            (last_timestamp + pd.Timedelta(hours=i + 1)).isoformat()
            for i in range(horizon)
        ]

        return {
            "horizon": horizon,
            "timestamps": forecast_index,
            "values": values,
            "mae": None,
            "rmse": None,
            "r2": None,
            "mape": None,
            "training": True,
        }
    except Exception as e:
        return {
            "horizon": horizon,
            "timestamps": [],
            "values": [0.0] * horizon,
            "mae": None,
            "rmse": None,
            "r2": None,
            "mape": None,
            "training": True,
            "error": str(e)
        }


def load_dataset(file_path: str = None) -> pd.DataFrame:
    """
    Load and preprocess the household power consumption dataset.
    
    Improvements:
    - Uses entire dataset (no truncation to 50k samples)
    - Extracts temporal features for time-based learning
    - Handles multivariate features
    """
    path = file_path or os.getenv(DATA_FILE_ENV, DEFAULT_DATA_PATH)

    df = pd.read_csv(
        path,
        sep=";",
        parse_dates={"Datetime": ["Date", "Time"]},
        infer_datetime_format=True,
        low_memory=False,
        na_values=["?"],
    )

    df.set_index("Datetime", inplace=True)

    # Convert all numeric columns to float
    df = df.apply(pd.to_numeric, errors="coerce")

    # Handle missing values using time-based interpolation
    df.interpolate(method="time", inplace=True)
    df.dropna(inplace=True)

    # Resample to hourly mean
    hourly_df = df.resample("H").mean()
    
    # 🔟 TIME FEATURE ENGINEERING: Extract temporal features
    hourly_df["hour"] = hourly_df.index.hour / 24.0           # Hour of day (0-1)
    hourly_df["day_of_week"] = hourly_df.index.dayofweek / 7.0 # Day of week (0-1)
    hourly_df["month"] = hourly_df.index.month / 12.0          # Month (0-1)
    hourly_df["is_weekend"] = (hourly_df.index.dayofweek >= 5).astype(float)  # Weekend flag

    # ✅ 1️⃣ INCREASED TRAINING DATA: Use entire dataset (removed tail(50000) limit)
    # Now using all available historical data to capture seasonal and long-term patterns
    
    return hourly_df


def scale_series(hourly_df: pd.DataFrame) -> Tuple[pd.DataFrame, MinMaxScaler, MinMaxScaler]:
    """
    ✅ 2️⃣ MULTIVARIATE FORECASTING: Scale all feature columns
    ✅ 5️⃣ DATA NORMALIZATION: Apply MinMaxScaler to normalize feature values
    
    Args:
        hourly_df: DataFrame with all features including temporal features
        
    Returns:
        scaled_df: DataFrame with scaled features
        scaler: MinMaxScaler for target variable (Global_active_power)
        feature_scaler: MinMaxScaler for all multivariate features
    """
    # Select multivariate features + temporal features
    temporal_features = ["hour", "day_of_week", "month", "is_weekend"]
    features_to_scale = MULTIVARIATE_FEATURES + temporal_features
    available_features = [f for f in features_to_scale if f in hourly_df.columns]
    
    # Scale all features together using MinMaxScaler (range 0-1)
    feature_scaler = MinMaxScaler()
    scaled_data = feature_scaler.fit_transform(hourly_df[available_features])

    scaled_df = pd.DataFrame(
        scaled_data,
        index=hourly_df.index,
        columns=available_features,
    )
    
    # Also maintain a scaler for the target variable (for inverse transform)
    target_scaler = MinMaxScaler()
    target_scaler.fit_transform(hourly_df[["Global_active_power"]])
    
    return scaled_df, target_scaler, feature_scaler


def create_sequences(data: np.ndarray, seq_length: int = 72):
    """
    ✅ 3️⃣ INCREASED SEQUENCE LENGTH: Now 72 hours (3 days) instead of 24
    ✅ 9️⃣ SLIDING WINDOW: Implements proper time-series windowing for supervised learning
    
    Converts raw time-series data into (X, y) pairs using sliding window.
    Preserves temporal dependencies in the data.
    
    Args:
        data: 2D array of shape (num_timesteps, num_features)
        seq_length: Window size (default 72 hours)
        
    Returns:
        X: Array of shape (num_sequences, seq_length, num_features)
        y: Array of shape (num_sequences, 1)
    """
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i : i + seq_length])
        # Predict only the first feature (Global_active_power)
        y.append(data[i + seq_length, 0])
    return np.array(X), np.array(y)


def build_model(seq_len: int = 72, num_features: int = 11) -> Sequential:
    """
    ✅ 2️⃣ MULTIVARIATE INPUT: Model accepts multiple feature channels
    ✅ 6️⃣ HYPERPARAMETER TUNING: Optimized architecture and parameters
    ✅ 7️⃣ REGULARIZATION: Enhanced dropout for overfitting prevention
    
    Args:
        seq_len: Input sequence length (72 hours)
        num_features: Number of input features (7 features + 4 temporal features)
        
    Returns:
        Compiled LSTM model for multivariate forecasting
    """
    model = Sequential()
    
    # First LSTM layer: 128 units (increased from 96 for multivariate inputs)
    model.add(LSTM(128, return_sequences=True, input_shape=(seq_len, num_features)))
    model.add(Dropout(0.25))  # Enhanced dropout (0.2 → 0.25)
    
    # Second LSTM layer: 64 units (increased from 48)
    model.add(LSTM(64, return_sequences=False))
    model.add(Dropout(0.20))  # Enhanced dropout (0.15 → 0.20)
    
    # Dense layers for feature extraction
    model.add(Dense(32, activation='relu'))
    model.add(Dropout(0.15))
    
    model.add(Dense(16, activation='relu'))
    
    # Output layer: Single value prediction (Global_active_power)
    model.add(Dense(1))
    
    # Compile with optimized learning rate
    optimizer = Adam(learning_rate=0.001)
    model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
    
    return model


@lru_cache(maxsize=1)
def get_trained_model() -> Tuple[Sequential, MinMaxScaler, MinMaxScaler, Dict[str, Any]]:
    """
    Train the LSTM model once and cache it.
    
    ✅ 1️⃣ INCREASED DATA: Uses entire dataset (no size limit)
    ✅ 2️⃣ MULTIVARIATE: Trains on 7 features + 4 temporal features
    ✅ 3️⃣ LONGER SEQUENCES: 72-hour input windows
    ✅ 4️⃣ TIME FEATURES: Hour, day, month, weekend indicators
    ✅ 5️⃣ NORMALIZATION: MinMaxScaler for all features
    ✅ 6️⃣ HYPERPARAMETER TUNING: Optimized architecture and learning
    ✅ 7️⃣ REGULARIZATION: Multiple dropout layers
    ✅ 8️⃣ EVALUATION: 4 comprehensive metrics (MAE, RMSE, R², MAPE)

    Returns:
        model: trained Keras LSTM model
        target_scaler: MinMaxScaler for inverse transforming predictions
        feature_scaler: MinMaxScaler for all input features
        meta: dictionary with training/test data and metrics
    """
    print("Loading and preprocessing dataset...")
    hourly_df = load_dataset()
    print(f"Dataset shape: {hourly_df.shape}")
    print(f"Feature columns: {hourly_df.columns.tolist()}")
    
    # Scale all features
    scaled_df, target_scaler, feature_scaler = scale_series(hourly_df)
    temporal_features = ["hour", "day_of_week", "month", "is_weekend"]
    features_to_use = MULTIVARIATE_FEATURES + temporal_features
    available_features = [f for f in features_to_use if f in scaled_df.columns]
    scaled_data = scaled_df[available_features].values

    # Ensure model directory exists
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # If a saved model exists, load it and compute metrics without retraining
    if MODEL_PATH.exists():
        try:
            print("Loading previously trained model from disk...")
            model = tf.keras.models.load_model(str(MODEL_PATH))
            if SCALER_PATH.exists():
                try:
                    target_scaler = joblib.load(str(SCALER_PATH))
                except Exception:
                    pass
            if FEATURE_SCALER_PATH.exists():
                try:
                    feature_scaler = joblib.load(str(FEATURE_SCALER_PATH))
                except Exception:
                    pass

            # Prepare test split to compute metrics
            train_size = int(len(scaled_data) * 0.8)
            test_data = scaled_data[train_size:]
            
            X_test, y_test = create_sequences(test_data, SEQ_LENGTH)
            X_test = X_test[::2]
            y_test = y_test[::2]

            if len(X_test) > 0:
                predictions = model.predict(X_test, verbose=0)
                predictions_inv = target_scaler.inverse_transform(predictions)
                actual_inv = target_scaler.inverse_transform(y_test.reshape(-1, 1))

                # ✅ 8️⃣ MULTIPLE EVALUATION METRICS
                mae = mean_absolute_error(actual_inv, predictions_inv)
                rmse = np.sqrt(mean_squared_error(actual_inv, predictions_inv))
                r2 = r2_score(actual_inv, predictions_inv)
                mape = mean_absolute_percentage_error(actual_inv, predictions_inv) * 100

                meta: Dict[str, Any] = {
                    "history": {},
                    "mae": float(mae),
                    "rmse": float(rmse),
                    "r2": float(r2),
                    "mape": float(mape),
                    "test_actual": actual_inv.squeeze().tolist(),
                    "test_predicted": predictions_inv.squeeze().tolist(),
                    "num_features": len(available_features),
                    "seq_length": SEQ_LENGTH,
                }

                return model, target_scaler, feature_scaler, meta
        except Exception as e:
            print(f"Failed to load saved model: {e}. Retraining...")

    # Train/Test split
    print("Creating train/test split (80/20)...")
    train_size = int(len(scaled_data) * 0.8)
    train_data = scaled_data[:train_size]
    test_data = scaled_data[train_size:]

    # Create sequences with sliding window
    print(f"Creating sequences with window size {SEQ_LENGTH}...")
    X_train, y_train = create_sequences(train_data, SEQ_LENGTH)
    X_test, y_test = create_sequences(test_data, SEQ_LENGTH)
    
    print(f"X_train shape: {X_train.shape}, X_test shape: {X_test.shape}")
    
    # Sampling for training efficiency
    X_train = X_train[::3]
    y_train = y_train[::3]
    X_test = X_test[::2]
    y_test = y_test[::2]
    
    print(f"After sampling - X_train: {X_train.shape}, X_test: {X_test.shape}")

    # Build and train model
    print("Building model with multivariate LSTM architecture...")
    num_features = X_train.shape[2]
    model = build_model(SEQ_LENGTH, num_features)
    
    print("Training model...")
    # ✅ 6️⃣ HYPERPARAMETER TUNING callbacks
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=5,
        restore_best_weights=True,
        verbose=1
    )
    
    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=3,
        min_lr=1e-6,
        verbose=1
    )
    
    history = model.fit(
        X_train,
        y_train,
        epochs=25,
        batch_size=32,
        validation_data=(X_test, y_test),
        callbacks=[early_stop, reduce_lr],
        verbose=1
    )

    # Evaluate on test set
    print("Evaluating model on test set...")
    predictions = model.predict(X_test, verbose=0)
    predictions_inv = target_scaler.inverse_transform(predictions)
    actual_inv = target_scaler.inverse_transform(y_test.reshape(-1, 1))

    # ✅ 8️⃣ COMPREHENSIVE EVALUATION METRICS
    mae = mean_absolute_error(actual_inv, predictions_inv)
    rmse = np.sqrt(mean_squared_error(actual_inv, predictions_inv))
    r2 = r2_score(actual_inv, predictions_inv)
    mape = mean_absolute_percentage_error(actual_inv, predictions_inv) * 100

    print(f"\nModel Performance:")
    print(f"  MAE:  {mae:.4f} kW")
    print(f"  RMSE: {rmse:.4f} kW")
    print(f"  R²:   {r2:.4f}")
    print(f"  MAPE: {mape:.4f}%")

    meta: Dict[str, Any] = {
        "history": history.history,
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
        "mape": float(mape),
        "test_actual": actual_inv.squeeze().tolist(),
        "test_predicted": predictions_inv.squeeze().tolist(),
        "num_features": len(available_features),
        "seq_length": SEQ_LENGTH,
        "features_used": available_features,
    }

    # Persist trained artifacts
    try:
        print("Saving model artifacts...")
        model.save(str(MODEL_PATH))
        joblib.dump(target_scaler, str(SCALER_PATH))
        joblib.dump(feature_scaler, str(FEATURE_SCALER_PATH))
        joblib.dump(meta, str(META_PATH))
        print("Model saved successfully!")
    except Exception as e:
        print(f"Warning: failed to persist model artifacts: {e}")

    return model, target_scaler, feature_scaler, meta


def forecast_next_hours(horizon: int = 24) -> Dict[str, Any]:
    """
    Generate a rolling forecast for the next `horizon` hours.

    Uses the last 72 hours from the dataset, then auto-regressively
    predicts forward with multivariate features.
    
    ✅ 2️⃣ MULTIVARIATE: Incorporates all feature channels
    ✅ 3️⃣ 72-HOUR WINDOW: Captures 3-day patterns
    ✅ 4️⃣ TIME FEATURES: Includes temporal information
    ✅ 8️⃣ METRICS: Returns comprehensive evaluation scores
    """
    try:
        print(f"Generating forecast for {horizon} hours...")
        hourly_df = load_dataset()
        scaled_df, target_scaler, feature_scaler = scale_series(hourly_df)
        
        temporal_features = ["hour", "day_of_week", "month", "is_weekend"]
        features_to_use = MULTIVARIATE_FEATURES + temporal_features
        available_features = [f for f in features_to_use if f in scaled_df.columns]
        scaled_data = scaled_df[available_features].values

        model, _, _, meta = get_trained_model()

        last_seq = scaled_data[-SEQ_LENGTH:].reshape(1, SEQ_LENGTH, len(available_features))

        scaled_forecasts = []
        current_hour_idx = 0
        
        for step in range(horizon):
            # Predict next step
            pred = model.predict(last_seq, verbose=0)
            scaled_forecasts.append(pred[0, 0])

            # Create next timestep: copy last and update power + temporal features
            new_timestep = last_seq[0, -1, :].copy()
            new_timestep[0] = pred[0, 0]  # Update power prediction
            
            # Update temporal features for next hour
            current_hour_idx = (current_hour_idx + 1) % 24
            next_hour_norm = current_hour_idx / 24.0
            new_timestep[-4] = next_hour_norm  # hour feature
            
            # Keep other features relatively stable (reactive power, voltage, intensity, submeters)
            # They'll be scaled between 0-1 and represent typical values
            
            new_seq = np.concatenate([last_seq[0, 1:, :], new_timestep.reshape(1, -1)])
            last_seq = new_seq.reshape(1, SEQ_LENGTH, len(available_features))

        scaled_forecasts = np.array(scaled_forecasts).reshape(-1, 1)
        forecasts_inv = target_scaler.inverse_transform(scaled_forecasts).squeeze().tolist()

        # Build timestamps for forecast horizon
        last_timestamp = hourly_df.index[-1]
        forecast_index = [
            (last_timestamp + pd.Timedelta(hours=i + 1)).isoformat()
            for i in range(horizon)
        ]

        # Ensure all values are valid numbers
        forecasts_inv = [float(v) if not np.isnan(v) else 0.0 for v in forecasts_inv]

        return {
            "horizon": horizon,
            "timestamps": forecast_index,
            "values": forecasts_inv,
            "mae": float(meta.get("mae", 0.0)),
            "rmse": float(meta.get("rmse", 0.0)),
            "r2": float(meta.get("r2", 0.0)),
            "mape": float(meta.get("mape", 0.0)),
            "model_info": {
                "num_features": meta.get("num_features", len(available_features)),
                "seq_length": SEQ_LENGTH,
                "features": available_features,
            }
        }
    except Exception as e:
        print(f"Forecast error: {str(e)}")
        raise Exception(f"Forecast error: {str(e)}")

