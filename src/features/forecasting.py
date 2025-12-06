"""Time-series forecasting for edge traffic using Prophet or ARIMA."""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, lit, when, isnan, isnull, sum as spark_sum
from pyspark.sql.types import DoubleType, BooleanType, StringType
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Try importing Prophet
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    try:
        from fbprophet import Prophet
        PROPHET_AVAILABLE = True
    except ImportError:
        PROPHET_AVAILABLE = False
        print("Warning: Prophet not available. Will use ARIMA fallback.")

# Try importing statsmodels for ARIMA
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    print("Warning: statsmodels not available. Will use simple moving average.")


def build_edge_timeseries(df: DataFrame) -> Dict[Tuple[str, str, str], pd.DataFrame]:
    """
    Build monthly time series for each (prev, curr, type) edge.
    
    Args:
        df: Spark DataFrame with columns: prev, curr, type, month, n
        
    Returns:
        Dictionary mapping (prev, curr, type) -> pandas DataFrame with columns: month, n, date
    """
    print("Building time series for all edges...")
    
    # Aggregate by edge and month
    edge_monthly = df.groupBy("prev", "curr", "type", "month") \
        .agg(spark_sum("n").alias("n"))
    
    # Convert to pandas
    pdf = edge_monthly.toPandas()
    
    # Build time series per edge
    timeseries_dict = {}
    
    for (prev, curr, edge_type), group in pdf.groupby(['prev', 'curr', 'type']):
        group = group.sort_values('month')
        group['date'] = pd.to_datetime(group['month'] + '-01')
        timeseries_dict[(prev, curr, edge_type)] = group[['month', 'date', 'n']].reset_index(drop=True)
    
    print(f"Built time series for {len(timeseries_dict)} edges")
    return timeseries_dict


def fit_and_forecast(ts_df: pd.DataFrame, horizon: int = 1, model_type: str = 'auto') -> Dict[str, float]:
    """
    Fit forecasting model and predict next period.
    
    Args:
        ts_df: pandas DataFrame with columns: date, n
        horizon: Number of periods to forecast (default 1)
        model_type: 'prophet', 'arima', 'exponential', 'moving_avg', or 'auto'
        
    Returns:
        Dictionary with: forecast_n, forecast_lower, forecast_upper
    """
    if len(ts_df) < 3:
        return {
            'forecast_n': 0.0,
            'forecast_lower': 0.0,
            'forecast_upper': 0.0
        }
    
    # Prepare data
    ts_df = ts_df.sort_values('date')
    dates = ts_df['date'].values
    values = ts_df['n'].values.astype(float)
    
    # Remove zeros and handle missing values
    values = np.maximum(values, 0.1)  # Avoid log(0)
    
    # Determine model type
    if model_type == 'auto':
        if PROPHET_AVAILABLE:
            model_type = 'prophet'
        elif STATSMODELS_AVAILABLE:
            model_type = 'arima'
        else:
            model_type = 'moving_avg'
    
    try:
        if model_type == 'prophet' and PROPHET_AVAILABLE:
            return _forecast_prophet(dates, values, horizon)
        elif model_type == 'arima' and STATSMODELS_AVAILABLE:
            return _forecast_arima(values, horizon)
        elif model_type == 'exponential' and STATSMODELS_AVAILABLE:
            return _forecast_exponential(values, horizon)
        else:
            return _forecast_moving_avg(values, horizon)
    except Exception as e:
        print(f"Warning: Forecast failed, using moving average: {e}")
        return _forecast_moving_avg(values, horizon)


def _forecast_prophet(dates: np.ndarray, values: np.ndarray, horizon: int) -> Dict[str, float]:
    """Forecast using Prophet."""
    df_prophet = pd.DataFrame({
        'ds': pd.to_datetime(dates),
        'y': values
    })
    
    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode='additive'
    )
    model.fit(df_prophet)
    
    # Forecast next period
    future = model.make_future_dataframe(periods=horizon, freq='MS')
    forecast = model.predict(future)
    
    last_row = forecast.iloc[-1]
    return {
        'forecast_n': float(last_row['yhat']),
        'forecast_lower': float(last_row['yhat_lower']),
        'forecast_upper': float(last_row['yhat_upper'])
    }


def _forecast_arima(values: np.ndarray, horizon: int) -> Dict[str, float]:
    """Forecast using ARIMA."""
    try:
        # Simple ARIMA(1,1,1) model
        model = ARIMA(values, order=(1, 1, 1))
        fitted = model.fit()
        
        forecast = fitted.forecast(steps=horizon)
        conf_int = fitted.get_forecast(steps=horizon).conf_int()
        
        # Handle both pandas Series and numpy array
        if hasattr(forecast, 'iloc'):
            forecast_val = float(forecast.iloc[0])
            lower = float(conf_int.iloc[0, 0])
            upper = float(conf_int.iloc[0, 1])
        else:
            # numpy array
            forecast_val = float(forecast[0])
            lower = float(conf_int[0, 0])
            upper = float(conf_int[0, 1])
        
        return {
            'forecast_n': max(0, forecast_val),
            'forecast_lower': max(0, lower),
            'forecast_upper': max(0, upper)
        }
    except Exception as e:
        print(f"ARIMA failed: {e}, using moving average")
        return _forecast_moving_avg(values, horizon)


