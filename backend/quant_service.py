"""Quantitative analysis service built on normalized stock history."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from indicators import calc_all_indicators
from signals import generate_signals


def _to_dataframe(history: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(history)
    if df.empty:
        raise ValueError("历史行情为空，无法进行量化分析")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"])
    if df.empty:
        raise ValueError("历史行情缺少有效收盘价")
    return df


def _max_drawdown(close: pd.Series) -> float:
    cumulative_max = close.cummax()
    drawdown = close / cumulative_max - 1
    return float(drawdown.min() * 100)


def _annualized_volatility(close: pd.Series, window: int = 20) -> float:
    returns = close.pct_change().dropna().tail(window)
    if returns.empty:
        return 0.0
    return float(returns.std() * np.sqrt(252) * 100)


def _position_advice(score: int, volatility: float, max_drawdown: float) -> dict[str, Any]:
    if score >= 4:
        base = 0.6
    elif score >= 2:
        base = 0.4
    elif score <= -2:
        base = 0.0
    else:
        base = 0.2

    if volatility > 45 or max_drawdown < -30:
        base *= 0.5
    elif volatility > 30 or max_drawdown < -20:
        base *= 0.75

    position = round(base, 2)
    return {
        "suggested_position_pct": int(position * 100),
        "max_single_position_pct": 60,
        "risk_budget_pct": 2,
        "stop_loss_pct": 8 if score >= 2 else 5,
    }


def _risk_level(volatility: float, max_drawdown: float) -> str:
    if volatility > 45 or max_drawdown < -35:
        return "high"
    if volatility > 28 or max_drawdown < -20:
        return "medium"
    return "low"


def analyze_stock(symbol: str, history: list[dict], realtime: dict | None = None) -> dict[str, Any]:
    df = _to_dataframe(history)
    indicators = calc_all_indicators(df.copy())
    signal = generate_signals(df.copy())

    close = df["close"]
    last_close = float(close.iloc[-1])
    ma20 = indicators["MA20"].iloc[-1]
    ma60 = indicators["MA60"].iloc[-1]
    volatility = _annualized_volatility(close)
    max_drawdown = _max_drawdown(close)
    risk_level = _risk_level(volatility, max_drawdown)

    trend = "neutral"
    if not pd.isna(ma20) and not pd.isna(ma60):
        if last_close > ma20 > ma60:
            trend = "uptrend"
        elif last_close < ma20 < ma60:
            trend = "downtrend"

    data_quality = {
        "sample_count": int(len(df)),
        "first_date": str(df["date"].iloc[0]) if "date" in df else "",
        "last_date": str(df["date"].iloc[-1]) if "date" in df else "",
        "missing_close_count": int(pd.isna(df["close"]).sum()),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    risks = []
    if risk_level == "high":
        risks.append("波动或回撤处于高位，仓位需要明显收缩")
    if trend == "downtrend":
        risks.append("价格处于空头趋势，避免逆势重仓")
    if realtime is None:
        risks.append("实时行情不可用，信号基于历史 K 线计算")
    if not risks:
        risks.append("未发现突出的单项风险，但仍需控制仓位")

    position = _position_advice(int(signal.get("score", 0)), volatility, max_drawdown)

    return {
        "symbol": symbol,
        "realtime": realtime,
        "signal": signal,
        "trend": trend,
        "risk": {
            "level": risk_level,
            "annualized_volatility_pct": round(volatility, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "notes": risks,
        },
        "position": position,
        "data_quality": data_quality,
        "decision": {
            "action": signal.get("signal", "hold"),
            "label": signal.get("signal_cn", "观望"),
            "confidence_pct": signal.get("confidence", 0),
            "summary": signal.get("explanation", "暂无信号"),
        },
        "disclaimer": "量化信号仅供研究参考，不构成投资建议。",
    }


def system_requirements_payload() -> dict[str, Any]:
    return {
        "product_scope": [
            "白名单用户访问的量化研究系统",
            "A 股行情、技术指标、策略信号和风险提示",
            "Azure App Service 上的 FastAPI + React 部署",
        ],
        "auth_requirements": [
            "Google 登录必须后端校验 ID Token",
            "登录邮箱必须存在于 ALLOWED_EMAILS 白名单",
            "业务 API 必须携带签名会话令牌",
        ],
        "quant_requirements": [
            "行情获取需要超时、缓存和降级",
            "策略计算复用同一份历史数据",
            "输出信号、风险等级、仓位建议和数据质量",
        ],
    }


def data_requirements_payload() -> dict[str, Any]:
    return {
        "sources": ["AKShare A 股实时行情", "AKShare 历史 K 线", "AKShare 行业板块"],
        "normalization": ["股票代码 6 位字符串", "日期 YYYY-MM-DD", "数值字段转原生 number"],
        "quality_controls": ["请求超时", "缓存复用", "旧缓存兜底", "partial/errors 字段暴露"],
        "derived_features": ["MA", "MACD", "RSI", "KDJ", "波动率", "最大回撤"],
    }
