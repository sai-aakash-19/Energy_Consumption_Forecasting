from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging

from model import forecast_next_hours, is_model_available, start_background_training, quick_forecast
from model import training_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ForecastRequest(BaseModel):
    horizon: int = Field(default=24, ge=1, le=168, description="Forecast horizon in hours (1-168)")


app = FastAPI(
    title="Energy Consumption Forecasting API",
    description="LSTM-based energy consumption forecasting for smart grids",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "message": "API is running"}


@app.post("/forecast")
def forecast(req: ForecastRequest):
    """
    Generate energy consumption forecast for the specified horizon.
    
    Args:
        req: ForecastRequest with horizon (1-168 hours)
    
    Returns:
        Forecast results with timestamps, values, and metrics
    """
    try:
        horizon = max(1, min(req.horizon, 168))
        logger.info(f"Forecast request for {horizon} hours")

        # If model is available, produce model forecast (fast due to persistence)
        if is_model_available():
            logger.info("Model found on disk — producing model forecast")
            result = forecast_next_hours(horizon=horizon)
            result["training"] = False
            logger.info("Forecast generated successfully")
            return result

        # Model not available: start background training and return a quick baseline forecast
        logger.info("Model not found — starting background training and returning quick forecast")
        start_background_training()
        result = quick_forecast(horizon=horizon)
        result["message"] = "Model training started in background. This is a quick baseline forecast."
        return result
    except Exception as e:
        logger.error(f"Forecast error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Forecast error: {str(e)}")


@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "message": "Energy Consumption Forecasting for Smart Grids",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "forecast": "/forecast (POST)",
            "docs": "/docs"
        },
    }


@app.get("/info")
def info():
    """Get API information and model metrics"""
    return {
        "name": "Energy Consumption Forecasting API",
        "model": "LSTM Neural Network",
        "description": "Predicts household power consumption for smart grid management",
        "features": [
            "Real-time energy forecasting",
            "Hourly predictions up to 7 days",
            "Performance metrics (MAE, RMSE, R², MAPE)"
        ]
    }


@app.get("/training")
def training():
    """Return training status and metrics if available."""
    try:
        status = training_status()
        return status
    except Exception as e:
        logger.error(f"Training status error: {e}")
        raise HTTPException(status_code=500, detail=f"Training status error: {str(e)}")


