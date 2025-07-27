import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from datetime import datetime
import numpy as np
from src.memory.memory_manager import MemoryManager
from prophet import Prophet


class Predictor:
    def __init__(self, model_name='arima', memory_manager: MemoryManager = None):
        self.model_name = model_name
        self.model = None
        self.series = None
        self.memory_manager = memory_manager

    def fetch_data_from_memory(self, chat_id: str, limit: int = 1000):
        if not self.memory_manager:
            raise ValueError("MemoryManager not configured.")

        history = self.memory_manager.get_history(chat_id, limit=limit)

        if not history:
            raise ValueError("No history found for the given chat_id.")

        timestamps = [datetime.fromisoformat(msg['timestamp']) for msg in history]
        # For simplicity, we'll use the length of the content as the data points
        data = [len(msg['content']) for msg in history]

        return self.preprocess_data(data, timestamps)

    def preprocess_data(self, data: list[float], timestamps: list[datetime]):
        # Create a pandas Series with a DatetimeIndex
        series = pd.Series(data, index=pd.to_datetime(timestamps))

        # Resample the data to a fixed frequency (e.g., daily) and fill missing values
        series = series.resample('D').sum().fillna(0)

        return series.values, series.index

    def ingest(self, data: list[float], timestamps: list[datetime]):
        self.series = pd.Series(data, index=pd.to_datetime(timestamps))
        # Data validation and normalization
        if self.series.isnull().any():
            raise ValueError("Input data contains missing values.")
        # Normalize data
        self.series = (self.series - self.series.mean()) / self.series.std()


    def predict(self, steps: int = 10) -> list[float]:
        if self.series is None:
            raise ValueError("No data ingested to make a prediction.")

        if self.model_name == 'arima':
            return self._predict_arima(steps)
        elif self.model_name == 'prophet':
            return self._predict_prophet(steps)
        else:
            raise ValueError(f"Unknown model: {self.model_name}")

    def _predict_arima(self, steps: int) -> list[float]:
        # Model training
        model = ARIMA(self.series, order=(5,1,0))
        model_fit = model.fit()
        # Prediction
        forecast = model_fit.forecast(steps=steps)
        return forecast.tolist()

    def _predict_prophet(self, steps: int) -> list[float]:
        df = self.series.reset_index()
        df.columns = ['ds', 'y']

        self.model = Prophet()
        self.model.fit(df)

        future = self.model.make_future_dataframe(periods=steps)
        forecast = self.model.predict(future)

        return forecast['yhat'].tail(steps).tolist()

    def detect_anomalies(self, threshold: float) -> bool:
        if self.series is None:
            raise ValueError("No data ingested to detect anomalies.")

        prediction = self.predict()

        if max(prediction) > threshold or min(prediction) < -threshold:
            return True
        return False

    def alert_user(self):
        print("Anomaly detected! Please check the latest forecast.")
        print("Suggestions: Adjust budget or increase stakes.")

    def show_forecast_in_console(self, steps: int = 10):
        try:
            forecast = self.predict(steps)
            print("--- Forecast ---")
            for i, value in enumerate(forecast):
                print(f"Step {i+1}: {value}")
            print("----------------")
        except ValueError as e:
            print(f"Error: {e}")
