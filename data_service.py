"""
Data service module using AKShare for Chinese A-share market data.
Provides: market overview, individual stock history, real-time quotes, sector data.
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from functools import lru_cache
import time


# Simple time-based cache
_cache = {}
_cache_ttl = {}
CACHE_DURATION = 60  # seconds


def _get_cached(key: str):
    """Get value from cache if not expired."""
    if key in _cache and time.time() - _cache_ttl.get(key, 0) < CACHE_DURATION:
        return _cache[key]
    return None


def _set_cached(key: str, value):
    """Set value in cache with timestamp."""
    _cache[key] = value
    _cache_ttl[key] = time.time()


def get_market_overview() -> dict:
    """
    Get market overview: index quotes + rise/fall statistics.
    Returns dict with indices and rise/fall counts.
    """
    cached = _get_cached("market_overview")
    if cached:
        return cached

    result = {"indices": [], "rise_fall": {}, "timestamp": datetime.now().isoformat()}

    try:
        # Major indices: SSE Composite, SZSE Component, ChiNext
        index_codes = {
            "sh000001": "上证指数",
            "sz399001": "深证成指",
            "sz399006": "创业板指",
            "sh000016": "上证50",
            "sz399005": "中小板指",
        }

        for code, name in index_codes.items():
            try:
                df = ak.stock_zh_index_spot_em()
                row = df[df["代码"] == code.replace("sh", "").replace("sz", "")]
                if not row.empty:
                    row = row.iloc[0]
                    result["indices"].append({
                        "code": code,
                        "name": name,
                        "price": float(row.get("最新价", 0)),
                        "change": float(row.get("涨跌额", 0)),
                        "change_pct": float(row.get("涨跌幅", 0)),
                        "volume": float(row.get("成交量", 0)),
                        "amount": float(row.get("成交额", 0)),
                    })
            except Exception:
                continue

    except Exception as e:
        # Fallback: try alternative API
        try:
            df = ak.stock_zh_index_spot_em()
            if df is not None and not df.empty:
                for _, row in df.head(5).iterrows():
                    result["indices"].append({
                        "code": str(row.get("代码", "")),
                        "name": str(row.get("名称", "")),
                        "price": float(row.get("最新价", 0)),
                        "change": float(row.get("涨跌额", 0)),
                        "change_pct": float(row.get("涨跌幅", 0)),
                        "volume": float(row.get("成交量", 0)),
                        "amount": float(row.get("成交额", 0)),
                    })
        except Exception:
            pass

    # Rise/Fall statistics
    try:
        df_market = ak.stock_zh_a_spot_em()
        if df_market is not None and not df_market.empty:
            changes = df_market["涨跌幅"].dropna()
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
    except Exception:
        pass

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
    if cached:
        return cached

    try:
        df = ak.stock_zh_a_hist(
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
        raise ValueError(f"获取股票 {symbol} 历史数据失败: {str(e)}")


def get_stock_realtime(symbol: str) -> dict:
    """Get real-time quote for a stock."""
    cache_key = f"realtime_{symbol}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            raise ValueError("无法获取实时行情数据")

        row = df[df["代码"] == symbol]
        if row.empty:
            raise ValueError(f"未找到股票代码: {symbol}")

        row = row.iloc[0]
        result = {
            "code": symbol,
            "name": str(row.get("名称", "")),
            "price": float(row.get("最新价", 0)),
            "change": float(row.get("涨跌额", 0)),
            "change_pct": float(row.get("涨跌幅", 0)),
            "open": float(row.get("今开", 0)),
            "high": float(row.get("最高", 0)),
            "low": float(row.get("最低", 0)),
            "pre_close": float(row.get("昨收", 0)),
            "volume": float(row.get("成交量", 0)),
            "amount": float(row.get("成交额", 0)),
            "turnover": float(row.get("换手率", 0)),
            "pe": float(row.get("市盈率-动态", 0)) if pd.notna(row.get("市盈率-动态")) else None,
            "pb": float(row.get("市净率", 0)) if pd.notna(row.get("市净率")) else None,
            "market_cap": float(row.get("总市值", 0)),
            "float_cap": float(row.get("流通市值", 0)),
        }

        _set_cached(cache_key, result)
        return result

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"获取股票 {symbol} 实时数据失败: {str(e)}")


def search_stock(keyword: str) -> list[dict]:
    """Search stocks by code or name keyword."""
    try:
        df = ak.stock_zh_a_spot_em()
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
                "price": float(row.get("最新价", 0)),
                "change_pct": float(row.get("涨跌幅", 0)),
            })

        return results

    except Exception as e:
        raise ValueError(f"搜索失败: {str(e)}")


def get_sector_list() -> list[dict]:
    """Get sector/industry performance ranking."""
    cache_key = "sector_list"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return []

        # Get sector performance
        df_perf = ak.stock_board_industry_cons_em(symbol=None)
    except Exception:
        pass

    try:
        # Alternative: use industry index spot data
        df = ak.stock_board_industry_name_em()
        results = []

        # Get detailed info for top sectors
        for _, row in df.head(30).iterrows():
            try:
                sector_name = str(row.get("板块名称", ""))
                results.append({
                    "name": sector_name,
                    "code": str(row.get("板块代码", "")),
                    "change_pct": float(row.get("涨跌幅", 0)) if pd.notna(row.get("涨跌幅")) else 0,
                    "leader": str(row.get("领涨股票", "")) if pd.notna(row.get("领涨股票")) else "",
                    "leader_pct": float(row.get("领涨股票-涨跌幅", 0)) if pd.notna(row.get("领涨股票-涨跌幅")) else 0,
                    "amount": float(row.get("总市值", 0)) if pd.notna(row.get("总市值")) else 0,
                })
            except Exception:
                continue

        # Sort by change_pct descending
        results.sort(key=lambda x: x["change_pct"], reverse=True)
        _set_cached(cache_key, results)
        return results

    except Exception as e:
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
