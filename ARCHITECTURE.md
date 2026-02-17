# 🏗️ Architecture & Technical Details

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER (React + Vite)                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  App.jsx (Main Component)                             │  │
│  │  ├─ useEffect (API health check)                      │  │
│  │  ├─ useState (horizon, forecast, error, etc.)         │  │
│  │  ├─ handleForecast (POST request)                     │  │
│  │  └─ Render (JSX with components)                      │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  styles.css (Modern Dark Theme)                       │  │
│  │  ├─ Gradients & Glassmorphism                         │  │
│  │  ├─ Responsive Grid Layout                            │  │
│  │  └─ Animations & Transitions                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                    Chart.js (Visualization)                 │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/JSON
        ┌───────────────────────────────────────────────────────┐
        │         FastAPI Backend Server (Port 8000)            │
        │  ┌─────────────────────────────────────────────────┐  │
        │  │  app.py (API Layer)                             │  │
        │  │  ├─ POST /forecast (Main endpoint)              │  │
        │  │  ├─ GET /health (Status check)                  │  │
        │  │  ├─ GET /info (API information)                 │  │
        │  │  └─ CORS Middleware                             │  │
        │  └─────────────────────────────────────────────────┘  │
        │  ┌─────────────────────────────────────────────────┐  │
        │  │  model.py (ML Pipeline)                         │  │
        │  │  ├─ load_dataset()                              │  │
        │  │  ├─ scale_series()                              │  │
        │  │  ├─ create_sequences()                          │  │
        │  │  ├─ build_model() → LSTM                        │  │
        │  │  ├─ get_trained_model() [cached]                │  │
        │  │  └─ forecast_next_hours()                       │  │
        │  └─────────────────────────────────────────────────┘  │
        │            TensorFlow/Keras (Deep Learning)           │
        │            Scikit-learn (Preprocessing)               │
        │            Pandas (Data Handling)                     │
        └───────────────────────────────────────────────────────┘
                            ↕ File I/O
        ┌───────────────────────────────────────────────────────┐
        │              data/ (Dataset Storage)                  │
        │  household_power_consumption.txt (2.14M rows)         │
        └───────────────────────────────────────────────────────┘
```

---

## Data Pipeline

### 1. **Data Loading**
```
Raw CSV File
    ↓
pd.read_csv() with parsing
    ↓
Parse Datetime Index
    ↓
Convert to numeric types
    ↓
Clean DataFrame
```

**Code:**
```python
df = pd.read_csv(
    path,
    sep=";",
    parse_dates={"Datetime": ["Date", "Time"]},
    infer_datetime_format=True,
    low_memory=False,
    na_values=["?"],
)
```

### 2. **Data Preprocessing**
```
Raw Data
    ↓
Handle missing values (interpolation)
    ↓
Resample to hourly mean
    ↓
MinMax scaling (0-1)
    ↓
Ready for LSTM
```

**Code:**
```python
df.interpolate(method="time", inplace=True)  # Fill gaps
hourly_df = df.resample("H").mean()          # Aggregate
scaler = MinMaxScaler()                       # Scale
scaled_data = scaler.fit_transform(data)
```

### 3. **Sequence Creation**
```
Hourly time series
    ↓
Create 24-hour sliding windows
    ↓
Target = next hour value
    ↓
X: (N, 24, 1) sequences
Y: (N,) predictions
```

**Code:**
```python
for i in range(len(data) - seq_length):
    X.append(data[i : i + seq_length])      # 24 hours
    y.append(data[i + seq_length])          # Next hour
```

### 4. **Train/Test Split**
```
Total sequences
    ↓
80% → Training set
20% → Test set
    ↓
Train model
Evaluate on test
```

---

## LSTM Model Architecture

```
Input (24 × 1 sequences)
    ↓
[LSTM Layer 1]
  • Units: 128
  • Return sequences: True
  • Activation: tanh
    ↓
[Dropout 0.2]
    ↓
