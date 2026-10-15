"""
파생상품 살펴보기: gs_quant.instrument

상품 객체를 만들고 구성 요소를 보여준다. 가격·위험 계산은 GS 계정이 필요하므로 하지 않고,
대신 만기 시점의 손익 구조(payoff)를 단순화해 직접 계산해 보여준다(프리미엄·할인 미반영).
"""

import json

import numpy as np

import gs_quant.instrument as I

BUY_SELL = {"name": "buy_sell", "label": "매수/매도", "type": "enum", "default": "Buy", "options": [["Buy", "매수 (Buy)"], ["Sell", "매도 (Sell)"]],
            "tip": "상품을 사는 쪽인지 파는 쪽인지 정합니다. 옵션을 사면 권리를 갖고, 팔면 의무를 집니다."}
PAY_REC = {"name": "pay_or_receive", "label": "고정금리 지급/수취", "type": "enum", "default": "Pay",
           "options": [["Pay", "고정 지급 (Pay)"], ["Receive", "고정 수취 (Receive)"]],
           "tip": "고정금리를 내는 쪽(Pay, 금리가 오르면 이익)인지 받는 쪽(Receive, 금리가 내리면 이익)인지 정합니다."}
CCY = {"name": "notional_currency", "label": "통화", "type": "enum", "default": "USD",
       "options": [["USD", "미국 달러"], ["EUR", "유로"], ["GBP", "영국 파운드"], ["JPY", "일본 엔"], ["KRW", "한국 원"]],
       "tip": "거래의 기준 통화입니다. 통화마다 기준 금리(달러는 SOFR 등)가 다릅니다."}
NOTIONAL = {"name": "notional_amount", "label": "명목 금액", "type": "float", "default": 10_000_000, "min": 0, "max": 1e12,
            "tip": "이자나 손익을 계산하는 기준 금액입니다. 스왑에서는 실제로 주고받지 않고 계산에만 씁니다."}
TENOR = {"name": "termination_date", "label": "만기", "type": "text", "default": "5y",
         "tip": "거래가 끝나는 시점입니다. 5y(5년), 6m(6개월)처럼 기간으로 쓰거나 2030-12-31처럼 날짜로 씁니다."}
OPT_TYPE = {"name": "option_type", "label": "옵션 종류", "type": "enum", "default": "Call", "options": [["Call", "콜 (살 권리)"], ["Put", "풋 (팔 권리)"]],
            "tip": "콜옵션은 정해진 가격에 살 권리로 가격이 오를 때 이익, 풋옵션은 팔 권리로 가격이 내릴 때 이익입니다."}
EXPIRY = {"name": "expiration_date", "label": "만기", "type": "text", "default": "6m",
          "tip": "옵션을 행사할 수 있는 마지막 날입니다. 3m, 1y처럼 기간이나 날짜로 씁니다."}

