"""
Technical indicators calculation module.
Supports: MA(5/10/20/60), MACD, RSI, KDJ
"""

import numpy as np
import pandas as pd


def calc_ma(close: pd.Series, periods: list[int] = None) -> dict[str, pd.Series]:
    """Calculate Moving Averages for given periods."""
    if periods is None:
        periods = [5, 10, 20, 60]
    result = {}
    for p in periods:
        result[f"MA{p}"] = close.rolling(window=p).mean()
    return result


def calc_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, pd.Series]:
    """
    Calculate MACD indicator.
    Returns: DIF, DEA, MACD histogram
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_hist = 2 * (dif - dea)
    return {"DIF": dif, "DEA": dea, "MACD": macd_hist}


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> dict[str, pd.Series]:
    """
    Calculate KDJ indicator.
    n: RSV period
    m1: K smoothing period
    m2: D smoothing period
    """
    lowest_low = low.rolling(window=n).min()
    highest_high = high.rolling(window=n).max()

    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(50)

    k = pd.Series(index=close.index, dtype=float)
    d = pd.Series(index=close.index, dtype=float)

    k.iloc[0] = 50
    d.iloc[0] = 50

    for i in range(1, len(close)):
        k.iloc[i] = (2 / 3) * k.iloc[i - 1] + (1 / 3) * rsv.iloc[i]
        d.iloc[i] = (2 / 3) * d.iloc[i - 1] + (1 / 3) * k.iloc[i]

    j = 3 * k - 2 * d

    return {"K": k, "D": d, "J": j}


def calc_all_indicators(df: pd.DataFrame) -> dict:
    """
    Calculate all technical indicators for a stock dataframe.
    Expects columns: open, high, low, close, volume
    Returns a dict of indicator values (last N rows for charting).
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ma_data = calc_ma(close)
    macd_data = calc_macd(close)
    rsi_data = calc_rsi(close)
    kdj_data = calc_kdj(high, low, close)

    # Add MAs to dataframe for convenience
    for key, val in ma_data.items():
        df[key] = val

    df["DIF"] = macd_data["DIF"]
    df["DEA"] = macd_data["DEA"]
    df["MACD"] = macd_data["MACD"]
    df["RSI"] = rsi_data
    df["K"] = kdj_data["K"]
    df["D"] = kdj_data["D"]
    df["J"] = kdj_data["J"]

    return df
