"""
gs-quant-easy 대시보드

gs_quant.timeseries 분석 함수를 웹 화면에서 바로 써볼 수 있는 초보자용 대시보드.
골드만삭스 Marquee API 계정 없이 쓸 수 있도록 가격 데이터는 Yahoo Finance 공개 차트 API에서 가져오고,
네트워크를 쓸 수 없으면 예시 데이터로 대체한다.

실행: python dashboard/app.py  →  http://localhost:5050
"""

import datetime as dt
import math
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, request, send_from_directory

import gs_quant.timeseries as ts
from gs_quant.datetime import business_day_count, business_day_offset, day_count_fraction, is_business_day
from gs_quant.datetime.date import DayCountConvention
from gs_quant.timeseries import Window
from gs_quant.timeseries.backtesting import RebalFreq

import epidemic
import functions as fn
import instruments
import strategy

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", 5050))
TRADING_DAYS = 252
RANGES = {"6mo", "1y", "2y", "5y"}

app = Flask(__name__, static_folder=None)
app.json.sort_keys = False  # 모델·곡선 순서를 정의한 순서대로 유지
_cache: dict = {}
CACHE_TTL = 600  # 같은 종목·기간은 10분 동안 다시 받지 않는다


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
    key = (ticker, period)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    try:
        result = fetch_prices(ticker, period)
        _cache[key] = (time.time(), result)
        return result
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


# ------------------------------------------------------------------ 함수 실험실
def parse_date(value) -> dt.date:
    """'2026-01-31' 또는 오늘 기준 상대 일수('-90', '+30')"""
    value = str(value).strip()
    if value and value[0] in "+-" and value[1:].isdigit():
        return dt.date.today() + dt.timedelta(days=int(value))
    return dt.date.fromisoformat(value)


fn._date = parse_date


class Ctx:
    def __init__(self, x=None, y=None, xs=None):
        self.x, self.y, self.xs = x, y, xs or []
        self.names = []

    def weights(self, text):
        n = len(self.xs)
        try:
            w = [float(v) for v in str(text).replace(" ", "").split(",") if v]
        except ValueError:
            raise ValueError("비중은 0.6, 0.4처럼 숫자를 쉼표로 구분해 입력하세요.")
        if not w:
            return [1 / n] * n
        if len(w) != n:
            raise ValueError(f"비중 개수({len(w)})가 종목 개수({n})와 다릅니다.")
        return w


def series_out(s: pd.Series, name: str) -> dict:
    return {"name": name, **to_points(s.dropna())}


def normalize_result(res, label: str) -> dict:
    if isinstance(res, pd.DataFrame):
        return {"kind": "lines", "lines": [series_out(res.iloc[:, i], str(c)) for i, c in enumerate(res.columns)]}
    if isinstance(res, pd.Series):
        if not isinstance(res.index, pd.DatetimeIndex):
            res = res.copy()
            res.index = pd.to_datetime(res.index)
        return {"kind": "lines", "lines": [series_out(res, label)]}
    if isinstance(res, (list, tuple)) and res and isinstance(res[0], (dt.date, dt.datetime)):
        return {"kind": "text", "value": ", ".join(d.isoformat()[:10] for d in res) + f"  (총 {len(res)}일)"}
    if isinstance(res, (list, tuple)):
        out = []
        for i, r in enumerate(res):
            out += normalize_result(r, f"{label} {i + 1}")["lines"]
        return {"kind": "lines", "lines": out}
    if isinstance(res, (bool, np.bool_)):
        return {"kind": "text", "value": "예" if res else "아니오"}
    if isinstance(res, (dt.date, dt.datetime)):
        return {"kind": "text", "value": res.isoformat()[:10]}
    if isinstance(res, (int, float, np.floating, np.integer)):
        return {"kind": "scalar", "value": float(res)}
    raise ValueError("결과 형식을 표시할 수 없습니다.")


def get_series(ticker: str, period: str, src: str):
    try:
        prices, meta = load(ticker, period)
    except TickerNotFound:
        raise ValueError(f"'{ticker}' 종목을 찾을 수 없습니다. 티커를 확인해 주세요.")
    return (ts.returns(prices).dropna() if src == "returns" else prices), meta


@app.get("/api/functions")
def api_functions():
    return jsonify(fn.catalog())


