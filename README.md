## ⚡ Energy Consumption Forecasting for Smart Grids

A full-stack AI-powered application using LSTM neural networks to predict household energy consumption for efficient smart grid management.

### 🎯 Features

- **Advanced LSTM Model**: Multi-layer LSTM with dropout regularization for accurate forecasting
- **Modern React UI**: Beautiful, responsive interface with real-time visualizations
- **Performance Metrics**: MAE, RMSE, R² Score, and MAPE for model evaluation
- **Interactive Charts**: Line charts for forecasts and bar charts for performance metrics
- **Error Handling**: Robust error handling and validation throughout the stack
- **API Health Status**: Real-time API connectivity indicator
- **Tab Navigation**: Switch between forecast curve and performance metrics

### 📊 Project Structure

```
.
├── backend/
│   ├── app.py              # FastAPI application with endpoints
│   ├── model.py            # LSTM model, data loading, and forecasting logic
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # HTML entry point
│   ├── vite.config.mts     # Vite configuration
│   ├── package.json        # Node dependencies
│   └── src/
│       ├── App.jsx         # Main React component
│       ├── main.jsx        # React entry point
│       └── styles.css      # Modern dark-themed styling
├── data/
│   └── household_power_consumption.txt  # Dataset (UCI ML Repository)
├── mini_pro_5.py           # Original Colab notebook (reference)
└── README.md               # This file
```

### 📥 Dataset

Place the `household_power_consumption.txt` file in the `data/` directory:

- **Source**: UCI Machine Learning Repository
- **Format**: Semicolon-separated values (;)
- **Size**: ~2.14M rows × 9 columns
- **Time Range**: 2006-2010 household data

You can download it from: https://archive.ics.uci.edu/ml/datasets/individual+household+electric+power+consumption

### 🚀 Quick Start

#### Prerequisites

- Python 3.8+
- Node.js 16+ and npm
- Git (optional)

#### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

# On Windows CMD:
.venv\Scripts\activate.bat

# On Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at: **http://127.0.0.1:8000**

> **Note**: First run may take 2-3 minutes as the model trains on the dataset

#### Frontend Setup

```bash
# Open a new terminal, navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The UI will be available at: **http://localhost:5173**

### 📡 API Endpoints

#### 1. Health Check
```http
GET /health
```
Response:
```json
{
  "status": "ok",
  "message": "API is running"
}
```

#### 2. Generate Forecast
```http
POST /forecast
Content-Type: application/json

{
  "horizon": 24
}
```

**Parameters:**
- `horizon` (integer): Number of hours to forecast (1-168)

**Response:**
```json
{
  "horizon": 24,
  "timestamps": ["2025-02-11T15:00:00", ...],
  "values": [1.234, 1.456, ...],
  "mae": 0.356,
  "rmse": 0.485,
  "r2": 0.876,
  "mape": 5.23
}
```

#### 3. API Information
```http
GET /info
```

#### 4. Root Endpoint
```http
GET /
```

### 🧠 Model Architecture

The LSTM model consists of:
- **Input Layer**: 24-hour time series window
- **LSTM Layer 1**: 128 units with dropout (0.2)
- **LSTM Layer 2**: 64 units with dropout (0.2)
- **LSTM Layer 3**: 32 units with dropout (0.1)
- **Dense Layer 1**: 16 units with ReLU activation
- **Output Layer**: Single unit (power prediction)

**Training Configuration:**
- Optimizer: Adam
- Loss Function: Mean Squared Error (MSE)
- Metrics: MAE
- Early Stopping: Patience=3
- Max Epochs: 50

### 📈 Performance Metrics

- **MAE (Mean Absolute Error)**: Average absolute difference between predicted and actual values
- **RMSE (Root Mean Squared Error)**: Standard deviation of prediction errors
- **R² Score**: Coefficient of determination (0-1, higher is better)
- **MAPE (Mean Absolute Percentage Error)**: Percentage error measure

### 🛠️ Configuration

#### Environment Variables

Set `ENERGY_DATA_FILE` to use a custom dataset path:

```bash
# Windows PowerShell
$env:ENERGY_DATA_FILE = "C:\path\to\data.txt"

# Windows CMD
set ENERGY_DATA_FILE=C:\path\to\data.txt

# Linux/Mac
export ENERGY_DATA_FILE=/path/to/data.txt
```

#### API Port Configuration

Frontend expects API at `http://127.0.0.1:8000`. To change:
1. Update backend port in `backend/app.py` or command line
2. Update `API_BASE` in `frontend/src/App.jsx`

### 🎨 UI Components