def _forecast_exponential(values: np.ndarray, horizon: int) -> Dict[str, float]:
    """Forecast using exponential smoothing."""
    try:
        model = ExponentialSmoothing(values, trend='add', seasonal=None)
        fitted = model.fit()
        
        forecast = fitted.forecast(steps=horizon)
        std_err = np.std(fitted.resid) if len(fitted.resid) > 0 else np.std(values)
        
        forecast_val = float(forecast.iloc[0])
        return {
            'forecast_n': max(0, forecast_val),
            'forecast_lower': max(0, forecast_val - 1.96 * std_err),
            'forecast_upper': max(0, forecast_val + 1.96 * std_err)
        }
    except Exception as e:
        print(f"Exponential smoothing failed: {e}, using moving average")
        return _forecast_moving_avg(values, horizon)


def _forecast_moving_avg(values: np.ndarray, horizon: int) -> Dict[str, float]:
    """Simple moving average forecast."""
    window = min(3, len(values))
    ma = np.mean(values[-window:])
    std = np.std(values[-window:]) if len(values) > 1 else ma * 0.1
    
    return {
        'forecast_n': float(ma),
        'forecast_lower': max(0, float(ma - 1.96 * std)),
        'forecast_upper': max(0, float(ma + 1.96 * std))
    }


def generate_forecasts_for_all_edges(
    spark: SparkSession,
    df: DataFrame,
    months: List[str],
    min_history_months: int = 6,
    forecast_ratio_threshold: float = 2.0,
    model_type: str = 'auto'
) -> DataFrame:
    """
    Generate forecasts for all edges and return as Spark DataFrame.
    
    Args:
        spark: SparkSession
        df: Clickstream DataFrame with prev, curr, type, month, n
        months: List of months in chronological order
        min_history_months: Minimum months of history required
        forecast_ratio_threshold: Ratio threshold for flagging
        model_type: Model type to use
        
    Returns:
        Spark DataFrame with forecast columns
    """
    print("=" * 80)
    print("FORECASTING: Generating forecasts for all edges")
    print("=" * 80)
    
    # Build time series
    timeseries_dict = build_edge_timeseries(df)
    
    # Get target month (last month)
    target_month = months[-1] if months else None
    if not target_month:
        print("No target month specified, skipping forecasting")
        return spark.createDataFrame([], schema="prev string, curr string, type string, month string, forecast_n double, forecast_lower double, forecast_upper double, forecast_ratio double, forecast_flag boolean")
    
    # Generate forecasts
    forecasts = []
    
    for (prev, curr, edge_type), ts_df in timeseries_dict.items():
        # Skip if insufficient history
        if len(ts_df) < min_history_months:
            continue
        
        # Get actual value for target month
        actual_row = ts_df[ts_df['month'] == target_month]
        if len(actual_row) == 0:
            continue
        
        actual_n = float(actual_row['n'].iloc[0])
        
        # Fit and forecast
        forecast_result = fit_and_forecast(ts_df, horizon=1, model_type=model_type)
        
        forecast_n = forecast_result['forecast_n']
        forecast_lower = forecast_result['forecast_lower']
        forecast_upper = forecast_result['forecast_upper']
        
        # Compute metrics
        forecast_error = actual_n - forecast_n
        forecast_ratio = actual_n / (forecast_n + 1e-6)
        
        # Flag if exceeds threshold
        forecast_flag = (
            actual_n > forecast_upper or
            forecast_ratio >= forecast_ratio_threshold
        )
        
        forecasts.append({
            'prev': str(prev),
            'curr': str(curr),
            'type': str(edge_type),
            'month': str(target_month),
            'forecast_n': float(forecast_n),
            'forecast_lower': float(forecast_lower),
            'forecast_upper': float(forecast_upper),
            'forecast_error': float(forecast_error),
            'forecast_ratio': float(forecast_ratio),
            'forecast_flag': bool(forecast_flag)
        })
    
    if not forecasts:
        print("No forecasts generated")
        return spark.createDataFrame([], schema="prev string, curr string, type string, month string, forecast_n double, forecast_lower double, forecast_upper double, forecast_ratio double, forecast_flag boolean")
    
    # Convert to Spark DataFrame
    forecast_df = spark.createDataFrame(forecasts)
    
    print(f"Generated forecasts for {len(forecasts)} edges")
    print(f"Forecasts with flag=True: {sum(1 for f in forecasts if f['forecast_flag'])}")
    
    return forecast_df
