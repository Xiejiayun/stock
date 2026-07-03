"""
Data service module using AKShare for Chinese A-share market data.
Provides: market overview, individual stock history, real-time quotes, sector data.
"""

import concurrent.futures
import logging
import os
import time
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd
from requests import sessions


# Simple time-based cache
_cache = {}
_cache_ttl = {}
CACHE_DURATION = int(os.getenv("CACHE_DURATION_SECONDS", "180"))
REQUEST_TIMEOUT = int(os.getenv("AKSHARE_REQUEST_TIMEOUT_SECONDS", "5"))
AKSHARE_TIMEOUT = int(os.getenv("AKSHARE_CALL_TIMEOUT_SECONDS", "5"))

logger = logging.getLogger(__name__)
_akshare_executor = concurrent.futures.ThreadPoolExecutor(max_workers=6)


def _install_default_request_timeout():
    """AKShare calls external HTTP APIs; do not let those calls hang forever."""
    original_request = sessions.Session.request

    if getattr(original_request, "_stock_timeout_patched", False):
        return

    def request_with_timeout(self, method, url, **kwargs):
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = REQUEST_TIMEOUT
        return original_request(self, method, url, **kwargs)

    request_with_timeout._stock_timeout_patched = True
    sessions.Session.request = request_with_timeout


_install_default_request_timeout()


def _get_cached(key: str):
    """Get value from cache if not expired."""
    if key in _cache and time.time() - _cache_ttl.get(key, 0) < CACHE_DURATION:
        return _cache[key]
    return None


def _get_stale(key: str):
    """Return stale cache when the upstream source is temporarily unavailable."""
    return _cache.get(key)


def _set_cached(key: str, value):
    """Set value in cache with timestamp."""
    _cache[key] = value
    _cache_ttl[key] = time.time()


def _call_akshare(label: str, func, *args, timeout: int = AKSHARE_TIMEOUT, **kwargs):
    future = _akshare_executor.submit(func, *args, **kwargs)
    return _resolve_akshare_future(label, future, timeout=timeout)


def _resolve_akshare_future(
    label: str,
    future: concurrent.futures.Future,
    cache_key: str | None = None,
    timeout: int = AKSHARE_TIMEOUT,
):
    try:
        result = future.result(timeout=timeout)
        if cache_key is not None:
            _set_cached(cache_key, result)
        return result
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        if cache_key is not None:
            stale = _get_stale(cache_key)
            if stale is not None:
                return stale
        raise TimeoutError(f"{label} 数据源响应超时") from exc
    except Exception:
        if cache_key is not None:
            stale = _get_stale(cache_key)
            if stale is not None:
                return stale
        raise


def _to_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_index_spot_df():
    cache_key = "index_spot_df"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        df = _call_akshare("指数行情", ak.stock_zh_index_spot_em)
        _set_cached(cache_key, df)
        return df
    except Exception:
        stale = _get_stale(cache_key)
        if stale is not None:
            return stale
        raise


def _get_a_spot_df():
    cache_key = "a_spot_df"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        df = _call_akshare("A股实时行情", ak.stock_zh_a_spot_em)
        _set_cached(cache_key, df)
        return df
    except Exception:
        stale = _get_stale(cache_key)
        if stale is not None:
            return stale
        raise