- **Header**: Title, subtitle, and API status indicator
- **Control Panel**: Horizon input and forecast button
- **Metrics Summary**: Display of MAE, RMSE, R², and MAPE
- **Chart Tabs**: Toggle between forecast curve and performance metrics
- **Empty State**: Helpful message when no forecast is generated
- **Footer**: Project information and copyright

### 📦 Building for Production

#### Backend
```bash
cd backend
pip install -r requirements.txt
# Use a production server like Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

#### Frontend
```bash
cd frontend
npm install
npm run build
# Serve the dist folder with a web server
```

### 🐛 Troubleshooting

**Issue**: `ModuleNotFoundError` for TensorFlow/Keras
- **Solution**: `pip install tensorflow --upgrade`

**Issue**: API returns 500 error on first request
- **Solution**: Wait 2-3 minutes for model training to complete

**Issue**: CORS errors in console
- **Solution**: Ensure backend is running at `http://127.0.0.1:8000`

**Issue**: Port already in use
- **Solution**: Change port in vite.config.mts or uvicorn command

**Issue**: Dataset file not found
- **Solution**: Download from UCI ML Repository and place in `data/` directory

### 📚 Dependencies

**Backend:**
- FastAPI: Modern web framework
- Uvicorn: ASGI server
- TensorFlow/Keras: Deep learning framework
- Scikit-learn: ML preprocessing and metrics
- Pandas: Data manipulation
- NumPy: Numerical computing

**Frontend:**
- React: UI library
- Vite: Build tool and dev server
- Chart.js: Charting library
- react-chartjs-2: React wrapper for Chart.js

### 📖 Data Preprocessing

1. **Loading**: Parse semicolon-separated text file
2. **Parsing**: Combine Date and Time columns into Datetime index
3. **Type Conversion**: Convert strings to numeric values
4. **Missing Values**: Linear interpolation for time series data
5. **Resampling**: Convert to hourly mean consumption
6. **Scaling**: MinMax scaling (0-1) for neural network input

### 🔄 Forecasting Process

1. Load and preprocess historical data
2. Scale data using fitted MinMaxScaler
3. Create 24-hour sequences for training
4. Train LSTM model with validation split
5. Generate rolling forecast by:
   - Predicting next hour from last 24 hours
   - Appending prediction to sequence
   - Sliding window for subsequent predictions
6. Inverse transform scaled values to kW
7. Generate ISO-formatted timestamps

### 📊 Data Flow

```
Dataset → Preprocessing → Scaling → Sequence Creation → LSTM Training
                                                           ↓
Frontend ← API Response ← Inverse Transform ← Rolling Forecast ← Trained Model
```

### 🎓 Learning Outcomes

This project demonstrates:
- LSTM architecture for time series forecasting
- Data preprocessing and normalization
- Training/validation/test splitting
- Performance metrics evaluation
- FastAPI backend development
- React UI development
- RESTful API design
- Real-time data visualization

### 📝 License

This project is for educational purposes as part of a B.Tech 3rd Year mini project.

### 👨‍💼 Author

**B.Tech 3rd Year Student**
Energy Consumption Forecasting for Smart Grids

### 🤝 Contributing

Suggestions for improvements:
- Add more LSTM layers or attention mechanisms
- Implement ensemble forecasting methods
- Add support for multiple consumption channels
- Create forecast confidence intervals
- Add historical comparison charts

### 📞 Support

For issues or questions:
1. Check the Troubleshooting section
2. Verify dataset placement and format
3. Ensure all dependencies are installed
4. Check that both servers are running
5. Review API response in browser console

---

**Last Updated**: February 11, 2026
**Version**: 1.0.0
```json
{
  "horizon": 24,
  "timestamps": ["..."],
  "values": [123.4, 125.6, "..."],
  "mae": 0.123,
  "rmse": 0.456
}
```

### 3. Frontend Setup & Run

From the project root:

```bash
cd frontend
npm install
npm run dev
```

The UI will be available at `http://127.0.0.1:5173`.

By default, the frontend calls the backend at `http://127.0.0.1:8000`. Make sure the backend is running before using the UI.

### 4. How the Forecast Works

- Uses the original logic:
  - Cleans missing values with time interpolation.
  - Resamples to hourly mean.
  - Scales `Global_active_power` using MinMaxScaler.
  - Trains an LSTM model on 80% of the data, tests on 20%.
- `/forecast`:
  - Trains the model once (cached).
  - Takes the last 24 hours from the dataset and produces an auto-regressive forecast for the requested `horizon` (1–168 hours).
  - Returns:
    - **Forecast curve** (timestamps + values).
    - **MAE** and **RMSE** on the held-out test set.

