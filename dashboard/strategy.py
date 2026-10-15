"""
규칙 기반 전략 백테스트: gs_quant.backtests.PredefinedAssetEngine

GS 계정 없이 동작하도록 시세를 직접 DataManager에 넣는다.
엔진은 매 영업일 23:00(장 마감 후 평가 시각)을 기준으로 트리거를 확인하고 주문을 체결한다.
"""

import datetime as dt

import pandas as pd

import gs_quant.timeseries as ts
from gs_quant.backtests.actions import AddTradeAction
from gs_quant.backtests.core import ValuationFixingType
from gs_quant.backtests.data_sources import DataManager, GenericDataSource
from gs_quant.backtests.predefined_asset_engine import PredefinedAssetEngine
from gs_quant.backtests.strategy import Strategy
from gs_quant.backtests.triggers import (
    DateTrigger, DateTriggerRequirements, MeanReversionTrigger, MeanReversionTriggerRequirements,
    MktTrigger, MktTriggerRequirements, TriggerDirection)
from gs_quant.data import DataFrequency
from gs_quant.instrument import EqStock

EOD = dt.time(23)

STRATEGIES = [
    {
        "id": "dca", "title": "적립식 매수", "trigger": "DateTrigger",
        "desc": "정해진 주기(매주·매월)의 첫 거래일마다 같은 수량을 꾸준히 삽니다. 가격이 쌀 때는 자연스럽게 더 싸게 사게 되어 평균 매입가가 낮아지는 효과(평균단가 효과)가 있습니다.",
        "read": "전략 자산 곡선이 '처음에 다 사기'보다 덜 출렁이는지, 최종 성과는 어떤지 비교해 보세요. 상승장에서는 처음에 다 사는 쪽이, 하락 후 반등장에서는 적립식이 유리한 경우가 많습니다.",
        "params": [
            {"name": "freq", "label": "매수 주기", "type": "enum", "default": "M", "options": [["W", "매주"], ["M", "매월"], ["Q", "매분기"]],
             "tip": "얼마나 자주 살지 정합니다. 매월이면 매달 첫 거래일에 삽니다."},
            {"name": "hold_days", "label": "보유 기간(일, 0=계속 보유)", "type": "int", "default": 0, "min": 0, "max": 1000,
             "tip": "산 뒤 며칠 뒤에 팔지 정합니다. 0이면 팔지 않고 계속 모아 갑니다(일반적인 적립식)."},
        ],
    },
    {
        "id": "dip", "title": "눌림목 매수", "trigger": "MktTrigger",
        "desc": "가격이 최근 이동평균보다 일정 % 이상 떨어졌을 때 삽니다. '좋은 종목이 잠깐 싸졌을 때 산다'는 아이디어입니다.",
        "read": "조건이 맞는 날마다 1회분씩 사고, 각 매수분은 정한 기간 뒤에 팝니다. 하락이 길게 이어지면 계속 사게 되어 손실이 커질 수 있다는 점(떨어지는 칼날)을 확인해 보세요.",
        "params": [
            {"name": "window", "label": "이동평균 기간(일)", "type": "int", "default": 20, "min": 5, "max": 250, "tip": "비교 기준이 될 이동평균 기간입니다. 20일은 약 1개월입니다."},
            {"name": "drop", "label": "하락 기준(%)", "type": "float", "default": 5, "min": 0.5, "max": 50, "step": 0.5,
             "tip": "가격이 이동평균보다 몇 % 이상 낮을 때 살지 정합니다. 5면 이동평균 대비 -5% 이하일 때 삽니다."},
            {"name": "hold_days", "label": "보유 기간(일)", "type": "int", "default": 20, "min": 1, "max": 500, "tip": "산 뒤 며칠(달력 기준) 뒤에 팔지 정합니다."},
        ],
    },
    {
        "id": "trend", "title": "추세 추종 (이동평균 돌파)", "trigger": "MktTrigger",
        "desc": "가격이 이동평균보다 위에 있으면(상승 추세) 삽니다. '오르는 말에 올라타라'는 추세 추종 전략의 가장 기본 형태입니다.",
        "read": "상승 추세가 길게 이어질수록 보유 수량이 늘어납니다. 추세가 없는 횡보장에서는 샀다 팔았다를 반복하며 손실이 쌓일 수 있습니다.",
        "params": [
            {"name": "window", "label": "이동평균 기간(일)", "type": "int", "default": 60, "min": 5, "max": 250, "tip": "추세를 판단할 이동평균 기간입니다. 길수록 큰 추세만 따라갑니다."},
            {"name": "hold_days", "label": "보유 기간(일)", "type": "int", "default": 10, "min": 1, "max": 500,
             "tip": "조건이 맞는 날마다 1회분씩 사고, 각각 이 기간 뒤에 팝니다. 추세가 계속되면 최대 '보유 기간 동안의 거래일 수'만큼 쌓입니다."},
        ],
    },
    {
        "id": "meanrev", "title": "평균 회귀", "trigger": "MeanReversionTrigger",
        "desc": "가격이 평균에서 크게 벗어나면 다시 평균으로 돌아온다고 보고 반대로 거래합니다. 평균보다 많이 싸면 사고(매수), 많이 비싸면 팝니다(공매도). 가격이 평균으로 돌아오면 정리합니다.",
        "read": "등락을 반복하는 종목에서 잘 맞고, 한 방향으로 길게 가는 종목에서는 손실이 납니다. 매매 장부에서 공매도(수량 -1) 거래의 손익도 확인해 보세요.",
        "params": [
            {"name": "z", "label": "진입 기준 (Z-점수)", "type": "float", "default": 1.5, "min": 0.5, "max": 4, "step": 0.1,
             "tip": "평균에서 표준편차 몇 배 이상 벗어나면 거래할지 정합니다. 클수록 드물게, 더 극단적인 상황에서만 거래합니다."},
            {"name": "window", "label": "평균·표준편차 기간(일)", "type": "int", "default": 20, "min": 5, "max": 250, "tip": "평균과 흔들림을 계산할 최근 거래일 수입니다."},
        ],
    },
]
BY_ID = {s["id"]: s for s in STRATEGIES}