def get_market_overview() -> dict:
    """
    Get market overview: index quotes + rise/fall statistics.
    Returns dict with indices and rise/fall counts.
    """
    cached = _get_cached("market_overview")
    if cached is not None:
        return cached

    result = {
        "indices": [],
        "rise_fall": {},
        "distribution": None,
        "timestamp": datetime.now().isoformat(),
        "source_status": "ok",
        "message": "",
    }

    index_cache_key = "index_spot_df"
    market_cache_key = "a_spot_df"
    index_df = _get_cached(index_cache_key)
    market_df = _get_cached(market_cache_key)
    index_future = None if index_df is not None else _akshare_executor.submit(ak.stock_zh_index_spot_em)
    market_future = None if market_df is not None else _akshare_executor.submit(ak.stock_zh_a_spot_em)

    try:
        # Major indices: SSE Composite, SZSE Component, ChiNext
        index_codes = {
            "sh000001": "上证指数",
            "sz399001": "深证成指",
            "sz399006": "创业板指",
            "sh000016": "上证50",
            "sz399005": "中小板指",
        }

        df = index_df
        if df is None:
            df = _resolve_akshare_future("指数行情", index_future, index_cache_key)
        if df is None or df.empty:
            raise ValueError("指数行情为空")

        code_series = df["代码"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(6)
        for code, name in index_codes.items():
            row = df[code_series == code[-6:]]
            if row.empty:
                continue
            row = row.iloc[0]
            result["indices"].append({
                "code": code,
                "name": name,
                "price": _to_float(row.get("最新价")),
                "change": _to_float(row.get("涨跌额")),
                "change_pct": _to_float(row.get("涨跌幅")),
                "volume": _to_float(row.get("成交量")),
                "amount": _to_float(row.get("成交额")),
            })

    except Exception as e:
        logger.warning("Failed to load index data: %s", e)
        result["source_status"] = "degraded"
        result["message"] = "指数行情源暂时不可用"

    # Rise/Fall statistics
    try:
        df_market = market_df
        if df_market is None:
            df_market = _resolve_akshare_future("A股实时行情", market_future, market_cache_key)
        if df_market is not None and not df_market.empty:
            changes = pd.to_numeric(df_market["涨跌幅"], errors="coerce").dropna()
            total = len(changes)
            rise = int((changes > 0).sum())
            fall = int((changes < 0).sum())
            flat = int((changes == 0).sum())
            limit_up = int((changes >= 9.9).sum())
            limit_down = int((changes <= -9.9).sum())

            result["rise_fall"] = {
                "total": total,
                "rise": rise,
                "fall": fall,
                "flat": flat,
                "limit_up": limit_up,
                "limit_down": limit_down,
            }

            # Change distribution
            bins = [-100, -7, -5, -3, -1, 0, 1, 3, 5, 7, 100]
            labels = [
                "<-7%", "-7~-5%", "-5~-3%", "-3~-1%", "-1~0%",
                "0~1%", "1~3%", "3~5%", "5~7%", ">7%"
            ]
            dist = pd.cut(changes, bins=bins, labels=labels).value_counts().sort_index()
            result["distribution"] = {
                "labels": labels,
                "values": [int(dist.get(label, 0)) for label in labels],
            }
    except Exception as e:
        logger.warning("Failed to load A-share breadth data: %s", e)
        result["source_status"] = "degraded"
        result["message"] = result["message"] or "市场涨跌统计源暂时不可用"

    _set_cached("market_overview", result)
    return result


def get_stock_history(
    symbol: str,
    period: str = "daily",
    start_date: str = None,
    end_date: str = None,
    adjust: str = "qfq",
) -> list[dict]:
    """
    Get historical K-line data for a stock.

    Args:
        symbol: Stock code (e.g., "000001", "600519")
        period: "daily", "weekly", "monthly"
        start_date: Start date "YYYYMMDD"
        end_date: End date "YYYYMMDD"
        adjust: "qfq" (forward), "hfq" (backward), "" (none)

    Returns:
        List of OHLCV dicts
    """
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")

    cache_key = f"history_{symbol}_{period}_{start_date}_{end_date}_{adjust}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        df = _call_akshare(
            f"股票 {symbol} 历史行情",
            ak.stock_zh_a_hist,
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

        if df is None or df.empty:
            return []

        # Normalize column names
        col_map = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "涨跌幅": "change_pct",
            "涨跌额": "change",
            "换手率": "turnover",
        }
        df = df.rename(columns=col_map)

        # Ensure date is string
        df["date"] = df["date"].astype(str)

        records = df[["date", "open", "high", "low", "close", "volume"]].to_dict("records")

        # Convert numpy types to Python native
        for r in records:
            for k, v in r.items():
                if hasattr(v, "item"):
                    r[k] = v.item()
                elif isinstance(v, float) and pd.isna(v):
                    r[k] = 0

        _set_cached(cache_key, records)
        return records

    except Exception as e:
        stale = _get_stale(cache_key)
        if stale is not None:
            return stale
        raise ValueError(f"获取股票 {symbol} 历史数据失败: {str(e)}")


