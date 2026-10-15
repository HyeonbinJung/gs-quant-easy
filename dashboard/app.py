"""
gs-quant-easy 대시보드

gs_quant.timeseries 분석 함수를 웹 화면에서 바로 써볼 수 있는 초보자용 대시보드.
골드만삭스 Marquee API 계정 없이 쓸 수 있도록 가격 데이터는 Yahoo Finance 공개 차트 API에서 가져오고,
네트워크를 쓸 수 없으면 예시 데이터로 대체한다.

실행: python dashboard/app.py  →  http://localhost:5050
"""

import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, request, send_from_directory

import gs_quant.timeseries as ts
from gs_quant.timeseries import Window

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", 5050))
TRADING_DAYS = 252
RANGES = {"6mo", "1y", "2y", "5y"}

app = Flask(__name__, static_folder=None)


def fetch_prices(ticker: str, period: str) -> tuple[pd.Series, dict]:
    """Yahoo Finance 일별 종가를 가져온다."""
    resp = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        params={"range": period, "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    closes = result["indicators"]["adjclose"][0]["adjclose"] if "adjclose" in result["indicators"] \
        else result["indicators"]["quote"][0]["close"]
    index = pd.to_datetime(result["timestamp"], unit="s").normalize().date
    series = pd.Series(closes, index=pd.DatetimeIndex(index), name=ticker, dtype=float).dropna()
    series = series[~series.index.duplicated(keep="last")]
    meta = result["meta"]
    return series, {
        "name": meta.get("longName") or meta.get("shortName") or ticker,
        "currency": meta.get("currency", ""),
        "sample": False,
    }


def sample_prices(ticker: str, period: str) -> tuple[pd.Series, dict]:
    """네트워크 오류 시 쓰는 예시 데이터(기하 브라운 운동). 티커마다 같은 결과가 나오도록 시드를 고정한다."""
    days = {"6mo": 126, "1y": 252, "2y": 504, "5y": 1260}[period]
    rng = np.random.default_rng(abs(hash(ticker)) % (2 ** 32))
    rets = rng.normal(0.0003, 0.018, days)
    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    return pd.Series(100 * np.exp(np.cumsum(rets)), index=index, name=ticker), {
        "name": f"{ticker} (예시 데이터)",
        "currency": "",
        "sample": True,
    }


class TickerNotFound(Exception):
    pass


def load(ticker: str, period: str) -> tuple[pd.Series, dict]:
    try:
        return fetch_prices(ticker, period)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise TickerNotFound(ticker) from exc
        return sample_prices(ticker, period)
    except (requests.RequestException, KeyError, TypeError, IndexError):
        return sample_prices(ticker, period)


def clean(values) -> list:
    return [None if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else round(float(v), 4)
            for v in values]


def to_points(s: pd.Series) -> dict:
    return {"dates": [d.strftime("%Y-%m-%d") for d in s.index], "values": clean(s.values)}


def last(s: pd.Series):
    s = s.dropna()
    return None if s.empty else float(s.iloc[-1])


def analyze(prices: pd.Series, bench: pd.Series | None, window: int) -> dict:
    w = Window(window, window)
    daily = ts.returns(prices)
    vol = ts.volatility(prices, w)  # 연환산 %, gs_quant가 계산
    bands = ts.bollinger_bands(prices, w)
    rsi = ts.relative_strength_index(prices, 14)
    drawdown = prices / prices.cummax() - 1
    mdd = ts.max_drawdown(prices)

    total_return = prices.iloc[-1] / prices.iloc[0] - 1
    years = max(len(prices) / TRADING_DAYS, 1e-9)
    cagr = (1 + total_return) ** (1 / years) - 1
    ann_vol = float(daily.dropna().std() * math.sqrt(TRADING_DAYS))
    sharpe = float(daily.dropna().mean() * TRADING_DAYS / ann_vol) if ann_vol else None

    out = {
        "price": to_points(prices),
        "ma": to_points(ts.moving_average(prices, w)),
        "bb_upper": to_points(bands.iloc[:, 1] if bands.shape[1] > 1 else bands.iloc[:, 0]),
        "bb_lower": to_points(bands.iloc[:, 0]),
        "volatility": to_points(vol),
        "drawdown": to_points(drawdown * 100),
        "zscore": to_points(ts.zscores(prices, w)),
        "rsi": to_points(rsi if isinstance(rsi, pd.Series) else rsi.iloc[:, 0]),
        "stats": {
            "last_price": float(prices.iloc[-1]),
            "total_return": total_return * 100,
            "cagr": cagr * 100,
            "volatility": ann_vol * 100,
            "max_drawdown": (last(mdd) or 0) * 100,
            "sharpe": sharpe,
            "rsi": last(rsi if isinstance(rsi, pd.Series) else rsi.iloc[:, 0]),
            "zscore": last(ts.zscores(prices, w)),
        },
    }
    if bench is not None:
        aligned = pd.concat([prices, bench], axis=1, join="inner").dropna()
        if len(aligned) > window + 2:
            beta = ts.beta(aligned.iloc[:, 0], aligned.iloc[:, 1], w)
            out["beta"] = to_points(beta)
            out["stats"]["beta"] = last(beta)
    return out


@app.get("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.get("/api/analyze")
def api_analyze():
    tickers = [t.strip().upper() for t in request.args.get("tickers", "AAPL").split(",") if t.strip()][:5]
    period = request.args.get("range", "1y")
    period = period if period in RANGES else "1y"
    window = min(max(int(request.args.get("window", 22)), 5), 120)
    bench_ticker = request.args.get("benchmark", "^GSPC").strip().upper() or None

    try:
        bench = load(bench_ticker, period)[0] if bench_ticker else None
    except TickerNotFound:
        bench = None
    results, closes = {}, {}
    for t in tickers:
        try:
            prices, meta = load(t, period)
        except TickerNotFound:
            results[t] = {"meta": {"name": t, "currency": "", "sample": False},
                          "error": f"'{t}' 종목을 찾을 수 없습니다. 티커를 확인해 주세요. (한국 주식은 005930.KS처럼 입력)"}
            continue
        if len(prices) < window + 5:
            results[t] = {"meta": meta, "error": "데이터가 너무 적습니다. 기간을 늘리거나 이동 구간을 줄여 보세요."}
            continue
        results[t] = {"meta": meta, **analyze(prices, bench, window)}
        closes[t] = prices

    # 종목 간 상관관계: gs_quant correlation(전체 구간)의 마지막 값
    corr = {}
    names = list(closes)
    for i, a in enumerate(names):
        for b in names[i:]:
            if a == b:
                corr[f"{a}|{b}"] = 1.0
                continue
            pair = pd.concat([closes[a], closes[b]], axis=1, join="inner").dropna()
            value = last(ts.correlation(pair.iloc[:, 0], pair.iloc[:, 1])) if len(pair) > 10 else None
            corr[f"{a}|{b}"] = corr[f"{b}|{a}"] = value

    # 누적 수익률 비교(시작점 100 기준)
    compare = {t: to_points(p / p.iloc[0] * 100) for t, p in closes.items()}
    return jsonify({"tickers": tickers, "benchmark": bench_ticker, "window": window,
                    "results": results, "correlation": corr, "compare": compare})


if __name__ == "__main__":
    print(f"gs-quant-easy 대시보드: http://localhost:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