@app.post("/api/run")
def api_run():
    body = request.get_json(force=True)
    spec = fn.REGISTRY.get(body.get("id"))
    if not spec:
        return jsonify({"error": "알 수 없는 함수입니다."}), 400
    period = body.get("range") if body.get("range") in RANGES else "1y"
    src = body.get("src") or spec["src"]
    given = body.get("params") or {}
    params = {p["name"]: given.get(p["name"], p["default"]) for p in spec["params"]}
    try:
        ctx, inputs = Ctx(), []
        if spec["input"] in ("x", "xy"):
            ctx.x, meta = get_series((body.get("x") or "AAPL").strip().upper(), period, src)
            inputs.append(series_out(ctx.x, meta["name"]))
        if spec["input"] == "xy":
            ctx.y, meta = get_series((body.get("y") or "^GSPC").strip().upper(), period, src)
            inputs.append(series_out(ctx.y, meta["name"]))
        if spec["input"] == "list":
            tickers = [t.strip().upper() for t in (body.get("tickers") or "").split(",") if t.strip()][:8]
            if len(tickers) < 2:
                raise ValueError("종목을 2개 이상 쉼표로 구분해 입력하세요.")
            for t in tickers:
                s, meta = get_series(t, period, "price")
                ctx.xs.append(s)
                ctx.names.append(meta["name"])
                inputs.append(series_out(s, meta["name"]))
            common = pd.concat(ctx.xs, axis=1, join="inner").dropna()
            ctx.xs = [common.iloc[:, i] for i in range(common.shape[1])]
        result = normalize_result(spec["run"](ctx, params), spec["title"])
    except Exception as exc:  # 원인을 화면에 보여준다
        return jsonify({"error": f"계산할 수 없습니다: {exc}"}), 400
    return jsonify({"result": result, "inputs": inputs, "src": src, "params": params})


def perf_stats(s: pd.Series) -> dict:
    r = ts.returns(s).dropna()
    vol = float(r.std() * math.sqrt(TRADING_DAYS))
    years = max(len(s) / TRADING_DAYS, 1e-9)
    total = float(s.iloc[-1] / s.iloc[0] - 1)
    return {"total_return": total * 100, "cagr": ((1 + total) ** (1 / years) - 1) * 100, "volatility": vol * 100,
            "max_drawdown": float(ts.max_drawdown(s).iloc[-1]) * 100,
            "sharpe": float(r.mean() * TRADING_DAYS / vol) if vol else None}


@app.post("/api/backtest")
def api_backtest():
    body = request.get_json(force=True)
    period = body.get("range") if body.get("range") in RANGES else "2y"
    tickers = [t.strip().upper() for t in (body.get("tickers") or "").split(",") if t.strip()][:8]
    try:
        if len(tickers) < 2:
            raise ValueError("종목을 2개 이상 입력하세요.")
        series, names = [], []
        for t in tickers:
            s, meta = get_series(t, period, "price")
            series.append(s)
            names.append(meta["name"])
        common = pd.concat(series, axis=1, join="inner").dropna()
        series = [common.iloc[:, i] for i in range(common.shape[1])]
        weights = Ctx(xs=series).weights(body.get("weights", ""))
        if abs(sum(weights) - 1) > 1e-6:
            raise ValueError(f"비중의 합이 1이 되어야 합니다(현재 {sum(weights):.2f}).")
        cost = float(body.get("cost", 0.1)) / 100
        labels = {"daily": "매일 리밸런싱", "weekly": "매주 리밸런싱", "monthly": "매월 리밸런싱"}
        # basket_series는 100에서 시작하므로 다른 곡선과 같이 1에서 시작하도록 맞춘다
        curves = {label: (lambda b: b / b.iloc[0])(ts.backtesting.basket_series(series, weights, [cost] * len(series), RebalFreq(freq)))
                  for freq, label in labels.items()}
        # 비교용: 처음 비중대로 사서 그대로 둔 경우
        curves["사서 그대로 두기"] = (common / common.iloc[0] * weights).sum(axis=1)
        for name, s in zip(names, series):
            curves[name] = s / s.iloc[0]
        chosen_freq = body.get("rebal_freq") if body.get("rebal_freq") in labels else "monthly"
        _, drift = ts.backtesting.backtest_basket(series, weights, [cost] * len(series), RebalFreq(chosen_freq))
        n = len(series)
        rets = common.pct_change()
        return jsonify({
            "chosen": labels.get(body.get("rebal_freq"), "매월 리밸런싱"),
            "names": names, "tickers": tickers, "weights": weights,
            "curves": {k: to_points(v) for k, v in curves.items()},
            "stats": {k: perf_stats(v) for k, v in curves.items()},
            "correlation": [[float(rets.iloc[:, i].corr(rets.iloc[:, j])) for j in range(n)] for i in range(n)],
            "weights_drift": [{"name": names[i], **to_points(drift.iloc[:, i] * 100)} for i in range(n)],
        })
    except Exception as exc:
        return jsonify({"error": f"백테스트할 수 없습니다: {exc}"}), 400