[LSTM Layer 2]
  • Units: 64
  • Return sequences: True
  • Activation: tanh
    ↓
[Dropout 0.2]
    ↓
[LSTM Layer 3]
  • Units: 32
  • Return sequences: False
  • Activation: tanh
    ↓
[Dropout 0.1]
    ↓
[Dense Layer]
  • Units: 16
  • Activation: ReLU
    ↓
[Output Layer]
  • Units: 1
  • Activation: Linear
    ↓
Prediction (1 value)
```

### Hyperparameters
```python
Optimizer:      Adam (learning rate: 0.001)
Loss:           Mean Squared Error (MSE)
Metrics:        MAE
Batch Size:     32
Max Epochs:     50
Early Stop:     patience=3
Dropout Rates:  0.2, 0.2, 0.1
```

---

## Forecasting Process

### Flow Diagram
```
Load Dataset
    ↓
Get Last 24 Hours (Scaled)
    ↓
FOR each hour in horizon:
  ├─ Predict next hour
  ├─ Append to sequence
  ├─ Slide window (remove oldest)
  └─ Repeat
    ↓
Inverse Transform (MinMax → kW)
    ↓
Generate Timestamps
    ↓
Return Results
```

### Code Example
```python
last_seq = scaled_df.values[-24:].reshape(1, 24, 1)  # 24-hour window

for _ in range(horizon):
    pred = model.predict(last_seq, verbose=0)
    
    # Append and slide window
    new_seq = np.concatenate([last_seq[0, 1:, 0], [pred[0, 0]]])
    last_seq = new_seq.reshape(1, 24, 1)

# Inverse transform back to kW
forecasts = scaler.inverse_transform(scaled_forecasts)
```

---

## API Request/Response Flow

### POST /forecast

**Request:**
```http
POST /forecast HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{
  "horizon": 24
}
```

**Processing:**
```
Validate horizon (1-168)
    ↓
Call forecast_next_hours(24)
    ↓
Load cached model
    ↓
Generate predictions
    ↓
Calculate metrics
    ↓
Format response
```

**Response:**
```json
{
  "horizon": 24,
  "timestamps": [
    "2025-02-11T15:00:00",
    "2025-02-11T16:00:00",
    ...
  ],
  "values": [
    1.234,
    1.456,
    ...
  ],
  "mae": 0.356,
  "rmse": 0.485,
  "r2": 0.876,
  "mape": 5.23
}
```

---

## Frontend Component Hierarchy

```
App (Main Component)
  ├─ Header
  │   ├─ Title & Subtitle
  │   └─ API Status Indicator
  │
  ├─ Main Content (Grid Layout)
  │   ├─ Left Panel (320px)
  │   │   └─ ControlsCard
  │   │       ├─ Input: Horizon
  │   │       ├─ Button: Generate
  │   │       ├─ Error Display
  │   │       └─ MetricsSummary
  │   │           ├─ MetricCard (MAE)
  │   │           ├─ MetricCard (RMSE)
  │   │           ├─ MetricCard (R²)
  │   │           └─ MetricCard (MAPE)
  │   │
  │   └─ Right Panel (Flexible)
  │       ├─ Tabs Navigation
  │       └─ VisualizationSection
  │           ├─ ForecastChart (Line)
  │           └─ MetricsChart (Bar)
  │
  └─ Footer
