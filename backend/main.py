"""
FastAPI application for Stock Trading Decision Support Tool.
Chinese A-share market focus, powered by AKShare.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from data_service import (
    get_market_overview,
    get_stock_history,
    get_stock_realtime,
    search_stock,
    get_sector_list,
    get_stock_detail_data,
)
from indicators import calc_all_indicators
from signals import generate_signals

app = FastAPI(
    title="A股交易决策支持系统",
    description="Chinese A-share Trading Decision Support Tool",
    version="1.0.0",
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/market/overview")
def api_market_overview():
    """Get market overview: indices + rise/fall stats."""
    try:
        data = get_market_overview()
        return {"code": 0, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取市场概览失败: {str(e)}")


@app.get("/api/stock/search")
def api_stock_search(keyword: str = Query(..., min_length=1, description="搜索关键词")):
    """Search stocks by code or name."""
    try:
        results = search_stock(keyword)
        return {"code": 0, "data": results}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@app.get("/api/stock/{symbol}/realtime")
def api_stock_realtime(symbol: str):
    """Get real-time quote for a stock."""
    try:
        data = get_stock_realtime(symbol)
        return {"code": 0, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实时行情失败: {str(e)}")


@app.get("/api/stock/{symbol}/history")
def api_stock_history(
    symbol: str,
    period: str = Query("daily", description="周期: daily/weekly/monthly"),
    days: int = Query(365, ge=30, le=3650, description="获取天数"),
):
    """Get historical K-line data."""
    try:
        data = get_stock_history(symbol, period=period)
        return {"code": 0, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史数据失败: {str(e)}")


@app.get("/api/stock/{symbol}/indicators")
def api_stock_indicators(symbol: str):
    """Get technical indicators for a stock."""
    try:
        history = get_stock_history(symbol, period="daily")
        if not history:
            raise ValueError(f"无法获取股票 {symbol} 的历史数据")

        df = pd.DataFrame(history)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = calc_all_indicators(df)

        # Return last 120 days of indicator data
        df_tail = df.tail(120)

        # Convert to serializable format
        indicator_data = {
            "dates": df_tail["date"].tolist(),
            "ma5": df_tail["MA5"].round(2).tolist(),
            "ma10": df_tail["MA10"].round(2).tolist(),
            "ma20": df_tail["MA20"].round(2).tolist(),
            "ma60": df_tail["MA60"].round(2).tolist() if "MA60" in df_tail.columns else [],
            "dif": df_tail["DIF"].round(4).tolist(),
            "dea": df_tail["DEA"].round(4).tolist(),
            "macd": df_tail["MACD"].round(4).tolist(),
            "rsi": df_tail["RSI"].round(2).tolist(),
            "k": df_tail["K"].round(2).tolist(),
            "d": df_tail["D"].round(2).tolist(),
            "j": df_tail["J"].round(2).tolist(),
        }

        # Replace NaN with None for JSON serialization
        for key in indicator_data:
            if key == "dates":
                continue
            indicator_data[key] = [
                None if pd.isna(v) else v for v in indicator_data[key]
            ]

        return {"code": 0, "data": indicator_data}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算技术指标失败: {str(e)}")


@app.get("/api/stock/{symbol}/signal")
def api_stock_signal(symbol: str):
    """Get trading signal for a stock."""
    try:
        history = get_stock_history(symbol, period="daily")
        if not history:
            raise ValueError(f"无法获取股票 {symbol} 的历史数据")

        df = pd.DataFrame(history)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        signal = generate_signals(df)

        # Also get realtime info
        try:
            realtime = get_stock_realtime(symbol)
            signal["stock_info"] = realtime
        except Exception:
            signal["stock_info"] = None

        return {"code": 0, "data": signal}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成交易信号失败: {str(e)}")


@app.get("/api/sector/list")
def api_sector_list():
    """Get sector/industry ranking."""
    try:
        data = get_sector_list()
        return {"code": 0, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取板块数据失败: {str(e)}")


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "A股交易决策支持系统"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