@app.post("/api/dates")
def api_dates():
    b = request.get_json(force=True)
    try:
        start, end = parse_date(b["start"]), parse_date(b["end"])
        conv = DayCountConvention(b.get("convention", "ACTUAL_365F"))
        rate = float(b.get("rate", 3.5)) / 100
        principal = float(b.get("principal", 10_000_000))
        frac = float(day_count_fraction(start, end, conv))
        return jsonify({
            "calendar_days": (end - start).days,
            "business_days": int(business_day_count(start, end)),
            "start_is_business": bool(is_business_day(start)),
            "end_is_business": bool(is_business_day(end)),
            "offset_date": business_day_offset(start, int(b.get("offset", 0)), roll="forward").isoformat(),
            "fraction": frac,
            "interest": principal * rate * frac,
        })
    except Exception as exc:
        return jsonify({"error": f"계산할 수 없습니다: {exc}"}), 400


# ------------------------------------------------------------------ 전략 백테스트
@app.get("/api/strategies")
def api_strategies():
    return jsonify({"strategies": strategy.STRATEGIES, "common": strategy.COMMON})


@app.post("/api/strategy")
def api_strategy():
    body = request.get_json(force=True)
    sid = body.get("id")
    if sid not in strategy.BY_ID:
        return jsonify({"error": "알 수 없는 전략입니다."}), 400
    period = body.get("range") if body.get("range") in RANGES else "2y"
    spec = strategy.BY_ID[sid]
    given = body.get("params") or {}
    params = {p["name"]: given.get(p["name"], p["default"]) for p in spec["params"] + strategy.COMMON}
    try:
        prices, meta = get_series((body.get("ticker") or "AAPL").strip().upper(), period, "price")
        r = strategy.run(prices, sid, params)
    except Exception as exc:
        return jsonify({"error": f"전략을 실행할 수 없습니다: {exc}"}), 400
    return jsonify({
        "name": meta["name"], "currency": meta["currency"], "capital": r["capital"], "summary": r["summary"],
        "perf": to_points(r["perf"]), "buy_hold": to_points(r["buy_hold"]), "price": to_points(r["price"]),
        "signal": to_points(r["signal"]) if r["signal"] is not None else None,
        "trades": r["trades"][-300:],
    })


# ------------------------------------------------------------------ 전염병 모델
@app.get("/api/epidemic/models")
def api_epidemic_models():
    return jsonify(epidemic.catalog())


@app.post("/api/epidemic")
def api_epidemic():
    body = request.get_json(force=True)
    model = body.get("model", "SIR")
    if model not in epidemic.MODELS:
        return jsonify({"error": "알 수 없는 모델입니다."}), 400
    given = body.get("params") or {}
    params = {p["name"]: given.get(p["name"], p["default"]) for p in epidemic.MODELS[model]["params"]}
    try:
        return jsonify(epidemic.simulate(model, params, bool(body.get("fit"))))
    except Exception as exc:
        return jsonify({"error": f"계산할 수 없습니다: {exc}"}), 400


# ------------------------------------------------------------------ 파생상품 살펴보기
@app.get("/api/instruments")
def api_instruments():
    return jsonify(instruments.catalog())


@app.post("/api/instrument")
def api_instrument():
    body = request.get_json(force=True)
    iid = body.get("id")
    if iid not in instruments.BY_ID:
        return jsonify({"error": "알 수 없는 상품입니다."}), 400
    given = body.get("params") or {}
    params = {p["name"]: given.get(p["name"], p["default"]) for p in instruments.BY_ID[iid]["params"]}
    try:
        return jsonify(instruments.build(iid, params))
    except Exception as exc:
        return jsonify({"error": f"상품을 만들 수 없습니다: {exc}"}), 400


if __name__ == "__main__":
    print(f"gs-quant-easy 대시보드: http://localhost:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