INSTRUMENTS = [
    {"id": "IRSwap", "cat": "금리", "title": "금리 스왑 (IRS)",
     "desc": "정해진 기간 동안 고정금리와 변동금리 이자를 서로 바꾸는 계약입니다. 원금은 주고받지 않고 이자 차이만 정산합니다. 은행과 기업이 금리 변동 위험을 관리할 때 가장 많이 씁니다.",
     "example": "변동금리 대출을 받은 회사가 금리 상승이 걱정되면 '고정 지급 스왑'을 맺어 사실상 고정금리 대출로 바꿀 수 있습니다.",
     "params": [PAY_REC, TENOR, CCY, NOTIONAL,
                {"name": "fixed_rate", "pct": True, "label": "고정금리(%)", "type": "float", "default": 4.0, "min": -5, "max": 30, "step": 0.05,
                 "tip": "계약 기간 내내 고정된 이자율입니다."}],
     "build": lambda p: I.IRSwap(p["pay_or_receive"], p["termination_date"], p["notional_currency"],
                                 notional_amount=p["notional_amount"], fixed_rate=p["fixed_rate"] / 100),
     "payoff": "swap"},
    {"id": "IRSwaption", "cat": "금리", "title": "스왑션",
     "desc": "정해진 날에 미리 정한 고정금리로 금리 스왑을 시작할 수 있는 '권리'(옵션)입니다. 나중에 금리가 유리하게 움직였을 때만 스왑을 시작하면 됩니다.",
     "example": "1년 뒤 대출을 받을 예정인 회사가, 그때 금리가 너무 오를까 봐 '고정 지급 스왑션'을 미리 사 둘 수 있습니다.",
     "params": [PAY_REC, {**TENOR, "default": "10y", "tip": "옵션을 행사하면 시작되는 스왑의 만기입니다."}, CCY, NOTIONAL,
                {**EXPIRY, "default": "1y", "tip": "스왑을 시작할지 결정해야 하는 날입니다."},
                {"name": "strike", "pct": True, "label": "행사 금리(%)", "type": "float", "default": 4.0, "min": -5, "max": 30, "step": 0.05, "tip": "스왑을 시작하면 적용될 고정금리입니다."},
                BUY_SELL],
     "build": lambda p: I.IRSwaption(p["pay_or_receive"], p["termination_date"], p["notional_currency"], notional_amount=p["notional_amount"],
                                     expiration_date=p["expiration_date"], strike=p["strike"] / 100, buy_sell=p["buy_sell"]),
     "payoff": "swaption"},
    {"id": "IRCap", "cat": "금리", "title": "금리 캡",
     "desc": "변동금리가 정한 상한(캡)을 넘으면 넘은 만큼을 보상받는 계약입니다. '금리 상승 보험'이라고 생각하면 됩니다.",
     "example": "변동금리 대출자가 금리가 5%를 넘을 때를 대비해 5% 캡을 사면, 실제 부담 금리가 5%를 넘지 않게 됩니다.",
     "params": [TENOR, CCY, NOTIONAL, {"name": "cap_rate", "pct": True, "label": "상한 금리(%)", "type": "float", "default": 5.0, "min": 0, "max": 30, "step": 0.05,
                                      "tip": "이 금리를 넘는 부분을 보상받습니다."}],
     "build": lambda p: I.IRCap(p["termination_date"], p["notional_currency"], notional_amount=p["notional_amount"], cap_rate=p["cap_rate"] / 100),
     "payoff": "cap"},
    {"id": "IRFloor", "cat": "금리", "title": "금리 플로어",
     "desc": "변동금리가 정한 하한(플로어) 아래로 떨어지면 모자란 만큼을 보상받는 계약입니다. 금리 하락에 대비하는 보험입니다.",
     "example": "변동금리 예금·채권을 가진 투자자가 금리가 2% 아래로 내려가도 최소 2% 수익을 지키려고 2% 플로어를 삽니다.",
     "params": [TENOR, CCY, NOTIONAL, {"name": "floor_rate", "pct": True, "label": "하한 금리(%)", "type": "float", "default": 2.0, "min": -5, "max": 30, "step": 0.05,
                                      "tip": "금리가 이 아래로 내려간 만큼을 보상받습니다."}],
     "build": lambda p: I.IRFloor(p["termination_date"], p["notional_currency"], notional_amount=p["notional_amount"], floor_rate=p["floor_rate"] / 100),
     "payoff": "floor"},
    {"id": "InflationSwap", "cat": "금리", "title": "물가 연동 스왑",
     "desc": "고정된 이자율과 실제 물가상승률(인플레이션)을 서로 바꾸는 계약입니다. 물가가 예상보다 많이 오르면 고정을 지급하는 쪽이 이익입니다.",
     "example": "연금 기금처럼 물가에 따라 지급액이 늘어나는 곳이 물가 상승 위험을 줄이려고 씁니다.",
     "params": [PAY_REC, TENOR, {**CCY, "default": "EUR"}, NOTIONAL,
                {"name": "fixed_rate", "pct": True, "label": "고정 물가율(%)", "type": "float", "default": 2.5, "min": -5, "max": 30, "step": 0.05, "tip": "계약에서 정한 고정 물가상승률입니다."}],
     "build": lambda p: I.InflationSwap(p["pay_or_receive"], p["termination_date"], p["notional_currency"], notional_amount=p["notional_amount"],
                                        fixed_rate=p["fixed_rate"] / 100),
     "payoff": "swap"},
    {"id": "FXForward", "cat": "외환", "title": "외환 선도 (선물환)",
     "desc": "미래의 정해진 날에 정해진 환율로 통화를 사고팔기로 지금 약속하는 계약입니다.",
     "example": "6개월 뒤 달러로 대금을 받을 수출 기업이, 그때 환율이 떨어질까 봐 지금 환율로 '달러 매도 선물환'을 맺어 둡니다.",
     "params": [{"name": "pair", "label": "통화쌍", "type": "enum", "default": "USDKRW", "options": [["USDKRW", "달러/원"], ["EURUSD", "유로/달러"], ["USDJPY", "달러/엔"], ["EURKRW", "유로/원"]],
                 "tip": "앞 통화 1단위가 뒤 통화로 얼마인지를 나타냅니다. USDKRW 1,400은 1달러 = 1,400원입니다."},
                BUY_SELL, {"name": "settlement_date", "label": "결제일", "type": "text", "default": "6m", "tip": "실제로 통화를 주고받는 날입니다."},
                {"name": "forward_rate", "label": "약정 환율", "type": "float", "default": 1400, "min": 0, "max": 1e6, "step": 1, "tip": "미래에 거래할 환율입니다."},
                {"name": "notional_amount", "label": "금액 (앞 통화)", "type": "float", "default": 1_000_000, "min": 0, "max": 1e12, "tip": "거래할 앞 통화(USDKRW면 달러) 금액입니다."}],
     "build": lambda p: I.FXForward(pair=p["pair"], buy_sell=p["buy_sell"], settlement_date=p["settlement_date"], forward_rate=p["forward_rate"],
                                    notional_amount=p["notional_amount"]),
     "payoff": "forward_fx"},
    {"id": "FXOption", "cat": "외환", "title": "외환 옵션",
     "desc": "미래에 정해진 환율로 통화를 사거나 팔 수 있는 권리입니다. 선물환과 달리 불리하면 행사하지 않아도 됩니다(대신 프리미엄을 냅니다).",
     "example": "수출 기업이 환율 하락은 막고 상승 이익은 누리고 싶을 때 '달러 풋옵션'을 삽니다.",
     "params": [{"name": "pair", "label": "통화쌍", "type": "enum", "default": "USDKRW", "options": [["USDKRW", "달러/원"], ["EURUSD", "유로/달러"], ["USDJPY", "달러/엔"]],
                 "tip": "앞 통화 1단위의 뒤 통화 가격입니다."},
                BUY_SELL, OPT_TYPE, EXPIRY,
                {"name": "strike_price", "label": "행사 환율", "type": "float", "default": 1400, "min": 0, "max": 1e6, "step": 1, "tip": "옵션을 행사하면 적용되는 환율입니다."},
                {"name": "notional_amount", "label": "금액 (앞 통화)", "type": "float", "default": 1_000_000, "min": 0, "max": 1e12, "tip": "옵션 대상 금액입니다."}],
     "build": lambda p: I.FXOption(pair=p["pair"], buy_sell=p["buy_sell"], option_type=p["option_type"], expiration_date=p["expiration_date"],
                                   strike_price=p["strike_price"], notional_amount=p["notional_amount"]),
     "payoff": "option_fx"},
    {"id": "FXBinary", "cat": "외환", "title": "외환 디지털(바이너리) 옵션",
     "desc": "만기에 환율이 행사가격을 넘으면(또는 밑돌면) 정해진 금액을 한 번에 받고, 아니면 아무것도 받지 않는 옵션입니다.",
     "example": "'만기에 달러/원이 1,450원 이상이면 100만 원'처럼 결과가 둘 중 하나로 정해집니다.",
     "params": [{"name": "pair", "label": "통화쌍", "type": "enum", "default": "USDKRW", "options": [["USDKRW", "달러/원"], ["EURUSD", "유로/달러"], ["USDJPY", "달러/엔"]], "tip": "기준이 되는 환율입니다."},
                BUY_SELL, OPT_TYPE, EXPIRY,
                {"name": "strike_price", "label": "행사 환율", "type": "float", "default": 1450, "min": 0, "max": 1e6, "step": 1, "tip": "넘었는지(밑돌았는지) 판단하는 기준 환율입니다."},
                {"name": "notional_amount", "label": "지급 금액", "type": "float", "default": 1_000_000, "min": 0, "max": 1e12, "tip": "조건을 만족하면 받는 금액입니다."}],
     "build": lambda p: I.FXBinary(pair=p["pair"], buy_sell=p["buy_sell"], option_type=p["option_type"], expiration_date=p["expiration_date"],
                                   strike_price=p["strike_price"], notional_amount=p["notional_amount"]),
     "payoff": "binary"},
    {"id": "EqOption", "cat": "주식", "title": "주식(지수) 옵션",
     "desc": "주식이나 지수를 정해진 가격(행사가격)에 사거나(콜) 팔(풋) 수 있는 권리입니다.",
     "example": "삼성전자를 가진 투자자가 주가 급락에 대비해 풋옵션을 사 두면, 주가가 행사가격 아래로 떨어진 만큼 보상받습니다.",
     "params": [{"name": "underlier", "label": "기초자산", "type": "text", "default": ".SPX", "tip": "옵션의 대상이 되는 주식이나 지수입니다. .SPX는 S&P 500 지수입니다."},
                BUY_SELL, OPT_TYPE, EXPIRY,
                {"name": "strike_price", "label": "행사가격", "type": "float", "default": 6000, "min": 0, "max": 1e9, "step": 1, "tip": "옵션을 행사하면 사고팔게 되는 가격입니다."},
                {"name": "number_of_options", "label": "옵션 수량", "type": "float", "default": 10, "min": 0, "max": 1e9, "tip": "옵션 계약 수입니다(여기서는 1계약 = 1단위로 계산)."},
                {"name": "option_style", "label": "행사 방식", "type": "enum", "default": "European", "options": [["European", "유럽식 (만기일에만)"], ["American", "미국식 (만기 전 언제나)"]],
                 "tip": "유럽식은 만기일에만, 미국식은 만기 전 아무 때나 행사할 수 있습니다."}],
     "build": lambda p: I.EqOption(p["underlier"], p["expiration_date"], p["strike_price"], p["option_type"], p["option_style"],
                                   number_of_options=p["number_of_options"], buy_sell=p["buy_sell"]),
     "payoff": "option_eq"},
    {"id": "EqForward", "cat": "주식", "title": "주식 선도",
     "desc": "미래의 정해진 날에 주식을 정해진 가격에 사고팔기로 약속하는 계약입니다. 옵션과 달리 반드시 거래해야 합니다.",
     "example": "3개월 뒤 주식을 살 계획인 투자자가 지금 가격으로 미리 약속해 가격 상승 위험을 없앱니다.",
     "params": [{"name": "underlier", "label": "기초자산", "type": "text", "default": ".SPX", "tip": "거래할 주식이나 지수입니다."},
                {"name": "expiration_date", "label": "만기", "type": "text", "default": "3m", "tip": "실제로 사고파는 날입니다."},
                {"name": "forward_price", "label": "약정 가격", "type": "float", "default": 6000, "min": 0, "max": 1e9, "step": 1, "tip": "미래에 거래할 가격입니다."},
                {"name": "number_of_shares", "label": "수량", "type": "float", "default": 10, "min": 0, "max": 1e9, "tip": "거래할 주식(지수 단위) 수입니다."}],
     "build": lambda p: I.EqForward(underlier=p["underlier"], expiration_date=p["expiration_date"], forward_price=p["forward_price"],
                                    number_of_shares=p["number_of_shares"]),
     "payoff": "forward_eq"},
    {"id": "EqBinary", "cat": "주식", "title": "주식 디지털(바이너리) 옵션",
     "desc": "만기에 주가가 행사가격을 넘으면(또는 밑돌면) 정해진 금액을 받고, 아니면 아무것도 받지 않습니다.",
     "example": "'1년 뒤 S&P 500이 6,000 이상이면 1억 원'처럼 결과가 0 또는 정해진 금액입니다.",
     "params": [{"name": "underlier", "label": "기초자산", "type": "text", "default": ".SPX", "tip": "기준이 되는 주식이나 지수입니다."},
                BUY_SELL, OPT_TYPE, EXPIRY,
                {"name": "strike_price", "label": "행사가격", "type": "float", "default": 6000, "min": 0, "max": 1e9, "step": 1, "tip": "넘었는지 판단하는 기준 가격입니다."},
                {"name": "notional_amount", "label": "지급 금액", "type": "float", "default": 100_000_000, "min": 0, "max": 1e13, "tip": "조건을 만족하면 받는 금액입니다."}],
     "build": lambda p: I.EqBinary(underlier=p["underlier"], buy_sell=p["buy_sell"], option_type=p["option_type"], expiration_date=p["expiration_date"],
                                   strike_price=p["strike_price"], notional_amount=p["notional_amount"]),
     "payoff": "binary_eq"},
    {"id": "EqVarianceSwap", "cat": "주식", "title": "분산 스왑 (변동성 거래)",
     "desc": "주가의 방향이 아니라 '얼마나 크게 출렁였는지'(실현 변동성)에 돈을 거는 계약입니다. 실제 변동성이 약정 변동성보다 크면 매수자가 이익입니다.",
     "example": "시장이 곧 크게 흔들릴 것 같지만 오를지 내릴지는 모를 때 변동성 자체를 삽니다.",
     "params": [{"name": "underlier", "label": "기초자산", "type": "text", "default": ".SPX", "tip": "변동성을 측정할 주식이나 지수입니다."},
                {"name": "expiration_date", "label": "만기", "type": "text", "default": "1y", "tip": "변동성 측정이 끝나는 날입니다."},
                {"name": "strike_price", "label": "약정 변동성(%)", "type": "float", "default": 20, "min": 0, "max": 200, "step": 0.5,
                 "tip": "기준이 되는 연 변동성입니다. 실제 변동성이 이보다 크면 매수자가 이익입니다."},
                {"name": "vega", "label": "변동성 1%p당 손익(베가 금액)", "type": "float", "default": 100_000, "min": 0, "max": 1e12,
                 "tip": "실제 변동성이 약정보다 1%p 클 때 대략 얼마를 벌지 정하는 금액입니다."}],
     "build": lambda p: I.EqVarianceSwap(underlier=p["underlier"], expiration_date=p["expiration_date"], strike_price=p["strike_price"]),
     "payoff": "variance"},
    {"id": "CommodSwap", "cat": "원자재", "title": "원자재 스왑",
     "desc": "원유 같은 원자재의 변동 가격과 고정 가격을 바꾸는 계약입니다. 실제 원자재는 주고받지 않고 가격 차이만 정산합니다.",
     "example": "항공사가 기름값 상승에 대비해 '고정 가격 지급' 스왑을 맺으면 사실상 연료를 고정 가격에 사는 효과가 납니다.",
     "params": [{"name": "commodity", "label": "원자재", "type": "enum", "default": "Brent", "options": [["Brent", "브렌트유"], ["WTI", "WTI 원유"], ["NG", "천연가스"]], "tip": "가격 기준이 되는 원자재입니다."},
                {"name": "quantity", "label": "월 수량", "type": "float", "default": 1000, "min": 0, "max": 1e12, "tip": "매달 정산 기준이 되는 수량(배럴 등)입니다."},
                {"name": "start", "label": "시작", "type": "text", "default": "1m", "tip": "계약이 시작되는 시점입니다."},
                {"name": "number_of_periods", "label": "기간 수(월)", "type": "int", "default": 12, "min": 1, "max": 360, "tip": "몇 달 동안 정산할지 정합니다."},
                {"name": "fixed_price", "label": "고정 가격", "type": "float", "default": 75, "min": 0, "max": 1e6, "step": 0.5, "tip": "계약에서 정한 원자재 가격입니다."}],
     "build": lambda p: I.CommodSwap(commodity=p["commodity"], quantity=p["quantity"], start=p["start"], number_of_periods=int(p["number_of_periods"]),
                                     fixed_price=p["fixed_price"]),
     "payoff": "commod"},
    {"id": "Bond", "cat": "채권", "title": "채권",
     "desc": "정부나 기업에 돈을 빌려주고 정해진 이자(쿠폰)와 만기에 원금을 돌려받는 증권입니다. 금리가 오르면 기존 채권 가격은 내려갑니다.",
     "example": "미국 국채(US Treasury)는 가장 안전한 자산 중 하나로, 주식이 급락할 때 피난처 역할을 하곤 합니다.",
     "params": [BUY_SELL, {"name": "identifier", "label": "채권 코드 (ISIN)", "type": "text", "default": "US912810TM08", "tip": "채권마다 붙은 국제 고유 번호(ISIN)입니다."},
                {"name": "size", "label": "액면 금액", "type": "float", "default": 1_000_000, "min": 0, "max": 1e12, "tip": "만기에 돌려받는 원금(액면가) 기준 금액입니다."}],
     "build": lambda p: I.Bond(buy_sell=p["buy_sell"], identifier=p["identifier"], size=p["size"]),
     "payoff": None},
    {"id": "CDIndex", "cat": "신용", "title": "신용부도스왑 지수 (CDX·iTraxx)",
     "desc": "여러 기업이 부도날 위험을 묶어서 사고파는 '부도 보험' 지수입니다. 보험을 산 쪽(Buy)은 정기적으로 보험료를 내고, 기업이 부도나면 손실을 보상받습니다.",
     "example": "회사채를 많이 가진 투자자가 경기 침체로 부도가 늘어날 것에 대비해 CDX 지수 보호를 삽니다.",
     "params": [{**BUY_SELL, "tip": "Buy는 부도 보험을 사는 쪽(신용 위험 회피), Sell은 보험을 파는 쪽(보험료 수익, 부도 시 손실)입니다."},
                {"name": "index_family", "label": "지수", "type": "enum", "default": "CDX.NA.IG",
                 "options": [["CDX.NA.IG", "CDX 북미 투자등급"], ["CDX.NA.HY", "CDX 북미 하이일드"], ["iTraxx Europe", "iTraxx 유럽"]],
                 "tip": "어떤 기업 묶음의 부도 위험인지 정합니다. IG는 우량 기업, HY는 신용도가 낮은 기업입니다."},
                TENOR, NOTIONAL],
     "build": lambda p: I.CDIndex(buy_sell=p["buy_sell"], index_family=p["index_family"], termination_date=p["termination_date"],
                                  notional_amount=p["notional_amount"]),
     "payoff": None},
]
BY_ID = {x["id"]: x for x in INSTRUMENTS}