def get_stock_realtime(symbol: str) -> dict:
    """Get real-time quote for a stock."""
    cache_key = f"realtime_{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        df = _get_a_spot_df()
        if df is None or df.empty:
            raise ValueError("无法获取实时行情数据")

        row = df[df["代码"] == symbol]
        if row.empty:
            raise ValueError(f"未找到股票代码: {symbol}")

        row = row.iloc[0]
        result = {
            "code": symbol,
            "name": str(row.get("名称", "")),
            "price": _to_float(row.get("最新价")),
            "change": _to_float(row.get("涨跌额")),
            "change_pct": _to_float(row.get("涨跌幅")),
            "open": _to_float(row.get("今开")),
            "high": _to_float(row.get("最高")),
            "low": _to_float(row.get("最低")),
            "pre_close": _to_float(row.get("昨收")),
            "volume": _to_float(row.get("成交量")),
            "amount": _to_float(row.get("成交额")),
            "turnover": _to_float(row.get("换手率")),
            "pe": None if pd.isna(row.get("市盈率-动态")) else _to_float(row.get("市盈率-动态")),
            "pb": None if pd.isna(row.get("市净率")) else _to_float(row.get("市净率")),
            "market_cap": _to_float(row.get("总市值")),
            "float_cap": _to_float(row.get("流通市值")),
        }

        _set_cached(cache_key, result)
        return result

    except ValueError:
        raise
    except Exception as e:
        stale = _get_stale(cache_key)
        if stale is not None:
            return stale
        raise ValueError(f"获取股票 {symbol} 实时数据失败: {str(e)}")


def search_stock(keyword: str) -> list[dict]:
    """Search stocks by code or name keyword."""
    try:
        df = _get_a_spot_df()
        if df is None or df.empty:
            return []

        # Search by code or name
        mask = df["代码"].str.contains(keyword, na=False) | df["名称"].str.contains(
            keyword, na=False
        )
        matches = df[mask].head(20)

        results = []
        for _, row in matches.iterrows():
            results.append({
                "code": str(row.get("代码", "")),
                "name": str(row.get("名称", "")),
                "price": _to_float(row.get("最新价")),
                "change_pct": _to_float(row.get("涨跌幅")),
            })

        return results

    except Exception as e:
        raise ValueError(f"搜索失败: {str(e)}")


def get_sector_list() -> list[dict]:
    """Get sector/industry performance ranking."""
    cache_key = "sector_list"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        df = _call_akshare("行业板块排名", ak.stock_board_industry_name_em)
        if df is None or df.empty:
            return []
        results = []

        # Get detailed info for top sectors
        for _, row in df.head(30).iterrows():
            try:
                sector_name = str(row.get("板块名称", ""))
                results.append({
                    "name": sector_name,
                    "code": str(row.get("板块代码", "")),
                    "change_pct": _to_float(row.get("涨跌幅")),
                    "leader": str(row.get("领涨股票", "")) if pd.notna(row.get("领涨股票")) else "",
                    "leader_pct": _to_float(row.get("领涨股票-涨跌幅")),
                    "amount": _to_float(row.get("总市值")),
                })
            except Exception:
                continue

        # Sort by change_pct descending
        results.sort(key=lambda x: x["change_pct"], reverse=True)
        _set_cached(cache_key, results)
        return results

    except Exception as e:
        stale = _get_stale(cache_key)
        if stale is not None:
            return stale
        logger.warning("Failed to load sector data: %s", e)
        raise ValueError(f"获取板块数据失败: {str(e)}")


def get_stock_detail_data(symbol: str) -> dict:
    """
    Get comprehensive stock data including history and indicators.
    Used for the detail page.
    """
    history = get_stock_history(symbol, period="daily")
    realtime = get_stock_realtime(symbol)

    return {
        "realtime": realtime,
        "history": history,
    }
