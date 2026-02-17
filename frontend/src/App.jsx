import React, { useState, useEffect } from "react";
import { Line, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  BarElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Legend,
  Tooltip,
  Filler,
} from "chart.js";

ChartJS.register(
  LineElement,
  BarElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Legend,
  Tooltip,
  Filler
);

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [horizon, setHorizon] = useState(24);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [forecast, setForecast] = useState(null);
  const [apiStatus, setApiStatus] = useState("checking");
  const [activeTab, setActiveTab] = useState("forecast");

  // Check API health on mount
  useEffect(() => {
    checkAPIHealth();
  }, []);

  const checkAPIHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        setApiStatus("online");
      } else {
        setApiStatus("error");
      }
    } catch (err) {
      setApiStatus("offline");
    }
  };

  const handleForecast = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/forecast`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ horizon: Number(horizon) }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || `API error: ${res.status}`);
      }

      const data = await res.json();
      setForecast(data);
      setActiveTab("forecast");
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to generate forecast. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = () => {
    switch (apiStatus) {
      case "online":
        return "#22c55e";
      case "offline":
        return "#ef4444";
      case "error":
        return "#f59e0b";
      default:
        return "#9ca3af";
    }
  };

  const formatTimestamp = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const chartData =
    forecast &&
    (() => ({
      labels: forecast.timestamps.map(formatTimestamp),
      datasets: [
        {
          label: "Forecasted Power Consumption (kW)",
          data: forecast.values,
          borderColor: "rgba(54, 162, 235, 1)",
          backgroundColor: "rgba(54, 162, 235, 0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: "rgba(54, 162, 235, 0.8)",
          pointBorderColor: "rgba(54, 162, 235, 1)",
          pointRadius: 3,
          pointHoverRadius: 5,
        },
      ],
    }))();

  const metricsData = forecast && {
    labels: ["MAE", "RMSE", "R² Score", "MAPE (%)"],
    datasets: [
      {
        label: "Model Performance Metrics",
        data: [
          forecast.mae || 0,
          forecast.rmse || 0,
          (forecast.r2 || 0) * 100,
          forecast.mape || 0,
        ],
        backgroundColor: [
          "rgba(34, 197, 94, 0.7)",
          "rgba(59, 130, 246, 0.7)",
          "rgba(168, 85, 247, 0.7)",
          "rgba(251, 146, 60, 0.7)",
        ],
        borderColor: [
          "rgba(34, 197, 94, 1)",
          "rgba(59, 130, 246, 1)",
          "rgba(168, 85, 247, 1)",
          "rgba(251, 146, 60, 1)",
        ],
        borderWidth: 2,
      },
    ],
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div>
            <h1>⚡ Energy Consumption Forecasting</h1>
            <p>AI-Powered Smart Grid Management using LSTM Neural Networks</p>
          </div>
          <div className="api-status">
            <span className="status-indicator" style={{ backgroundColor: getStatusColor() }}></span>
            <span className="status-text">
              API {apiStatus === "online" ? "Online" : apiStatus === "offline" ? "Offline" : "Error"}
            </span>
          </div>
        </div>
      </header>

      <main className="content">
        <section className="controls-card">
          <h2>🎯 Forecast Configuration</h2>
          <div className="form-group">
            <label htmlFor="horizon" className="field">
              <span>Forecast Horizon (hours)</span>
              <div className="input-group">
                <input
                  id="horizon"
                  type="number"
                  min="1"
                  max="168"
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value)}
                  disabled={loading}
                />
                <span className="input-hint">1 hour to 7 days</span>
              </div>
            </label>
          </div>

          <button
            onClick={handleForecast}
            disabled={loading || apiStatus === "offline"}
            className="btn-primary"
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Generating Forecast...
              </>
            ) : (
              "🚀 Generate Forecast"
            )}
          </button>

          {error && <div className="error-box">{error}</div>}

          {forecast && (
            <div className="metrics-summary">
              <h3>📊 Model Performance</h3>
              <div className="metrics-grid">
                <div className="metric-card">
                  <span className="metric-label">MAE</span>
                  <span className="metric-value">{forecast.mae?.toFixed(3) || "N/A"}</span>
                  <span className="metric-unit">kW</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">RMSE</span>
                  <span className="metric-value">{forecast.rmse?.toFixed(3) || "N/A"}</span>
                  <span className="metric-unit">kW</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">R² Score</span>
                  <span className="metric-value">{(forecast.r2 * 100)?.toFixed(2) || "N/A"}%</span>
                  <span className="metric-unit">Accuracy</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">MAPE</span>
                  <span className="metric-value">{forecast.mape?.toFixed(2) || "N/A"}%</span>
                  <span className="metric-unit">Error</span>
                </div>
              </div>

              {/* 🆕 Model Architecture Information */}
              {forecast.model_info && (
                <div className="model-info-box">
                  <h4>🧠 Model Architecture</h4>
                  <div className="model-info-grid">
                    <div className="info-item">
                      <span className="info-label">Input Features:</span>
                      <span className="info-value">{forecast.model_info.num_features}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Sequence Length:</span>
                      <span className="info-value">{forecast.model_info.seq_length} hours (3 days)</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Architecture:</span>
                      <span className="info-value">Multi-layer LSTM</span>
                    </div>
                  </div>
                  {forecast.model_info.features && (
                    <div className="features-list">
                      <span className="features-label">Features Used:</span>
                      <div className="features-tags">
                        {forecast.model_info.features.map((f, i) => (
                          <span key={i} className="feature-tag">{f}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </section>

        {forecast && (
          <section className="visualization-section">
            <div className="tabs">
              <button
                className={`tab-button ${activeTab === "forecast" ? "active" : ""}`}
                onClick={() => setActiveTab("forecast")}
              >
                📈 Forecast Curve
              </button>
              <button
                className={`tab-button ${activeTab === "metrics" ? "active" : ""}`}
                onClick={() => setActiveTab("metrics")}
              >
                📊 Performance Metrics
              </button>
            </div>

            {activeTab === "forecast" && (
              <div className="chart-card">
                <h2>Power Consumption Forecast</h2>
                <Line
                  data={chartData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                      legend: {
                        display: true,
                        labels: { color: "#d1d5db", font: { size: 12 } },
                      },
                      tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.8)",
                        titleColor: "#e5e7eb",
                        bodyColor: "#d1d5db",
                      },
                    },
                    scales: {
                      x: {
                        grid: { color: "rgba(148, 163, 184, 0.1)" },
                        ticks: { color: "#9ca3af", maxTicksLimit: 12 },
                      },
                      y: {
                        grid: { color: "rgba(148, 163, 184, 0.1)" },
                        ticks: { color: "#9ca3af" },
                        title: {
                          display: true,
                          text: "Power (kW)",
                          color: "#d1d5db",
                        },
                      },
                    },
                  }}
                />
              </div>
            )}

            {activeTab === "metrics" && metricsData && (
              <div className="chart-card">
                <h2>Model Performance Metrics</h2>
                <Bar
                  data={metricsData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                      legend: {
                        display: true,
                        labels: { color: "#d1d5db", font: { size: 12 } },
                      },
                    },
                    scales: {
                      x: {
                        grid: { color: "rgba(148, 163, 184, 0.1)" },
                        ticks: { color: "#9ca3af" },
                      },
                      y: {
                        grid: { color: "rgba(148, 163, 184, 0.1)" },
                        ticks: { color: "#9ca3af" },
                      },
                    },
                  }}
                />
              </div>
            )}
          </section>
        )}

        {!forecast && (
          <section className="empty-state">
            <div className="empty-content">
              <div className="empty-icon">📊</div>
              <h2>No Forecast Yet</h2>
              <p>Configure the parameters and generate a forecast to visualize energy consumption predictions</p>
            </div>
          </section>
        )}
      </main>

      <footer className="footer">
        <div className="footer-content">
          <span>🔬 Energy Consumption Forecasting for Smart Grids | LSTM-based ML Model</span>
          <span>© 2026</span>
        </div>
      </footer>
    </div>
  );
}

export default App;