COMMON = [
    {"name": "quantity", "label": "1회 거래 수량(주)", "type": "int", "default": 1, "min": 1, "max": 100000,
     "tip": "신호가 나올 때마다 몇 주씩 사고팔지 정합니다."},
    {"name": "capital", "label": "시작 현금", "type": "float", "default": 0, "min": 0, "max": 1e13,
     "tip": "백테스트를 시작할 때 가진 현금입니다. 0이면 첫날 가격의 20배(20주를 살 수 있는 금액)로 자동 설정합니다. 현금이 모자라도 빌려서 산 것으로 계산하니, 현금이 마이너스가 될 수 있습니다."},
]


def _eod(d) -> dt.datetime:
    return dt.datetime.combine(d, EOD)


def _schedule(index: list, freq: str) -> list:
    s = pd.Series(index, index=pd.to_datetime(index))
    rule = {"W": "W-MON", "M": "MS", "Q": "QS"}[freq]
    return [d for d in s.groupby(pd.Grouper(freq=rule)).first().dropna()]


def run(prices: pd.Series, sid: str, p: dict) -> dict:
    spec = BY_ID[sid]
    # 엔진이 영업일마다 가격을 찾으므로 휴장일은 직전 종가로 채운다
    px = prices.copy()
    px.index = pd.to_datetime(px.index)
    px = px.reindex(pd.bdate_range(px.index[0], px.index[-1])).ffill()
    days = [d.date() for d in px.index]
    daily = pd.Series(px.values, index=days)
    # 체결은 평가 시각(23:00)에 일어나므로, 주말을 포함한 매일 23:00 가격을 만든다
    all_days = pd.date_range(px.index[0], px.index[-1] + pd.Timedelta(days=7))
    realtime = pd.Series(px.reindex(all_days).ffill().values, index=[_eod(d.date()) for d in all_days])

    asset = EqStock(name="STOCK", quantity=int(p["quantity"]))
    dm = DataManager()
    dm.add_data_source(daily, DataFrequency.DAILY, asset, ValuationFixingType.PRICE)
    dm.add_data_source(realtime, DataFrequency.REAL_TIME, asset, ValuationFixingType.PRICE)

    hold = int(p.get("hold_days") or 0)
    duration = dt.timedelta(days=hold) if hold > 0 else None
    action = AddTradeAction(asset, duration, name="Trade")

    if sid == "dca":
        trigger = DateTrigger(DateTriggerRequirements([_eod(d) for d in _schedule(days, p["freq"])]), action)
        signal = None
    elif sid in ("dip", "trend"):
        ma = ts.moving_average(daily, int(p["window"]))
        gap = (pd.Series(daily.values, index=pd.to_datetime(days)) / pd.Series(ma.values, index=pd.to_datetime(ma.index)) - 1).fillna(0)
        signal = gap
        gap_rt = pd.Series(gap.reindex(all_days).ffill().fillna(0).values, index=[_eod(d.date()) for d in all_days])
        if sid == "dip":
            req = MktTriggerRequirements(GenericDataSource(gap_rt), -float(p["drop"]) / 100, TriggerDirection.BELOW)
        else:
            req = MktTriggerRequirements(GenericDataSource(gap_rt), 0.0, TriggerDirection.ABOVE)
        trigger = MktTrigger(req, action)
    elif sid == "meanrev":
        req = MeanReversionTriggerRequirements(GenericDataSource(realtime), float(p["z"]), int(p["window"]), int(p["window"]))
        trigger = MeanReversionTrigger(req, action)
        signal = ts.zscores(pd.Series(daily.values, index=pd.to_datetime(days)), int(p["window"]))
    else:
        raise ValueError("알 수 없는 전략입니다.")

    capital = float(p.get("capital") or 0) or float(daily.iloc[0]) * 20
    engine = PredefinedAssetEngine(dm)
    bt = engine.run_backtest(Strategy(None, trigger), start=days[0], end=days[-1], frequency="B", initial_value=capital)

    perf = bt.performance
    perf.index = pd.to_datetime(perf.index)
    buy_hold = pd.Series(daily.values, index=pd.to_datetime(days)) / daily.iloc[0] * capital

    # 백테스트 종료일 이후로 예약된 매도 주문은 체결되지 않으므로 장부 계산에서 뺀다
    bt.orders = [o for o in bt.orders if o.executed_price is not None]
    ledger = bt.trade_ledger().reset_index(drop=True)
    trades = []
    for _, row in ledger.iterrows():
        o, cv, pnl = _num(row["Open Value"]), _num(row["Close Value"]), _num(row["Trade PnL"])
        # 장부에는 수량 부호가 없으므로 손익 = (청산가 - 진입가) × 방향 에서 방향을 되찾는다
        short = pnl is not None and cv is not None and cv != o and pnl * (cv - o) < 0
        trades.append({
            "side": "공매도" if short else "매수",
            "open": str(row["Open"])[:10], "close": None if row["Close"] is None or pd.isna(row["Close"]) else str(row["Close"])[:10],
            "open_value": _num(row["Open Value"]), "close_value": _num(row["Close Value"]),
            "status": "청산" if row["Status"] == "closed" else "보유 중", "pnl": _num(row["Trade PnL"]),
        })
    closed = [t["pnl"] for t in trades if t["pnl"] is not None]
    wins = [x for x in closed if x > 0]

    def stats(s):
        r = ts.returns(s).dropna()
        return {"final": float(s.iloc[-1]), "total_return": float(s.iloc[-1] / s.iloc[0] - 1) * 100,
                "max_drawdown": float(ts.max_drawdown(s).iloc[-1]) * 100,
                "volatility": float(r.std() * (252 ** 0.5)) * 100}

    return {
        "strategy": {k: spec[k] for k in ("id", "title")},
        "capital": capital,
        "perf": perf, "buy_hold": buy_hold, "price": pd.Series(daily.values, index=pd.to_datetime(days)),
        "signal": signal,
        "trades": trades,
        "summary": {
            "strategy": stats(perf), "buy_hold": stats(buy_hold),
            "n_trades": len(trades), "n_closed": len(closed), "n_open": len(trades) - len(closed),
            "win_rate": (len(wins) / len(closed) * 100) if closed else None,
            "avg_pnl": (sum(closed) / len(closed)) if closed else None,
            "realized_pnl": sum(closed),
        },
    }


def _num(v):
    try:
        return None if v is None or pd.isna(v) else float(v)
    except (TypeError, ValueError):
        return None
