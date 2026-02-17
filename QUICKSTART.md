# 🚀 Quick Start Guide

## Setup in 5 Minutes

### ✅ Prerequisites
- Python 3.8+ installed
- Node.js 16+ installed
- Dataset: `household_power_consumption.txt` in `data/` folder

### 🔧 Backend Setup

```powershell
# Open terminal in project root
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Start API server
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

**Wait until you see:**
```
Uvicorn running on http://127.0.0.1:8000
Application startup complete
```

This takes 2-3 minutes on first run (model training).

### 🎨 Frontend Setup

```bash
# Open NEW terminal in project root
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**You'll see:**
```
VITE v5.4.10  ready in XXX ms

➜  Local:   http://localhost:5173/
```

### 🌐 Open in Browser

Navigate to: **http://localhost:5173**

### 📊 Generate Your First Forecast

1. Keep `24` hours selected (or adjust 1-168)
2. Click **🚀 Generate Forecast**
3. Wait 10-30 seconds for results
4. View the forecast curve and metrics
5. Click **📊 Performance Metrics** tab to see model scores

---

## 🎯 Interface Guide

### **Left Panel: Controls**
- **Forecast Horizon**: Hours to predict (1-168)
- **Generate Forecast**: Run the model
- **Metrics Summary**: Shows MAE, RMSE, R², MAPE
- **API Status**: Green = Connected, Red = Offline

### **Right Panel: Charts**
- **Forecast Curve**: Shows power consumption prediction
- **Performance Metrics**: Bar chart of model metrics
- Toggle tabs to switch views

---

## 📡 API Testing

Test the API directly:

```bash
# Health check
curl http://127.0.0.1:8000/health

# Generate forecast for 24 hours
curl -X POST http://127.0.0.1:8000/forecast \
  -H "Content-Type: application/json" \
  -d "{\"horizon\": 24}"

# View API docs
# Open: http://127.0.0.1:8000/docs
```

---

## ❌ Troubleshooting

### Problem: "Port 8000 already in use"
```bash
# Use different port
uvicorn app:app --reload --port 8001
# Then update frontend API_BASE in src/App.jsx
```

### Problem: "Dataset not found"
- Download from: https://archive.ics.uci.edu/ml/datasets/individual+household+electric+power+consumption
- Save to: `data/household_power_consumption.txt`

### Problem: "API error 500"
- Backend is still training (wait 2-3 minutes)
- Check console for error messages
- Verify dataset has correct format

### Problem: "npm modules not found"
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 📚 Next Steps

1. **Explore the code**: Check improvements in IMPROVEMENTS.md
2. **Modify parameters**: Try different horizons (1, 48, 168 hours)
3. **Deploy to production**: Follow README.md "Building for Production"
4. **Customize**: Adjust model layers in `backend/model.py`

---

## 🎓 Key Files

| File | Purpose |
|------|---------|
| `backend/app.py` | API endpoints |
| `backend/model.py` | LSTM model & forecasting |
| `frontend/src/App.jsx` | Main UI component |
| `frontend/src/styles.css` | Modern dark theme |
| `data/household_power_consumption.txt` | Dataset (required) |

---

## 💡 Tips

✅ Keep both **backend** and **frontend** terminals running
✅ Check **API status** indicator in header
✅ First forecast takes longer due to model initialization
✅ Use **Tab key** to navigate tabs after generating forecast
✅ Check **browser console** (F12) for detailed errors

---

## 📊 Expected Results

**Typical model performance:**
- MAE: 0.3-0.5 kW
- RMSE: 0.4-0.6 kW
- R²: 0.80-0.90
- MAPE: 5-10%

Results vary based on data and training.

---

**Ready to forecast? Run the setup steps above!** ⚡
