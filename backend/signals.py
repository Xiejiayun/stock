"""
Trading signal generation module.
Multi-indicator scoring system for buy/sell decisions.
"""

import pandas as pd
import numpy as np
from indicators import calc_all_indicators


def generate_signals(df: pd.DataFrame) -> dict:
    """
    Generate trading signals based on multiple technical indicators.

    Scoring system:
    - MA trend: +2/-2
    - MACD golden/dead cross: +2/-2
    - RSI overbought/oversold: +1/-1
    - KDJ golden/dead cross: +1/-1

    Total score range: -6 to +6

    Returns:
        dict with signal, confidence, score, and explanation
    """
    if len(df) < 60:
        return {
            "signal": "hold",
            "signal_cn": "观望",
            "confidence": 0,
            "score": 0,
            "explanation": "数据不足，无法生成有效信号（需要至少60个交易日数据）",
            "details": [],
        }

    df = calc_all_indicators(df.copy())

    score = 0
    details = []

    # --- MA Trend Analysis (+2 / -2) ---
    last = df.iloc[-1]
    prev = df.iloc[-2]

    ma_score = 0
    if not pd.isna(last.get("MA5")) and not pd.isna(last.get("MA20")):
        if last["MA5"] > last["MA10"] > last["MA20"]:
            ma_score = 2
            details.append("均线多头排列（MA5>MA10>MA20），趋势向上")
        elif last["MA5"] < last["MA10"] < last["MA20"]:
            ma_score = -2
            details.append("均线空头排列（MA5<MA10<MA20），趋势向下")
        elif last["MA5"] > last["MA20"]:
            ma_score = 1
            details.append("短期均线在长期均线上方，偏多")
        elif last["MA5"] < last["MA20"]:
            ma_score = -1
            details.append("短期均线在长期均线下方，偏空")
        else:
            details.append("均线交织，趋势不明")
    score += ma_score

    # --- MACD Analysis (+2 / -2) ---
    macd_score = 0
    if not pd.isna(last.get("DIF")) and not pd.isna(prev.get("DIF")):
        # Golden cross: DIF crosses above DEA
        if prev["DIF"] <= prev["DEA"] and last["DIF"] > last["DEA"]:
            macd_score = 2
            details.append("MACD金叉（DIF上穿DEA），买入信号")
        # Dead cross: DIF crosses below DEA
        elif prev["DIF"] >= prev["DEA"] and last["DIF"] < last["DEA"]:
            macd_score = -2
            details.append("MACD死叉（DIF下穿DEA），卖出信号")
        elif last["DIF"] > last["DEA"]:
            macd_score = 1
            details.append("MACD处于多头区域（DIF>DEA）")
        elif last["DIF"] < last["DEA"]:
            macd_score = -1
            details.append("MACD处于空头区域（DIF<DEA）")

        # MACD histogram trend
        if last["MACD"] > 0 and last["MACD"] > prev["MACD"]:
            details.append("MACD柱状图放大，动能增强")
        elif last["MACD"] < 0 and last["MACD"] < prev["MACD"]:
            details.append("MACD柱状图负值扩大，下跌动能增强")
    score += macd_score

    # --- RSI Analysis (+1 / -1) ---
    rsi_score = 0
    if not pd.isna(last.get("RSI")):
        rsi_val = last["RSI"]
        if rsi_val < 20:
            rsi_score = 1
            details.append(f"RSI={rsi_val:.1f}，严重超卖，可能反弹")
        elif rsi_val < 30:
            rsi_score = 1
            details.append(f"RSI={rsi_val:.1f}，超卖区域，关注反弹机会")
        elif rsi_val > 80:
            rsi_score = -1
            details.append(f"RSI={rsi_val:.1f}，严重超买，注意回调风险")
        elif rsi_val > 70:
            rsi_score = -1
            details.append(f"RSI={rsi_val:.1f}，超买区域，谨慎追高")
        else:
            details.append(f"RSI={rsi_val:.1f}，处于正常区间")
    score += rsi_score

    # --- KDJ Analysis (+1 / -1) ---
    kdj_score = 0
    if not pd.isna(last.get("K")) and not pd.isna(prev.get("K")):
        # KDJ golden cross: K crosses above D
        if prev["K"] <= prev["D"] and last["K"] > last["D"]:
            kdj_score = 1
            details.append("KDJ金叉（K上穿D），短线买入信号")
        elif prev["K"] >= prev["D"] and last["K"] < last["D"]:
            kdj_score = -1
            details.append("KDJ死叉（K下穿D），短线卖出信号")

        # J value extremes
        if last["J"] > 100:
            details.append(f"KDJ-J值={last['J']:.1f}，超买区域")
        elif last["J"] < 0:
            details.append(f"KDJ-J值={last['J']:.1f}，超卖区域")
    score += kdj_score

    # --- Final Signal Determination ---
    confidence = min(abs(score) / 6.0 * 100, 100)

    if score >= 4:
        signal = "strong_buy"
        signal_cn = "强烈买入"
    elif score >= 2:
        signal = "buy"
        signal_cn = "买入"
    elif score <= -4:
        signal = "strong_sell"
        signal_cn = "强烈卖出"
    elif score <= -2:
        signal = "sell"
        signal_cn = "卖出"
    else:
        signal = "hold"
        signal_cn = "观望"

    return {
        "signal": signal,
        "signal_cn": signal_cn,
        "confidence": round(confidence, 1),
        "score": score,
        "explanation": f"综合评分 {score}/6，{'多头' if score > 0 else '空头' if score < 0 else '中性'}信号",
        "details": details,
    }