```

---

## State Management

### React Hooks Usage
```javascript
const [horizon, setHorizon] = useState(24)        // User input
const [loading, setLoading] = useState(false)     // Loading state
const [error, setError] = useState("")            // Error messages
const [forecast, setForecast] = useState(null)    // API response
const [apiStatus, setApiStatus] = useState("checking")  // API health
const [activeTab, setActiveTab] = useState("forecast")  // Tab state
```

### Effect Dependencies
```javascript
useEffect(() => {
  checkAPIHealth()
}, [])  // Run once on mount
```

---

## Performance Optimizations

### Frontend
- **Code Splitting**: Chart.js bundled separately
- **Lazy Rendering**: Charts only render after forecast
- **CSS Optimization**: Minimal repaints with GPU acceleration
- **Event Debouncing**: Input validation on every keystroke

### Backend
- **Model Caching**: LRU cache prevents retraining
- **Batch Processing**: Process 32 samples per batch
- **Early Stopping**: Avoid unnecessary epochs
- **Efficient I/O**: Single dataset load per session

### Infrastructure
- **CORS Middleware**: Fast request processing
- **Async Operations**: Non-blocking forecast generation
- **Error Handling**: Fast error responses

---

## CSS Architecture

### Theme Variables (Implicit)
```css
/* Colors */
Primary Cyan:      #38bdf8
Primary Green:     #22c55e
Dark Background:   #0f172a
Slate Text:        #9ca3af
Light Text:        #e5e7eb

/* Spacing */
Large Gap:    2rem
Medium Gap:   1.5rem
Small Gap:    0.75rem

/* Border Radius */
Cards:   12px
Inputs:  8px
Buttons: 8px
```

### Layout System
```css
Grid Layout:
  Desktop:  320px (left) + flexible (right)
  Tablet:   Single column (1024px breakpoint)
  Mobile:   Single column (640px breakpoint)

Flexbox:
  Header:   space-between + center
  Metrics:  2-column grid (responsive)
  Tabs:     flex with gap
```

---

## Error Handling Strategy

### Frontend
```javascript
try {
  const res = await fetch(...)
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.detail)
  }
} catch (err) {
  setError(err.message)  // Display to user
}
```

### Backend
```python
try:
  result = forecast_next_hours(horizon)
except Exception as e:
  logger.error(str(e))
  raise HTTPException(status_code=500, detail=str(e))
```

---

## Metrics Interpretation

### MAE (Mean Absolute Error)
- **Unit**: kW
- **Meaning**: Average prediction error
- **Lower**: Better
- **Example**: 0.356 kW = 356 W average error

### RMSE (Root Mean Squared Error)
- **Unit**: kW
- **Meaning**: Standard deviation of errors
- **Penalizes**: Large errors more
- **Example**: 0.485 kW = penalizes outliers

### R² Score
- **Range**: 0 to 1
- **Meaning**: Proportion of variance explained
- **1.0**: Perfect prediction
- **0.876**: Explains 87.6% of variance

### MAPE (Mean Absolute Percentage Error)
- **Unit**: Percentage (%)
- **Meaning**: Average percentage error
- **Example**: 5.23% = 5.23% off on average
- **Industry**: 5-10% is good

---

## Scaling & Load Handling

### Current Capacity
- **Single Model**: Trained once, reused via caching
- **Request Rate**: Handles any rate (stateless API)
- **Memory**: ~400MB for trained model
- **Dataset**: 2.14M rows (2GB file)

### For Production Scaling
- Deploy backend on Gunicorn/uWSGI with multiple workers
- Use reverse proxy (Nginx) for load balancing
- Cache predictions for common horizons
- Implement database for request logging
- Use async/await for concurrent requests

---

## Technology Stack Summary

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** | React | 18.3.1 | UI library |
| | Vite | 5.4.10 | Build tool |
| | Chart.js | 4.4.4 | Visualizations |
| **Backend** | FastAPI | 0.115.5 | Web framework |
| | Uvicorn | 0.32.0 | ASGI server |
| | TensorFlow | 2.18.0 | Deep learning |
| **Data** | Pandas | 2.2.3 | Data processing |
| | NumPy | 1.26.4 | Numerical computing |
| | Scikit-learn | 1.5.2 | ML utilities |

---

## Development Workflow

```
1. Code Change
    ↓
2. Frontend: Vite HMR reloads (automatic)
   Backend: Manual restart required
    ↓
3. Test in Browser
    ↓
4. Check Console for Errors (F12)
    ↓
5. Review API Response (Network tab)
    ↓
6. Production: Build and deploy
```

---

**Architecture Version**: 1.0
**Last Updated**: February 11, 2026