def _years(tenor: str) -> float:
    t = str(tenor).strip().lower()
    try:
        n = float(t[:-1])
        return {"y": n, "m": n / 12, "w": n / 52, "d": n / 365}[t[-1]]
    except (ValueError, KeyError):
        return 1.0


def payoff(spec: dict, p: dict):
    """만기 시점 손익(단순화). x축 값 목록, 손익 목록, 축 이름을 돌려준다."""
    kind = spec["payoff"]
    sign = -1 if p.get("buy_sell") == "Sell" else 1
    if kind in ("swap", "swaption", "cap", "floor"):
        years = _years(p["termination_date"])
        strike = {"swap": p.get("fixed_rate"), "swaption": p.get("strike"), "cap": p.get("cap_rate"), "floor": p.get("floor_rate")}[kind]
        x = np.round(np.linspace(max(strike - 4, -1), strike + 4, 81), 3)
        diff = (x - strike) / 100 * p["notional_amount"] * years
        if kind == "swap":
            y = diff * (1 if p["pay_or_receive"] == "Pay" else -1)
        elif kind == "swaption":
            y = sign * (np.maximum(diff, 0) if p["pay_or_receive"] == "Pay" else np.maximum(-diff, 0))
        elif kind == "cap":
            y = np.maximum(diff, 0)
        else:
            y = np.maximum(-diff, 0)
        label = "만기까지 평균 변동금리(%)" if spec["id"] != "InflationSwap" else "만기까지 평균 물가상승률(%)"
        return x, y, label, f"전체 기간({years:g}년) 누적 이자 차이로 단순화했습니다. 할인·지급 일정·프리미엄은 반영하지 않았습니다."
    if kind in ("option_fx", "option_eq", "binary", "binary_eq", "forward_fx", "forward_eq"):
        k = p.get("strike_price") or p.get("forward_rate") or p.get("forward_price")
        x = np.round(np.linspace(k * 0.7, k * 1.3, 121), 4)
        if kind in ("option_fx", "option_eq"):
            qty = p.get("number_of_options") or p.get("notional_amount")
            intrinsic = np.maximum(x - k, 0) if p["option_type"] == "Call" else np.maximum(k - x, 0)
            y = sign * intrinsic * qty
        elif kind in ("binary", "binary_eq"):
            hit = (x >= k) if p["option_type"] == "Call" else (x <= k)
            y = sign * hit * p["notional_amount"]
        else:
            qty = p.get("number_of_shares") or p.get("notional_amount")
            y = (x - k) * qty * (sign if kind == "forward_fx" else 1)
        label = "만기 시점 환율" if "fx" in kind or kind == "binary" else "만기 시점 기초자산 가격"
        note = "옵션 프리미엄(구입 비용)은 GS 가격 계산이 필요해 빼고, 만기 시점의 내재가치만 그렸습니다." if "option" in kind or "binary" in kind else "만기 시점 손익입니다."
        return x, y, label, note
    if kind == "variance":
        k = p["strike_price"]
        x = np.round(np.linspace(max(k - 15, 1), k + 25, 81), 2)
        variance_notional = p["vega"] / (2 * k)
        y = variance_notional * (x ** 2 - k ** 2)
        return x, y, "만기까지 실현 변동성(%)", "분산 스왑은 '변동성의 제곱'으로 정산해서, 변동성이 클수록 이익이 가속됩니다(볼록성)."
    if kind == "commod":
        k = p["fixed_price"]
        x = np.round(np.linspace(k * 0.6, k * 1.4, 81), 2)
        y = (x - k) * p["quantity"] * int(p["number_of_periods"])
        return x, y, "평균 원자재 가격", "고정 가격을 지급하는 쪽 기준, 전체 기간 누적 정산액입니다."
    return None


def build(iid: str, p: dict) -> dict:
    spec = BY_ID[iid]
    inst = spec["build"](p)
    fields = json.loads(inst.to_json())
    out = {"title": spec["title"], "class": type(inst).__name__, "fields": fields}
    pay = payoff(spec, p)
    if pay:
        x, y, label, note = pay
        out["payoff"] = {"x": [float(v) for v in x], "y": [float(v) for v in y], "x_label": label, "note": note}
    return out


def catalog():
    return [{k: v for k, v in x.items() if k not in ("build",)} for x in INSTRUMENTS]
