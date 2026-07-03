"""
FastAPI application for Stock Trading Decision Support Tool.
Chinese A-share market focus, powered by AKShare.
"""

import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd

from auth_service import (
    CurrentUser,
    auth_config,
    create_dev_session,
    create_session_token,
    require_user,
    verify_google_id_token,
)

from data_service import (
    get_market_overview,
    get_stock_history,
    get_stock_realtime,
    search_stock,
    get_sector_list,
)
from indicators import calc_all_indicators
from signals import generate_signals
from quant_service import analyze_stock, data_requirements_payload, system_requirements_payload


class GoogleLoginRequest(BaseModel):
    credential: str


class DevLoginRequest(BaseModel):
    email: str

app = FastAPI(
    title="A股交易决策支持系统",
    description="Chinese A-share Trading Decision Support Tool",
    version="1.0.0",
)


def _auth_response(user: CurrentUser) -> dict[str, Any]:
    return {
        "code": 0,
        "data": {
            "token": create_session_token(user),
            "user": {
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "provider": user.provider,
            },
        },
    }

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _indicator_payload(history: list[dict]) -> dict:
    if not history:
        raise ValueError("历史数据为空，无法计算技术指标")

    df = pd.DataFrame(history)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = calc_all_indicators(df)
    df_tail = df.tail(120)

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

    for key in indicator_data:
        if key == "dates":
            continue
        indicator_data[key] = [None if pd.isna(v) else v for v in indicator_data[key]]

    return indicator_data


def _signal_payload(symbol: str, history: list[dict], realtime: dict | None = None) -> dict:
    if not history:
        raise ValueError(f"无法获取股票 {symbol} 的历史数据")

    df = pd.DataFrame(history)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    signal = generate_signals(df)
    signal["stock_info"] = realtime
    return signal


@app.get("/api/auth/config")
def api_auth_config():
    """Return frontend-safe authentication configuration."""
    return {"code": 0, "data": auth_config()}


@app.post("/api/auth/google")
def api_auth_google(payload: GoogleLoginRequest):
    """Validate Google ID token and enforce email whitelist."""
    user = verify_google_id_token(payload.credential)
    return _auth_response(user)


@app.post("/api/auth/dev")
def api_auth_dev(payload: DevLoginRequest):
    """Local development login, disabled unless DEV_LOGIN_ENABLED=true."""
    user = create_dev_session(str(payload.email))
    return _auth_response(user)


@app.get("/api/auth/me")
def api_auth_me(user: CurrentUser = Depends(require_user)):
    return {
        "code": 0,
        "data": {
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "provider": user.provider,
        },
    }


@app.get("/api/market/overview")
def api_market_overview(user: CurrentUser = Depends(require_user)):
    """Get market overview: indices + rise/fall stats."""
    try:
        data = get_market_overview()
        return {"code": 0, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取市场概览失败: {str(e)}")


@app.get("/api/stock/search")
def api_stock_search(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    user: CurrentUser = Depends(require_user),
):
    """Search stocks by code or name."""
    try:
        results = search_stock(keyword)
        return {"code": 0, "data": results}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@app.get("/api/stock/{symbol}/realtime")
def api_stock_realtime(symbol: str, user: CurrentUser = Depends(require_user)):
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
    user: CurrentUser = Depends(require_user),
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
def api_stock_indicators(symbol: str, user: CurrentUser = Depends(require_user)):
    """Get technical indicators for a stock."""
    try:
        history = get_stock_history(symbol, period="daily")
        return {"code": 0, "data": _indicator_payload(history)}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算技术指标失败: {str(e)}")


@app.get("/api/stock/{symbol}/signal")
def api_stock_signal(symbol: str, user: CurrentUser = Depends(require_user)):
    """Get trading signal for a stock."""
    try:
        history = get_stock_history(symbol, period="daily")
        realtime = None
        try:
            realtime = get_stock_realtime(symbol)
        except Exception:
            pass

        return {"code": 0, "data": _signal_payload(symbol, history, realtime)}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成交易信号失败: {str(e)}")


@app.get("/api/stock/{symbol}/detail")
def api_stock_detail(symbol: str, user: CurrentUser = Depends(require_user)):
    """Get realtime quote, history, indicators, and signal with one upstream history load."""
    realtime = None
    history = []
    indicators = None
    signal = None
    errors = {}

    try:
        realtime = get_stock_realtime(symbol)
    except Exception as e:
        errors["realtime"] = str(e)

    try:
        history = get_stock_history(symbol, period="daily")
    except Exception as e:
        errors["history"] = str(e)

    if history:
        try:
            indicators = _indicator_payload(history)
        except Exception as e:
            errors["indicators"] = str(e)

        try:
            signal = _signal_payload(symbol, history, realtime)
        except Exception as e:
            errors["signal"] = str(e)

    if realtime is None and not history:
        detail = errors.get("history") or errors.get("realtime") or "无法加载股票数据"
        raise HTTPException(status_code=400, detail=detail)

    return {
        "code": 0,
        "data": {
            "realtime": realtime,
            "history": history,
            "indicators": indicators,
            "signal": signal,
            "errors": errors,
            "partial": bool(errors),
        },
    }


@app.get("/api/sector/list")
def api_sector_list(user: CurrentUser = Depends(require_user)):
    """Get sector/industry ranking."""
    try:
        data = get_sector_list()
        return {"code": 0, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取板块数据失败: {str(e)}")


@app.get("/api/quant/requirements")
def api_quant_requirements(user: CurrentUser = Depends(require_user)):
    return {
        "code": 0,
        "data": {
            "system": system_requirements_payload(),
            "data": data_requirements_payload(),
        },
    }


@app.get("/api/quant/{symbol}/analysis")
def api_quant_analysis(symbol: str, user: CurrentUser = Depends(require_user)):
    realtime = None
    errors = {}

    try:
        realtime = get_stock_realtime(symbol)
    except Exception as e:
        errors["realtime"] = str(e)

    try:
        history = get_stock_history(symbol, period="daily")
        analysis = analyze_stock(symbol, history, realtime)
        analysis["errors"] = errors
        analysis["partial"] = bool(errors)
        return {"code": 0, "data": analysis}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"量化分析失败: {str(e)}")


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "A股交易决策支持系统"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


# --- Static file serving (production: serves frontend build) ---
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    def serve_spa(path: str):
        """Serve frontend SPA — all non-API routes return index.html."""
        file_path = STATIC_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
