"""
함수 실험실: GS 계정 없이 쓸 수 있는 gs_quant 함수 목록과 초보자용 설명.

각 항목:
  id       gs_quant 함수 이름(코드 예시에 쓰임)
  cat      분류
  title    한국어 이름
  desc     쉬운 설명
  read     결과 읽는 법
  use      언제 쓰나
  input    x(종목 1개) | xy(종목 2개) | list(여러 종목) | none(입력 없음)
  src      x에 넣을 기본 데이터: price(가격) | returns(일별 수익률)
  params   [{name, label, type(int|float|enum|date|bool), default, options, tip}]
  code     파이썬 코드 예시 템플릿({파라미터} 치환)
  run      실제 계산 함수 (ctx, params) -> 결과
"""

import datetime as dt

import pandas as pd

import gs_quant.timeseries as ts
from gs_quant.datetime.date import DayCountConvention, PaymentFrequency
from gs_quant.timeseries import Window
from gs_quant.timeseries.algebra import FilterOperator
from gs_quant.timeseries.analysis import LagMode, SignDirection, ThresholdType
from gs_quant.timeseries.backtesting import RebalFreq
from gs_quant.timeseries.datetime import AggregateFunction, AggregatePeriod
from gs_quant.timeseries.helper import Interpolate, Returns, SeriesType
from gs_quant.timeseries.statistics import Direction, MeanType
from gs_quant.timeseries.technicals import Frequency, SeasonalModel


# ---------------------------------------------------------------- 공통 파라미터
def W(default=22, tip=None):
    return {"name": "w", "label": "이동 구간(일)", "type": "int", "default": default, "min": 2, "max": 500,
            "tip": tip or "최근 며칠을 묶어서 계산할지 정합니다. 22일은 약 1개월, 63일은 약 3개월, 252일은 약 1년입니다."}


BETA = {"name": "beta", "label": "감쇠 계수(beta)", "type": "float", "default": 0.94, "min": 0, "max": 0.999, "step": 0.01,
        "tip": "과거 데이터를 얼마나 오래 기억할지 정합니다(0~1). 1에 가까울수록 과거를 오래 기억해 선이 부드럽고, 0에 가까울수록 최근 값에 민감합니다. 리스크 관리에서는 0.94가 흔히 쓰입니다."}

RET_TYPE = {"name": "returns_type", "label": "수익률 계산 방식", "type": "enum", "default": "simple",
            "options": [["simple", "단순 수익률"], ["logarithmic", "로그 수익률"], ["absolute", "가격 차이"]],
            "tip": "단순 수익률은 (오늘/어제 - 1), 로그 수익률은 ln(오늘/어제)로 계산합니다. 가격 차이는 오늘 - 어제입니다. 보통은 단순 수익률이면 충분합니다."}

INTERP = {"name": "method", "label": "날짜 맞추기 방식", "type": "enum", "default": "intersect",
          "options": [["intersect", "두 종목 모두 있는 날만"], ["step", "빈 날은 직전 값으로 채움"], ["nan", "빈 날은 비워 둠"],
                      ["zero", "빈 날은 0으로"], ["time", "시간 비례 보간"]],
          "tip": "한국과 미국처럼 휴장일이 다른 두 종목을 계산할 때 날짜가 안 맞는 날을 어떻게 처리할지 정합니다."}

RISK_FREE = {"name": "rate", "label": "무위험 금리(연, %)", "type": "float", "default": 3.0, "min": -5, "max": 30, "step": 0.1,
             "tip": "예금이나 국채처럼 위험 없이 받을 수 있는 연 이자율입니다. 이걸 넘는 수익만 '진짜 초과 수익'으로 봅니다. 한국 기준금리나 미국 국채 금리를 넣으면 됩니다."}


def _w(p, key="w"):
    return Window(int(p[key]), int(p[key]))


def _date(s):
    return dt.date.fromisoformat(s)


def _flags(s):
    """일별 수익률이 0보다 크면 1, 아니면 0"""
    return (ts.returns(s).fillna(0) > 0).astype(int)


CATS = ["수익률·가격 변환", "위험·변동성", "시장 비교·관계", "추세·기술적 지표", "기초 통계",
        "데이터 정리", "산술·논리 연산", "날짜·달력", "포트폴리오"]

F = []


def add(**kw):
    kw.setdefault("params", [])
    kw.setdefault("src", "price")
    F.append(kw)


# ================================================================ 수익률·가격 변환
add(id="returns", cat=CATS[0], title="수익률", input="x",
    desc="가격이 일정 기간 동안 몇 % 변했는지 계산합니다. 투자 분석의 가장 기본 재료입니다.",
    read="0.02는 2% 상승, -0.01은 1% 하락입니다.",
    use="가격 대신 '얼마나 벌었나'로 비교하고 싶을 때. 대부분의 위험 지표가 수익률에서 출발합니다.",
    params=[{"name": "obs", "label": "비교 간격(일)", "type": "int", "default": 1, "min": 1, "max": 252,
             "tip": "며칠 전 가격과 비교할지 정합니다. 1이면 일간, 5면 주간, 22면 월간 수익률입니다."},
            {**RET_TYPE, "name": "type"}],
    code="ts.returns(x, {obs}, Returns.{type})",
    run=lambda c, p: ts.returns(c.x, int(p["obs"]), Returns(p["type"])))

add(id="prices", cat=CATS[0], title="수익률 → 가격", input="x", src="returns",
    desc="수익률을 차례로 쌓아서 다시 가격(누적 자산) 곡선으로 바꿉니다. returns의 반대 계산입니다.",
    read="시작값이 1이면, 1.25는 처음 투자금이 1.25배(25% 수익)가 됐다는 뜻입니다.",
    use="전략 수익률을 '돈이 어떻게 불어났나' 그래프로 보고 싶을 때.",
    params=[{"name": "initial", "label": "시작값", "type": "float", "default": 1, "min": 0.0001, "max": 1e9,
             "tip": "누적 곡선의 출발점입니다. 100으로 두면 지수처럼 읽기 편합니다."},
            {**RET_TYPE, "name": "type"}],
    code="ts.prices(r, {initial}, Returns.{type})",
    run=lambda c, p: ts.prices(c.x, float(p["initial"]), Returns(p["type"])))

add(id="index", cat=CATS[0], title="지수화 (시작점 맞추기)", input="x",
    desc="첫날 값을 기준(예: 1 또는 100)으로 맞춰서 나머지를 비율로 표시합니다.",
    read="100에서 시작해 130이면 30% 오른 것입니다.",
    use="가격 단위가 다른 종목(원화 vs 달러)을 한 그래프에서 비교할 때.",
    params=[{"name": "initial", "label": "시작값", "type": "float", "default": 100, "min": 0.0001, "max": 1e9,
             "tip": "첫날 값을 몇으로 맞출지 정합니다. 보통 1 또는 100을 씁니다."}],
    code="ts.index(x, {initial})",
    run=lambda c, p: ts.index(c.x, float(p["initial"])))

add(id="change", cat=CATS[0], title="누적 변화량", input="x",
    desc="첫날 값에서 얼마나 변했는지를 '차이(뺄셈)'로 보여줍니다.",
    read="값이 15000이면 첫날보다 가격이 15,000(원/달러) 올랐다는 뜻입니다.",
    use="비율이 아니라 금액·포인트 변화가 중요할 때(예: 금리 0.5%p 변화).",
    code="ts.change(x)",
    run=lambda c, p: ts.change(c.x))

add(id="annualize", cat=CATS[0], title="연환산", input="x", src="returns",
    desc="일별처럼 짧은 기간의 값을 1년 기준으로 늘려 줍니다. 데이터 간격(일·주·월)을 자동으로 알아내서 그에 맞는 배수를 곱합니다.",
    read="일별 수익률의 흔들림을 1년 단위로 키운 값입니다.",
    use="일간·월간 데이터처럼 간격이 다른 지표를 같은 '연 단위'로 비교할 때.",
    code="ts.annualize(r)",
    run=lambda c, p: ts.annualize(c.x))

add(id="excess_returns", cat=CATS[0], title="초과 수익 곡선", input="x",
    desc="같은 기간 예금(무위험 금리)에 넣었을 때보다 얼마나 더 벌었는지를 누적 곡선으로 보여줍니다.",
    read="곡선이 오르면 예금보다 나은 성과, 내리면 예금만 못한 성과입니다.",
    use="'그냥 예금했으면 어땠을까'와 비교하고 싶을 때. 샤프 지수의 재료입니다.",
    params=[RISK_FREE],
    code="ts.excess_returns(x, {rate} / 100)",
    run=lambda c, p: ts.excess_returns(c.x, float(p["rate"]) / 100))

add(id="geometrically_aggregate", cat=CATS[0], title="복리 누적 수익률", input="x", src="returns",
    desc="매일의 수익률을 복리로 곱해 쌓아서 '지금까지 총 몇 %'인지 계산합니다.",
    read="0.35면 기간 시작 이후 누적 35% 수익입니다.",
    use="수익률을 단순히 더하지 않고 실제 복리 효과까지 반영한 누적 성과가 필요할 때.",
    code="ts.geometrically_aggregate(r)",
    run=lambda c, p: ts.geometrically_aggregate(c.x))

# ================================================================ 위험·변동성
add(id="volatility", cat=CATS[1], title="변동성", input="x",
    desc="가격이 얼마나 크게 출렁이는지를 연 % 단위로 나타냅니다. 가장 대표적인 위험 지표입니다.",
    read="20이면 1년에 대략 ±20% 범위의 움직임이 흔하다는 뜻입니다. 대형 우량주는 보통 15~30, 성장주·코인은 그 이상입니다.",
    use="종목이 얼마나 위험한지, 지금이 평소보다 불안한 시기인지 볼 때.",
    params=[W(), RET_TYPE],
    code="ts.volatility(x, Window({w}, {w}), Returns.{returns_type})",
    run=lambda c, p: ts.volatility(c.x, _w(p), Returns(p["returns_type"])))

add(id="vol_swap_volatility", cat=CATS[1], title="변동성 스왑식 변동성", input="x",
    desc="파생상품 '변동성 스왑' 가격을 정할 때 쓰는 방식(로그 수익률, 평균 0 가정)으로 변동성을 계산합니다.",
    read="일반 변동성과 비슷하게 읽으면 됩니다. 계산 방식이 조금 다를 뿐입니다.",
    use="변동성 자체를 거래하는 상품을 공부할 때 일반 변동성과 비교해 보기 좋습니다.",
    params=[{**W(), "name": "n_days"}],
    code="ts.vol_swap_volatility(x, {n_days})",
    run=lambda c, p: ts.vol_swap_volatility(c.x, int(p["n_days"])))

add(id="exponential_volatility", cat=CATS[1], title="지수가중 변동성", input="x",
    desc="최근 움직임에 더 큰 가중치를 줘서 계산한 변동성입니다. 시장이 갑자기 불안해지면 일반 변동성보다 빨리 반응합니다.",
    read="연 % 단위입니다. 갑자기 튀어 오르면 최근 시장이 크게 흔들렸다는 신호입니다.",
    use="위험이 커지는 순간을 빨리 감지하고 싶을 때(리스크 관리, 포지션 축소 판단).",
    params=[BETA],
    code="ts.exponential_volatility(x, {beta})",
    run=lambda c, p: ts.exponential_volatility(c.x, float(p["beta"])))

add(id="exponential_spread_volatility", cat=CATS[1], title="지수가중 스프레드 변동성", input="x",
    desc="비율(%)이 아니라 '차이(포인트)'의 흔들림을 지수가중으로 계산합니다.",
    read="값의 단위는 원래 데이터 단위(원, 포인트, %p)입니다.",
    use="금리·스프레드처럼 0 근처이거나 음수가 될 수 있는 데이터의 위험을 볼 때.",
    params=[BETA],
    code="ts.exponential_spread_volatility(x, {beta})",
    run=lambda c, p: ts.exponential_spread_volatility(c.x, float(p["beta"])))

add(id="std", cat=CATS[1], title="표준편차", input="x", src="returns",
    desc="값들이 평균에서 평균적으로 얼마나 떨어져 있는지 나타냅니다. 변동성의 원재료입니다.",
    read="일별 수익률의 표준편차가 0.02면 하루에 ±2% 정도 움직이는 게 보통이라는 뜻입니다.",
    use="연환산 전의 '하루 단위 흔들림'을 직접 보고 싶을 때.",
    params=[W()],
    code="ts.std(r, Window({w}, {w}))",
    run=lambda c, p: ts.std(c.x, _w(p)))

add(id="exponential_std", cat=CATS[1], title="지수가중 표준편차", input="x", src="returns",
    desc="최근 값에 더 큰 가중치를 준 표준편차입니다.",
    read="일반 표준편차보다 최근 변화에 빨리 반응합니다.",
    use="흔들림이 변하는 속도를 빨리 잡고 싶을 때.",
    params=[BETA],
    code="ts.exponential_std(r, {beta})",
    run=lambda c, p: ts.exponential_std(c.x, float(p["beta"])))

add(id="var", cat=CATS[1], title="분산", input="x", src="returns",
    desc="표준편차를 제곱한 값입니다. 수학적으로 다루기 쉬워서 포트폴리오 이론에 많이 쓰입니다.",
    read="값 자체보다 클수록 흔들림이 크다는 정도로 읽으면 됩니다.",
    use="포트폴리오 위험을 직접 계산하거나 공부할 때.",
    params=[W()],
    code="ts.var(r, Window({w}, {w}))",
    run=lambda c, p: ts.var(c.x, _w(p)))

add(id="max_drawdown", cat=CATS[1], title="최대 낙폭 (MDD)", input="x",
    desc="최고점에서 최저점까지 가장 크게 떨어졌던 비율입니다. '최악의 타이밍에 샀다면 얼마나 잃었을까'입니다.",
    read="-0.3이면 고점 대비 30% 하락을 겪은 적이 있다는 뜻입니다. 0에 가까울수록 좋습니다.",
    use="내가 견딜 수 있는 손실 수준인지 확인할 때. 전략 비교에서 가장 많이 보는 지표 중 하나입니다.",
    params=[{**W(252, "최근 며칠 안에서 최대 낙폭을 찾을지 정합니다. 252일이면 '최근 1년 중 최악의 하락'입니다."), "name": "w"}],
    code="ts.max_drawdown(x, Window({w}, 0))",
    run=lambda c, p: ts.max_drawdown(c.x, Window(int(p["w"]), 0)))

add(id="range_", cat=CATS[1], title="구간 고저폭", input="x",
    desc="최근 일정 기간의 최고값과 최저값의 차이입니다.",
    read="값이 클수록 그 기간에 가격이 넓게 움직였다는 뜻입니다.",
    use="박스권(일정 범위 안에서 오르내림)인지, 크게 움직이는 장인지 볼 때.",
    params=[W()],
    code="ts.range_(x, Window({w}, {w}))",
    run=lambda c, p: ts.range_(c.x, _w(p)))

add(id="sharpe_ratio", cat=CATS[1], title="샤프 지수 (이동)", input="x",
    desc="위험(변동성) 1단위당 예금 대비 초과 수익을 얼마나 냈는지 보여주는 '가성비' 지표입니다. 최근 구간 기준으로 계속 계산합니다.",
    read="1 이상이면 좋은 편, 2 이상이면 매우 좋음, 0 아래면 위험만 지고 예금보다 못한 성과입니다.",
    use="수익률이 높아도 위험이 컸는지, 안정적으로 벌었는지 구분할 때.",
    params=[RISK_FREE, W(252)],
    code="ts.econometrics.get_ratio_pure(ts.excess_returns(x, {rate} / 100), Window({w}, {w}))",
    run=lambda c, p: ts.econometrics.get_ratio_pure(ts.excess_returns(c.x, float(p["rate"]) / 100), _w(p)))

# ================================================================ 시장 비교·관계
add(id="beta", cat=CATS[2], title="베타", input="xy",
    desc="기준(Y, 보통 시장 지수)이 1% 움직일 때 종목(X)이 평균 몇 % 움직이는지입니다.",
    read="1.5면 시장보다 1.5배 크게, 0.5면 절반만, 음수면 반대로 움직입니다.",
    use="시장이 빠질 때 내 종목이 얼마나 같이 빠질지 가늠할 때.",
    params=[W(63)],
    code="ts.beta(x, y, Window({w}, {w}))",
    run=lambda c, p: ts.beta(c.x, c.y, _w(p)))

add(id="correlation", cat=CATS[2], title="상관관계", input="xy",
    desc="두 종목이 얼마나 같은 방향으로 움직이는지 -1~1 사이 숫자로 나타냅니다.",
    read="1에 가까우면 같이 오르내림, 0이면 서로 무관, -1이면 정반대로 움직입니다.",
    use="분산투자할 때 서로 덜 닮은 종목을 고르기 위해.",
    params=[W(63), {"name": "type_", "label": "입력 데이터 종류", "type": "enum", "default": "prices",
                    "options": [["prices", "가격"], ["returns", "수익률"]],
                    "tip": "넣은 데이터가 가격인지 수익률인지 알려줍니다. 가격을 넣으면 함수가 알아서 수익률로 바꿔 계산합니다."}],
    code="ts.correlation(x, y, Window({w}, {w}), SeriesType('{type_}'))",
    run=lambda c, p: ts.correlation(c.x, c.y, _w(p), SeriesType(p["type_"])))

add(id="corr_swap_correlation", cat=CATS[2], title="상관관계 스왑식 상관관계", input="xy",
    desc="파생상품 '상관관계 스왑'에서 쓰는 방식(로그 수익률, 평균 0 가정)으로 계산한 상관관계입니다.",
    read="일반 상관관계처럼 -1~1로 읽습니다.",
    use="일반 상관관계와 비교하며 파생상품 계산 방식을 공부할 때.",
    params=[{**W(63), "name": "n_days"}],
    code="ts.corr_swap_correlation(x, y, {n_days})",
    run=lambda c, p: ts.corr_swap_correlation(c.x, c.y, int(p["n_days"])))

add(id="cov", cat=CATS[2], title="공분산", input="xy", src="returns",
    desc="두 종목이 함께 움직이는 정도를 나타내는 원재료 숫자입니다. 상관관계는 이 값을 각자의 흔들림으로 나눈 것입니다.",
    read="양수면 같이, 음수면 반대로 움직이는 경향입니다. 크기는 단위에 따라 달라 직접 비교는 어렵습니다.",
    use="포트폴리오 위험 계산(분산·공분산 행렬)을 공부할 때.",
    params=[W(63)],
    code="ts.cov(rx, ry, Window({w}, {w}))",
    run=lambda c, p: ts.cov(c.x, c.y, _w(p)))

add(id="compare", cat=CATS[2], title="크기 비교", input="xy",
    desc="날마다 X와 Y 중 어느 쪽이 큰지 비교합니다.",
    read="1은 X가 큼, -1은 Y가 큼, 0은 같음입니다.",
    use="두 지표의 우위가 언제 바뀌는지 볼 때(예: 지수화한 두 종목의 성과 역전).",
    params=[{**INTERP, "default": "step"}],
    code="ts.compare(ts.index(x), ts.index(y), Interpolate.{method})",
    run=lambda c, p: ts.compare(ts.index(c.x), ts.index(c.y), Interpolate(p["method"])))

# ================================================================ 추세·기술적 지표
add(id="moving_average", cat=CATS[3], title="이동평균", input="x",
    desc="최근 N일 가격의 평균을 이어 그린 선입니다. 들쭉날쭉한 가격을 부드럽게 만들어 큰 흐름(추세)을 보여줍니다.",
    read="가격이 이동평균 위에 있으면 상승 추세, 아래에 있으면 하락 추세로 보는 경우가 많습니다.",
    use="추세 판단. 20일·60일·120일선이 자주 쓰입니다.",
    params=[W(20)],
    code="ts.moving_average(x, Window({w}, {w}))",
    run=lambda c, p: ts.moving_average(c.x, _w(p)))

add(id="smoothed_moving_average", cat=CATS[3], title="평활 이동평균", input="x",
    desc="이전 평균값을 이어받아 천천히 갱신하는 이동평균입니다. 일반 이동평균보다 더 부드럽습니다.",
    read="일반 이동평균처럼 추세선으로 읽습니다. 반응은 조금 느립니다.",
    use="잔물결을 더 많이 걸러 내고 큰 추세만 보고 싶을 때. RSI 계산에도 쓰입니다.",
    params=[W(20)],
    code="ts.smoothed_moving_average(x, Window({w}, {w}))",
    run=lambda c, p: ts.smoothed_moving_average(c.x, _w(p)))

add(id="exponential_moving_average", cat=CATS[3], title="지수이동평균 (EMA)", input="x",
    desc="최근 가격에 더 큰 가중치를 준 이동평균입니다. 일반 이동평균보다 추세 변화에 빨리 반응합니다.",
    read="가격이 EMA를 위로 뚫으면 상승 전환, 아래로 뚫으면 하락 전환 신호로 보기도 합니다.",
    use="추세 전환을 빨리 잡고 싶을 때.",
    params=[{**BETA, "default": 0.9}],
    code="ts.exponential_moving_average(x, {beta})",
    run=lambda c, p: ts.exponential_moving_average(c.x, float(p["beta"])))

add(id="macd", cat=CATS[3], title="MACD", input="x",
    desc="짧은 기간 지수이동평균에서 긴 기간 지수이동평균을 뺀 값입니다. 추세의 방향과 힘을 함께 보여줍니다.",
    read="0보다 크면 단기 흐름이 장기보다 강한 상승 국면, 0 아래면 하락 국면입니다. 0선을 넘나드는 시점이 추세 전환 신호로 쓰입니다.",
    use="추세 추종 매매의 대표 지표. 보통 12일·26일 조합을 씁니다.",
    params=[{"name": "m", "label": "짧은 기간(일)", "type": "int", "default": 12, "min": 2, "max": 200, "tip": "빠르게 반응하는 단기 이동평균의 기간입니다."},
            {"name": "n", "label": "긴 기간(일)", "type": "int", "default": 26, "min": 3, "max": 400, "tip": "느리게 반응하는 장기 이동평균의 기간입니다. 짧은 기간보다 커야 합니다."},
            {"name": "s", "label": "신호선 기간(일)", "type": "int", "default": 1, "min": 1, "max": 50, "tip": "결과를 한 번 더 부드럽게 할 기간입니다. 1이면 그대로, 9가 흔히 쓰이는 '신호선'입니다."}],
    code="ts.macd(x, {m}, {n}, {s})",
    run=lambda c, p: ts.macd(c.x, int(p["m"]), int(p["n"]), int(p["s"])))

add(id="bollinger_bands", cat=CATS[3], title="볼린저 밴드", input="x",
    desc="이동평균 위아래로 '평소 흔들림(표준편차) × k'만큼 띠를 그립니다.",
    read="가격은 대부분 띠 안에서 움직입니다. 띠를 벗어나면 평소보다 강한 움직임, 띠가 좁아지면 큰 움직임이 다가온다는 신호로 봅니다.",
    use="과열·과매도 판단, 변동성 축소 후 돌파 매매.",
    params=[W(20), {"name": "k", "label": "밴드 폭(k)", "type": "float", "default": 2, "min": 0.5, "max": 5, "step": 0.5,
                    "tip": "표준편차의 몇 배만큼 띠를 넓힐지 정합니다. 2면 가격의 약 95%가 띠 안에 들어옵니다."}],
    code="ts.bollinger_bands(x, Window({w}, {w}), {k})",
    run=lambda c, p: ts.bollinger_bands(c.x, _w(p), float(p["k"])).set_axis(["하단 밴드", "상단 밴드"], axis=1))

add(id="relative_strength_index", cat=CATS[3], title="RSI (상대강도지수)", input="x",
    desc="최근 N일 동안 오른 힘과 내린 힘을 비교해 0~100으로 나타냅니다.",
    read="70 이상은 과열(많이 올랐음), 30 이하는 침체(많이 떨어졌음)로 봅니다. 과열이 더 이어지는 경우도 많아 단독 신호로는 부족합니다.",
    use="단기 과열·과매도 확인.",
    params=[W(14, "RSI 계산 기간입니다. 14일이 표준입니다.")],
    code="ts.relative_strength_index(x, {w})",
    run=lambda c, p: ts.relative_strength_index(c.x, int(p["w"])))

add(id="trend", cat=CATS[3], title="추세 추출", input="x",
    desc="데이터를 '추세 + 계절성 + 잡음'으로 나눈 뒤 추세만 남깁니다.",
    read="매끈한 선이 데이터의 근본적인 방향입니다.",
    use="계절 영향이 있는 데이터(소매 판매, 전력 수요 등)의 진짜 방향을 볼 때. 주가는 계절성이 약해 이동평균과 비슷하게 나옵니다.",
    params=[{"name": "method", "label": "분해 방식", "type": "enum", "default": "additive",
             "options": [["additive", "덧셈형"], ["multiplicative", "곱셈형"]],
             "tip": "덧셈형은 계절 영향이 늘 같은 크기(예: +100), 곱셈형은 같은 비율(예: +5%)이라고 가정합니다."},
            {"name": "freq", "label": "계절 주기", "type": "enum", "default": "week",
             "options": [["week", "주"], ["month", "월"], ["quarter", "분기"], ["year", "연"]],
             "tip": "반복되는 패턴의 주기입니다. 데이터가 주기의 2배 이상 길어야 합니다(연 주기면 2년 이상)."}],
    code="ts.trend(x, SeasonalModel.{method}, Frequency.{freq})",
    run=lambda c, p: ts.trend(c.x, SeasonalModel(p["method"]), Frequency(p["freq"])))

add(id="seasonally_adjusted", cat=CATS[3], title="계절 조정", input="x",
    desc="데이터에서 반복되는 계절 패턴을 제거합니다. 추세 추출과 달리 잡음은 남겨 둡니다.",
    read="계절 효과를 뺀 '실제' 변화입니다.",
    use="경제지표 뉴스의 '계절조정 기준'이 바로 이것입니다.",
    params=[{"name": "method", "label": "분해 방식", "type": "enum", "default": "additive",
             "options": [["additive", "덧셈형"], ["multiplicative", "곱셈형"]],
             "tip": "덧셈형은 계절 영향이 늘 같은 크기, 곱셈형은 같은 비율이라고 가정합니다."},
            {"name": "freq", "label": "계절 주기", "type": "enum", "default": "week",
             "options": [["week", "주"], ["month", "월"], ["quarter", "분기"], ["year", "연"]],
             "tip": "반복되는 패턴의 주기입니다. 데이터가 주기의 2배 이상 길어야 합니다."}],
    code="ts.seasonally_adjusted(x, SeasonalModel.{method}, Frequency.{freq})",
    run=lambda c, p: ts.seasonally_adjusted(c.x, SeasonalModel(p["method"]), Frequency(p["freq"])))

# ================================================================ 기초 통계
add(id="mean", cat=CATS[4], title="평균", input="x",
    desc="최근 N일 값의 평균입니다. '제곱평균'을 고르면 값의 크기(부호 무시)를 강조한 평균이 됩니다.",
    read="산술평균은 이동평균과 같습니다.",
    use="수익률의 평균, 값의 평균 수준을 볼 때.",
    params=[W(), {"name": "mean_type", "label": "평균 종류", "type": "enum", "default": "arithmetic",
                  "options": [["arithmetic", "산술평균"], ["quadratic", "제곱평균(RMS)"]],
                  "tip": "산술평균은 일반 평균, 제곱평균은 값을 제곱해 평균 낸 뒤 제곱근을 씌운 값으로 크기를 강조합니다."}],
    code="ts.mean(x, Window({w}, {w}), MeanType.{mean_type})",
    run=lambda c, p: ts.mean(c.x, _w(p), MeanType(p["mean_type"])))

add(id="median", cat=CATS[4], title="중앙값", input="x",
    desc="최근 N일 값을 크기순으로 세웠을 때 한가운데 값입니다. 평균과 달리 극단값에 덜 흔들립니다.",
    read="평균과 차이가 크면 한쪽으로 튀는 값이 있었다는 뜻입니다.",
    use="급등락 하루 때문에 평균이 왜곡될 때.",
    params=[W()],
    code="ts.median(x, Window({w}, {w}))",
    run=lambda c, p: ts.median(c.x, _w(p)))

add(id="mode", cat=CATS[4], title="최빈값", input="x",
    desc="최근 N일 동안 가장 자주 나온 값입니다.",
    read="가격처럼 값이 매번 다른 데이터에서는 큰 의미가 없고, 등급·횟수 같은 데이터에 유용합니다.",
    use="자주 반복되는 수준(지지선 후보)을 찾을 때.",
    params=[W()],
    code="ts.mode(x, Window({w}, {w}))",
    run=lambda c, p: ts.mode(c.x.round(0), _w(p)))

add(id="min_", cat=CATS[4], title="구간 최저값", input="x",
    desc="최근 N일 중 가장 낮은 값입니다.",
    read="가격이 이 선 근처면 최근 저점 부근입니다.",
    use="지지선, 손절 기준, 신저가 확인.",
    params=[W()],
    code="ts.min_(x, Window({w}, {w}))",
    run=lambda c, p: ts.min_(c.x, _w(p)))

add(id="max_", cat=CATS[4], title="구간 최고값", input="x",
    desc="최근 N일 중 가장 높은 값입니다.",
    read="가격이 이 선을 넘으면 신고가 돌파입니다.",
    use="저항선, 돌파 매매(터틀 트레이딩), 신고가 확인.",
    params=[W()],
    code="ts.max_(x, Window({w}, {w}))",
    run=lambda c, p: ts.max_(c.x, _w(p)))

add(id="sum_", cat=CATS[4], title="구간 합계", input="x", src="returns",
    desc="최근 N일 값을 모두 더합니다.",
    read="수익률에 쓰면 최근 N일 수익률의 단순 합계(근사 누적 수익률)입니다.",
    use="거래량 합계, 최근 한 달 수익률 합계 등.",
    params=[W()],
    code="ts.sum_(r, Window({w}, {w}))",
    run=lambda c, p: ts.sum_(c.x, _w(p)))

add(id="product", cat=CATS[4], title="구간 곱", input="x",
    desc="최근 N일 값을 모두 곱합니다.",
    read="(1 + 수익률)을 넣으면 최근 N일 복리 누적 배수가 됩니다.",
    use="복리 계산. 여기서는 1 + 일별 수익률을 넣어 계산합니다.",
    params=[W()],
    code="ts.product(1 + ts.returns(x), Window({w}, {w}))",
    run=lambda c, p: ts.product(1 + ts.returns(c.x).fillna(0), _w(p)))

add(id="percentile", cat=CATS[4], title="백분위 값", input="x",
    desc="값들을 작은 순서로 세웠을 때 하위 n% 위치의 값입니다.",
    read="n=5이고 결과가 -0.03이면, 하루 수익률이 -3%보다 나쁜 날은 전체의 5%뿐이라는 뜻입니다(역사적 VaR의 원리).",
    use="최악의 날 손실 규모 추정(VaR), 기준선 정하기.",
    src="returns",
    params=[{"name": "n", "label": "백분위(n, %)", "type": "float", "default": 5, "min": 0, "max": 100,
             "tip": "몇 % 위치의 값을 볼지 정합니다. 50은 중앙값, 5는 하위 5%(나쁜 쪽 꼬리)입니다."},
            W(252)],
    code="ts.percentile(r, {n}, Window({w}, {w}))",
    run=lambda c, p: ts.percentile(c.x, float(p["n"]), _w(p)))

add(id="percentiles", cat=CATS[4], title="백분위 순위", input="x",
    desc="오늘 값이 최근 N일 중에서 상위 몇 % 위치인지 0~100으로 나타냅니다.",
    read="90이면 최근 기간 중 상위 10% 높은 수준, 10이면 하위 10% 낮은 수준입니다.",
    use="지금 가격·변동성이 역사적으로 비싼지 싼지 가늠할 때.",
    params=[W(252)],
    code="ts.percentiles(x, w=Window({w}, {w}))",
    run=lambda c, p: ts.percentiles(c.x, w=_w(p)))

add(id="zscores", cat=CATS[4], title="Z-점수", input="x",
    desc="현재 값이 평균에서 '평소 흔들림(표준편차)의 몇 배'만큼 떨어져 있는지입니다.",
    read="0은 평균, +2는 이례적으로 높음, -2는 이례적으로 낮음입니다.",
    use="평균회귀 전략, 이상 징후 탐지.",
    params=[W()],
    code="ts.zscores(x, Window({w}, {w}))",
    run=lambda c, p: ts.zscores(c.x, _w(p)))

add(id="winsorize", cat=CATS[4], title="극단값 자르기 (윈저화)", input="x", src="returns",
    desc="평균에서 너무 멀리 튄 값을 '평균 ± 표준편차 × 한도'로 잘라 냅니다.",
    read="결과에서 위아래 극단이 평평하게 잘려 있습니다.",
    use="한두 번의 폭등·폭락이 분석 전체를 왜곡하지 않게 할 때.",
    params=[{"name": "limit", "label": "한도(표준편차 배수)", "type": "float", "default": 2.5, "min": 0.5, "max": 10, "step": 0.5,
             "tip": "평균에서 표준편차 몇 배를 넘으면 자를지 정합니다. 작을수록 많이 잘립니다."}, W(252)],
    code="ts.winsorize(r, {limit}, Window({w}, {w}))",
    run=lambda c, p: ts.winsorize(c.x, float(p["limit"]), _w(p)))

add(id="count", cat=CATS[4], title="데이터 개수", input="x",
    desc="처음부터 지금까지 쌓인 데이터 개수를 셉니다.",
    read="마지막 값이 전체 거래일 수입니다.",
    use="데이터가 빠짐없이 있는지 확인할 때.",
    code="ts.count(x)",
    run=lambda c, p: ts.count(c.x))

# ================================================================ 데이터 정리
add(id="diff", cat=CATS[5], title="차분", input="x",
    desc="오늘 값에서 N일 전 값을 뺍니다.",
    read="양수면 N일 전보다 올랐고 음수면 내렸습니다(금액 기준).",
    use="금리·스프레드처럼 비율보다 차이가 중요한 데이터의 변화량.",
    params=[{"name": "obs", "label": "간격(일)", "type": "int", "default": 1, "min": 1, "max": 252, "tip": "며칠 전 값과 비교할지 정합니다."}],
    code="ts.diff(x, {obs})",
    run=lambda c, p: ts.diff(c.x, int(p["obs"])))

add(id="lag", cat=CATS[5], title="시차 이동", input="x",
    desc="데이터를 N일 뒤로 밀어 냅니다. 오늘 자리에 N일 전 값이 들어갑니다.",
    read="원래 그래프를 오른쪽으로 N일 옮긴 모양입니다.",
    use="'어제 신호로 오늘 매매' 같은 백테스트에서 미래 정보를 쓰는 실수를 막을 때.",
    params=[{"name": "obs", "label": "밀어낼 일수", "type": "int", "default": 5, "min": -252, "max": 252, "tip": "양수면 뒤로(과거 값을 현재로), 음수면 앞으로 옮깁니다."},
            {"name": "mode", "label": "끝부분 처리", "type": "enum", "default": "extend",
             "options": [["extend", "날짜를 늘려 유지"], ["truncate", "원래 기간으로 자름"]],
             "tip": "밀어낸 만큼 생긴 날짜를 새로 만들지, 원래 기간에 맞춰 잘라낼지 정합니다."}],
    code="ts.lag(x, {obs}, LagMode.{mode})",
    run=lambda c, p: ts.lag(c.x, int(p["obs"]), LagMode(p["mode"])))

add(id="smooth_spikes", cat=CATS[5], title="튀는 값 다듬기", input="x",
    desc="양옆 값보다 한도 이상 튀는 점을 양옆의 평균으로 바꿉니다.",
    read="하루짜리 오류성 급등락이 사라진 선입니다.",
    use="데이터 오류나 일시적 이상치를 걸러 낼 때.",
    params=[{"name": "threshold", "label": "한도(비율)", "type": "float", "default": 0.05, "min": 0.001, "max": 1, "step": 0.01,
             "tip": "양옆보다 몇 % 이상 튀면 다듬을지 정합니다. 0.05면 5%입니다."}],
    code="ts.smooth_spikes(x, {threshold})",
    run=lambda c, p: ts.smooth_spikes(c.x, float(p["threshold"]), ThresholdType.percentage))

add(id="smooth_outliers", cat=CATS[5], title="이상 구간 다듬기", input="x",
    desc="주변 흐름(이동 중앙값)에서 크게 벗어났다가 돌아오는 구간을 찾아 직선으로 이어 줍니다. 여러 날 이어진 이상치도 처리합니다.",
    read="일시적인 급락·급등 구간이 매끈하게 이어진 선입니다.",
    use="며칠간 이어진 데이터 오류나 일시적 충격을 걸러 낼 때.",
    params=[{"name": "threshold", "label": "한도(비율)", "type": "float", "default": 0.3, "min": 0.01, "max": 5, "step": 0.05,
             "tip": "주변 흐름에서 몇 % 이상 벗어나면 이상 구간으로 볼지 정합니다."}],
    code="ts.smooth_outliers(x, {threshold})",
    run=lambda c, p: ts.smooth_outliers(c.x, float(p["threshold"])))

add(id="repeat", cat=CATS[5], title="빈 날 채우기", input="x",
    desc="주말·휴장일처럼 데이터가 없는 날을 직전 값으로 채워 매일 값이 있게 만듭니다. n을 키우면 n일마다 하나씩만 남깁니다.",
    read="계단 모양 선이 되며 날짜 수가 늘어납니다.",
    use="휴장일이 다른 시장의 데이터를 합칠 때.",
    params=[{"name": "n", "label": "간격(일)", "type": "int", "default": 1, "min": 1, "max": 90, "tip": "1이면 매일, 7이면 7일마다 하나씩 값을 남깁니다."}],
    code="ts.repeat(x, {n})",
    run=lambda c, p: ts.repeat(c.x, int(p["n"])))

add(id="consecutive", cat=CATS[5], title="연속 상승·하락 일수", input="x", src="returns",
    desc="수익률이 며칠 연속으로 양수(또는 음수)였는지 셉니다.",
    read="5면 5일 연속 상승(또는 하락) 중이라는 뜻입니다.",
    use="연속 상승·하락 이후 반전 가능성을 살펴볼 때.",
    params=[{"name": "direction", "label": "방향", "type": "enum", "default": "positive",
             "options": [["positive", "연속 상승"], ["negative", "연속 하락"]], "tip": "어느 쪽 연속 횟수를 셀지 정합니다."}],
    code="ts.consecutive(r, SignDirection.{direction})",
    run=lambda c, p: ts.consecutive(c.x, SignDirection(p["direction"])))

add(id="filter_", cat=CATS[5], title="조건 필터", input="x", src="returns",
    desc="조건에 맞는 값을 지웁니다. 예: '0보다 작은 값 제거'로 상승한 날만 남기기.",
    read="조건에 걸린 날짜가 빠진 데이터입니다.",
    use="특정 조건의 날만 따로 분석할 때(상승일만, 3% 이상 급락일만 등).",
    params=[{"name": "operator", "label": "지울 조건", "type": "enum", "default": "less_than",
             "options": [["less_than", "기준보다 작으면"], ["greater_than", "기준보다 크면"], ["l_equals", "기준 이하면"],
                         ["g_equals", "기준 이상이면"], ["equals", "기준과 같으면"], ["not_equals", "기준과 다르면"]],
             "tip": "어떤 값을 지울지 정합니다."},
            {"name": "value", "label": "기준값", "type": "float", "default": 0, "min": -1e9, "max": 1e9, "step": 0.01, "tip": "비교할 기준 숫자입니다. 수익률이면 0.03이 3%입니다."}],
    code="ts.filter_(r, FilterOperator.{operator}, {value})",
    run=lambda c, p: ts.filter_(c.x, FilterOperator(p["operator"]), float(p["value"])))

add(id="filter_dates", cat=CATS[5], title="날짜 필터", input="x",
    desc="기준 날짜보다 앞(또는 뒤)의 데이터를 지웁니다.",
    read="선택한 기간만 남은 데이터입니다.",
    use="특정 사건 이후(또는 이전)만 보고 싶을 때.",
    params=[{"name": "operator", "label": "지울 조건", "type": "enum", "default": "less_than",
             "options": [["less_than", "기준일 이전"], ["greater_than", "기준일 이후"], ["equals", "기준일 당일"]], "tip": "어느 쪽 날짜를 지울지 정합니다."},
            {"name": "date", "label": "기준 날짜", "type": "date", "default": "-90", "tip": "기준이 되는 날짜입니다."}],
    code="ts.filter_dates(x, FilterOperator.{operator}, date.fromisoformat('{date}'))",
    run=lambda c, p: ts.filter_dates(c.x, FilterOperator(p["operator"]), pd.Timestamp(_date(p["date"]))))

add(id="date_range", cat=CATS[5], title="기간 자르기", input="x",
    desc="시작일과 종료일 사이의 데이터만 잘라 냅니다. 숫자를 넣으면 '앞에서 n번째', '뒤에서 n번째' 위치로 자릅니다.",
    read="선택한 기간의 데이터입니다.",
    use="특정 기간(예: 하락장)만 따로 분석할 때.",
    params=[{"name": "start_date", "label": "시작일", "type": "date", "default": "-180", "tip": "남길 기간의 첫날입니다."},
            {"name": "end_date", "label": "종료일", "type": "date", "default": "-30", "tip": "남길 기간의 마지막 날입니다."},
            {"name": "weekdays_only", "label": "평일만", "type": "bool", "default": False, "tip": "켜면 토·일요일 데이터를 뺍니다."}],
    code="ts.date_range(x, date.fromisoformat('{start_date}'), date.fromisoformat('{end_date}'), {weekdays_only})",
    run=lambda c, p: ts.date_range(c.x, _date(p["start_date"]), _date(p["end_date"]), bool(p["weekdays_only"])))

add(id="value", cat=CATS[5], title="특정 날짜 값", input="x",
    desc="원하는 날짜의 값을 꺼냅니다. 그날 데이터가 없으면 직전 값을 씁니다.",
    read="결과는 숫자 하나입니다.",
    use="'1년 전 오늘 가격은?' 같은 질문.",
    params=[{"name": "date", "label": "날짜", "type": "date", "default": "-120", "tip": "값을 알고 싶은 날짜입니다."}],
    code="ts.value(x, date.fromisoformat('{date}'))",
    run=lambda c, p: ts.value(c.x, _date(p["date"])))

add(id="first", cat=CATS[5], title="첫 값", input="x",
    desc="데이터의 첫날 값을 모든 날짜에 채운 선입니다.",
    read="가로로 평평한 선이 시작 가격입니다.",
    use="시작 가격 대비 비교선이 필요할 때.",
    code="ts.first(x)",
    run=lambda c, p: ts.first(c.x))

add(id="last", cat=CATS[5], title="마지막 값", input="x",
    desc="데이터의 마지막 값을 모든 날짜에 채운 선입니다.",
    read="가로로 평평한 선이 현재 가격입니다.",
    use="현재 가격을 과거 흐름과 비교하는 기준선.",
    code="ts.last(x)",
    run=lambda c, p: ts.last(c.x))

add(id="last_value", cat=CATS[5], title="마지막 값 (숫자)", input="x",
    desc="데이터의 마지막 값을 숫자 하나로 꺼냅니다.",
    read="가장 최근 값입니다.",
    use="다른 계산에 현재 값을 넣을 때.",
    code="ts.last_value(x)",
    run=lambda c, p: ts.last_value(c.x))

add(id="interpolate", cat=CATS[5], title="날짜 맞추기 (보간)", input="xy",
    desc="X의 데이터를 Y가 가진 날짜에 맞춰 다시 배열합니다. 빈 날을 어떻게 채울지 고를 수 있습니다.",
    read="Y의 날짜 기준으로 정리된 X입니다.",
    use="한국 종목을 미국 거래일 기준으로 맞출 때처럼, 서로 다른 달력의 데이터를 합칠 때.",
    params=[{**INTERP, "default": "step"}],
    code="ts.interpolate(x, y, Interpolate.{method})",
    run=lambda c, p: ts.interpolate(c.x, c.y, Interpolate(p["method"])))

add(id="align", cat=CATS[5], title="두 데이터 날짜 정렬", input="xy",
    desc="두 종목의 날짜를 같은 기준으로 맞춥니다. 결과로 맞춰진 두 데이터가 함께 나옵니다.",
    read="두 선의 날짜가 정확히 일치합니다.",
    use="상관관계·베타처럼 두 데이터를 같은 날끼리 비교해야 할 때의 사전 작업.",
    params=[INTERP],
    code="ts.align(x, y, Interpolate.{method})",
    run=lambda c, p: ts.align(c.x, c.y, Interpolate(p["method"])))

add(id="union", cat=CATS[5], title="빈 날짜 메우기 (합치기)", input="xy",
    desc="X에 없는 날짜를 Y의 값으로 채웁니다. 두 데이터가 겹치면 X를 우선합니다.",
    read="두 데이터의 날짜가 합쳐진 하나의 선입니다.",
    use="데이터 출처 두 곳을 이어 붙여 빈칸 없는 시계열을 만들 때.",
    code="ts.union([x, y])",
    run=lambda c, p: ts.union([c.x, c.y]))

add(id="append", cat=CATS[5], title="뒤에 이어 붙이기", input="xy",
    desc="X가 끝난 뒤의 날짜부터 Y 데이터를 이어 붙입니다.",
    read="X 기간 다음에 Y가 이어진 선입니다.",
    use="과거 데이터와 최신 데이터를 다른 출처에서 가져와 연결할 때.",
    code="ts.append([x, y])",
    run=lambda c, p: ts.append([c.x, c.y]))

add(id="prepend", cat=CATS[5], title="앞에 이어 붙이기", input="xy",
    desc="Y가 시작되기 전까지는 X를 쓰고, 그 뒤부터는 Y를 씁니다.",
    read="앞부분은 X, 뒷부분은 Y인 선입니다.",
    use="최신 출처(Y)를 우선하되 그 이전 기간은 오래된 출처(X)로 채울 때.",
    code="ts.prepend([x, y])",
    run=lambda c, p: ts.prepend([c.x, c.y]))

add(id="bucketize", cat=CATS[5], title="기간별 묶기", input="x",
    desc="일별 데이터를 주·월·분기·연 단위로 묶어 각 묶음의 최대·최소·평균 등을 구합니다.",
    read="막대(기간)마다 값 하나가 나옵니다.",
    use="일별 가격으로 월말 가격, 월평균, 분기 최고가 등을 만들 때.",
    params=[{"name": "aggregate_function", "label": "묶음 계산", "type": "enum", "default": "last",
             "options": [["last", "마지막 값"], ["first", "첫 값"], ["mean", "평균"], ["max", "최대"], ["min", "최소"], ["sum", "합계"]],
             "tip": "각 기간 안에서 어떤 값을 대표로 쓸지 정합니다. '마지막 값 + 월'이면 월말 가격입니다."},
            {"name": "period", "label": "기간 단위", "type": "enum", "default": "month",
             "options": [["week", "주"], ["month", "월"], ["quarter", "분기"], ["year", "연"]], "tip": "얼마 단위로 묶을지 정합니다."}],
    code="ts.bucketize(x, AggregateFunction.{aggregate_function}, AggregatePeriod.{period})",
    run=lambda c, p: ts.bucketize(c.x, AggregateFunction(p["aggregate_function"]), AggregatePeriod(p["period"])))

# ================================================================ 산술·논리 연산
for fid, title, sym, desc in [
    ("add", "더하기", "+", "두 데이터를 날짜별로 더합니다."),
    ("subtract", "빼기", "-", "X에서 Y를 날짜별로 뺍니다. 지수화한 두 종목을 빼면 성과 차이(스프레드)가 됩니다."),
    ("multiply", "곱하기", "*", "두 데이터를 날짜별로 곱합니다."),
    ("divide", "나누기 (비율)", "/", "X를 Y로 나눕니다. 두 종목 가격 비율로 상대 강도를 볼 때 많이 씁니다."),
    ("floordiv", "몫 나누기", "//", "X를 Y로 나눈 몫(소수점 버림)입니다."),
]:
    add(id=fid, cat=CATS[6], title=title, input="xy",
        desc=desc + " 두 종목은 시작점을 100으로 지수화해서 넣습니다.",
        read="비율(나누기)이 오르면 X가 Y보다 강하다는 뜻입니다." if fid == "divide" else "날짜별 계산 결과입니다.",
        use="두 종목의 상대 성과 비교, 페어 트레이딩, 지표 조합.",
        params=[{**INTERP, "default": "step"}],
        code=f"ts.{fid}(ts.index(x, 100), ts.index(y, 100), Interpolate.{{method}})",
        run=(lambda f: lambda c, p: getattr(ts, f)(ts.index(c.x, 100), ts.index(c.y, 100), Interpolate(p["method"])))(fid))

add(id="abs_", cat=CATS[6], title="절댓값", input="x", src="returns",
    desc="음수를 양수로 바꿉니다. 방향은 무시하고 크기만 봅니다.",
    read="수익률에 쓰면 '하루에 얼마나 크게 움직였나'입니다.",
    use="움직임의 크기(변동성의 직관적 버전)를 볼 때.",
    code="ts.abs_(r)",
    run=lambda c, p: ts.abs_(c.x))

add(id="exp", cat=CATS[6], title="지수 함수 (e^x)", input="x", src="returns",
    desc="e(약 2.718)의 x제곱을 계산합니다. 로그 수익률을 일반 비율로 되돌릴 때 씁니다.",
    read="로그 수익률 0.05 → 1.051(약 5.1% 상승)입니다.",
    use="로그 수익률과 일반 수익률을 서로 바꿀 때.",
    code="ts.exp(r)",
    run=lambda c, p: ts.exp(c.x))

add(id="log", cat=CATS[6], title="자연로그", input="x",
    desc="값의 자연로그를 계산합니다. 가격에 로그를 씌우면 같은 비율 변화가 같은 높이로 보입니다.",
    read="오래된 차트에서 10→20과 100→200이 같은 높이로 그려집니다.",
    use="장기 차트(로그 스케일), 로그 수익률 계산.",
    code="ts.log(x)",
    run=lambda c, p: ts.log(c.x))

add(id="power", cat=CATS[6], title="거듭제곱", input="x", src="returns",
    desc="각 값을 y제곱합니다.",
    read="수익률을 제곱하면 분산 계산의 재료가 됩니다.",
    use="분산·변동성을 직접 계산해 볼 때.",
    params=[{"name": "y", "label": "지수(y)", "type": "float", "default": 2, "min": -10, "max": 10, "step": 0.5, "tip": "몇 제곱할지 정합니다. 2는 제곱, 0.5는 제곱근입니다."}],
    code="ts.power(r, {y})",
    run=lambda c, p: ts.power(c.x, float(p["y"])))

add(id="sqrt", cat=CATS[6], title="제곱근", input="x",
    desc="각 값의 제곱근을 계산합니다.",
    read="분산의 제곱근이 표준편차입니다.",
    use="분산을 변동성으로 바꿀 때, 시간 비례 위험(√시간) 계산.",
    code="ts.sqrt(x)",
    run=lambda c, p: ts.sqrt(c.x))

add(id="floor", cat=CATS[6], title="하한 고정", input="x", src="returns",
    desc="기준값보다 작은 값을 기준값으로 올립니다.",
    read="선이 기준값 아래로 내려가지 않습니다.",
    use="손실 상한을 둔 상품(원금보장형 등)의 손익 구조를 흉내 낼 때.",
    params=[{"name": "value", "label": "하한값", "type": "float", "default": -0.02, "min": -1e9, "max": 1e9, "step": 0.01, "tip": "이 값보다 작으면 이 값으로 바꿉니다. 수익률이면 -0.02가 -2%입니다."}],
    code="ts.floor(r, {value})",
    run=lambda c, p: ts.floor(c.x, float(p["value"])))

add(id="ceil", cat=CATS[6], title="상한 고정", input="x", src="returns",
    desc="기준값보다 큰 값을 기준값으로 내립니다.",
    read="선이 기준값 위로 올라가지 않습니다.",
    use="수익 상한이 있는 상품(커버드콜 등)의 손익 구조를 흉내 낼 때.",
    params=[{"name": "value", "label": "상한값", "type": "float", "default": 0.02, "min": -1e9, "max": 1e9, "step": 0.01, "tip": "이 값보다 크면 이 값으로 바꿉니다."}],
    code="ts.ceil(r, {value})",
    run=lambda c, p: ts.ceil(c.x, float(p["value"])))

add(id="weighted_sum", cat=CATS[6], title="가중 합계", input="list",
    desc="여러 종목을 비중대로 섞은 값(가중 평균)을 날짜별로 계산합니다. 리밸런싱 없이 단순히 섞는 계산입니다.",
    read="각 종목을 100으로 지수화한 뒤 비중대로 합친 선입니다.",
    use="간단한 지수·바스켓 만들기. 매매 비용과 리밸런싱까지 넣으려면 '포트폴리오 백테스트'를 쓰세요.",
    params=[{"name": "weights", "label": "비중(쉼표 구분)", "type": "text", "default": "", "tip": "종목 순서대로 비중을 쉼표로 적습니다. 예: 0.6, 0.4. 비우면 똑같이 나눕니다."}],
    code="ts.weighted_sum([ts.index(s, 100) for s in series], [{weights}])",
    run=lambda c, p: ts.weighted_sum([ts.index(s, 100) for s in c.xs], c.weights(p["weights"])))

add(id="if_", cat=CATS[6], title="조건 선택 (if)", input="xy",
    desc="조건이 참인 날은 X, 거짓인 날은 Y 값을 씁니다. 여기서는 'X가 오른 날'을 조건으로 씁니다.",
    read="X가 오른 날은 X의 수익률, 내린 날은 Y의 수익률이 들어간 선입니다.",
    use="조건에 따라 자산을 바꾸는 규칙(스위칭 전략)을 만들 때.",
    code="ts.if_(flags, ts.returns(x), ts.returns(y))  # flags = X 상승일이면 1",
    run=lambda c, p: ts.if_(_flags(c.x), ts.returns(c.x).fillna(0), ts.returns(c.y).fillna(0)))

add(id="and_", cat=CATS[6], title="논리 AND", input="xy",
    desc="두 조건이 모두 참이면 1, 아니면 0입니다. 여기서는 'X와 Y가 둘 다 오른 날'을 찾습니다.",
    read="1인 날이 두 종목이 함께 오른 날입니다.",
    use="여러 조건을 동시에 만족하는 날을 찾을 때(매매 신호 조합).",
    code="ts.and_(x_up, y_up)",
    run=lambda c, p: ts.and_(*ts.align(_flags(c.x), _flags(c.y), Interpolate.INTERSECT)))

add(id="or_", cat=CATS[6], title="논리 OR", input="xy",
    desc="둘 중 하나라도 참이면 1입니다. 여기서는 'X나 Y 중 하나라도 오른 날'을 찾습니다.",
    read="0인 날이 둘 다 내린 날입니다.",
    use="여러 신호 중 하나라도 나오면 행동하는 규칙.",
    code="ts.or_(x_up, y_up)",
    run=lambda c, p: ts.or_(*ts.align(_flags(c.x), _flags(c.y), Interpolate.INTERSECT)))

add(id="not_", cat=CATS[6], title="논리 NOT", input="x",
    desc="참과 거짓을 뒤집습니다. 여기서는 'X가 오르지 않은 날'이 1이 됩니다.",
    read="1인 날이 하락(또는 보합)한 날입니다.",
    use="조건을 반대로 쓰고 싶을 때.",
    code="ts.not_(x_up)",
    run=lambda c, p: ts.not_(_flags(c.x)))

# ================================================================ 날짜·달력
for fid, title, read in [("day", "일(日)", "1~31"), ("month", "월", "1~12"), ("year", "연도", "예: 2026"),
                         ("quarter", "분기", "1~4"), ("weekday", "요일", "0=월요일 … 4=금요일")]:
    add(id=fid, cat=CATS[7], title=f"날짜 → {title}", input="x",
        desc=f"각 데이터의 날짜에서 {title}만 꺼냅니다.",
        read=f"값은 {read}입니다.",
        use="요일 효과, 월말 효과, 분기 실적 시즌처럼 달력 패턴을 분석할 때.",
        code=f"ts.{fid}(x)",
        run=(lambda f: lambda c, p: getattr(ts, f)(c.x))(fid))

add(id="day_count_fractions", cat=CATS[7], title="이자 일수 비율", input="x",
    desc="연속된 날짜 사이 기간을 '1년 중 몇 분의 몇'으로 계산합니다. 채권·스왑 이자 계산의 기본입니다.",
    read="ACT/360 기준으로 하루는 약 0.00278(=1/360)입니다.",
    use="채권 이자, 예금 이자를 정확히 계산할 때.",
    params=[{"name": "convention", "label": "일수 계산 관행", "type": "enum", "default": "ACTUAL_360",
             "options": [["ACTUAL_360", "ACT/360 (단기금리·달러)"], ["ACTUAL_365F", "ACT/365 고정 (원화·파운드)"], ["ACTUAL_365L", "ACT/365L"],
                         ["ACTUAL_364", "ACT/364"], ["ACTUAL_365_25", "ACT/365.25"], ["ONE_ONE", "1/1"]],
             "tip": "1년을 며칠로 볼지 정하는 시장 관행입니다. 원화 금리는 보통 ACT/365, 달러 단기금리는 ACT/360을 씁니다."}],
    code="ts.day_count_fractions(x, DayCountConvention.{convention})",
    run=lambda c, p: ts.day_count_fractions(c.x, DayCountConvention(p["convention"])))

add(id="day_countdown", cat=CATS[7], title="D-day 카운트다운", input="x",
    desc="각 날짜에서 목표일까지 며칠 남았는지 셉니다.",
    read="값이 0이 되는 날이 목표일입니다.",
    use="옵션 만기, 실적 발표, 배당 기준일까지 남은 기간 계산.",
    params=[{"name": "end_date", "label": "목표일", "type": "date", "default": "+60", "tip": "카운트다운할 목표 날짜입니다."},
            {"name": "business_days", "label": "영업일 기준", "type": "bool", "default": True, "tip": "켜면 주말을 빼고 셉니다."}],
    code="ts.day_countdown(date.fromisoformat('{end_date}'), x.index[0], {business_days})",
    run=lambda c, p: ts.day_countdown(_date(p["end_date"]), c.x.index[0].date(), bool(p["business_days"])))

add(id="generate_series", cat=CATS[7], title="예시 데이터 만들기", input="none",
    desc="연습용 가상 가격 데이터를 무작위로 만듭니다. 실행할 때마다 달라집니다.",
    read="실제 종목과 무관한 가상의 가격 흐름입니다.",
    use="실제 데이터 없이 함수를 연습하거나 전략을 시험할 때.",
    params=[{"name": "length", "label": "길이(일)", "type": "int", "default": 252, "min": 10, "max": 2000, "tip": "몇 일치 데이터를 만들지 정합니다."},
            {"name": "direction", "label": "날짜 방향", "type": "enum", "default": "end_today",
             "options": [["end_today", "오늘에서 끝남"], ["start_today", "오늘부터 시작"]], "tip": "만든 데이터의 날짜를 과거로 붙일지 미래로 붙일지 정합니다."}],
    code="ts.generate_series({length}, Direction.{direction})",
    run=lambda c, p: ts.generate_series(int(p["length"]), Direction(p["direction"])))

# ================================================================ 포트폴리오
add(id="basket_series", cat=CATS[8], title="바스켓(포트폴리오) 백테스트", input="list",
    desc="여러 종목을 정한 비중으로 담고 주기적으로 비중을 다시 맞추면서(리밸런싱) 매매 비용까지 반영해 포트폴리오 가치를 계산합니다.",
    read="1에서 시작한 포트폴리오 가치입니다. 1.3이면 30% 수익입니다.",
    use="'이 종목들을 이 비중으로 들고 있었다면?'을 확인할 때. 자세한 비교는 '포트폴리오 백테스트' 탭을 쓰세요.",
    params=[{"name": "weights", "label": "비중(쉼표 구분)", "type": "text", "default": "", "tip": "종목 순서대로 비중을 쉼표로 적습니다. 예: 0.6, 0.4. 비우면 똑같이 나눕니다."},
            {"name": "cost", "label": "매매 비용(%)", "type": "float", "default": 0.1, "min": 0, "max": 5, "step": 0.05, "tip": "사고팔 때마다 드는 수수료·세금·슬리피지를 거래금액 대비 %로 넣습니다. 0.1은 0.1%입니다."},
            {"name": "rebal_freq", "label": "리밸런싱 주기", "type": "enum", "default": "monthly",
             "options": [["daily", "매일"], ["weekly", "매주"], ["monthly", "매월"]], "tip": "비중이 틀어졌을 때 원래 비중으로 다시 맞추는 주기입니다."}],
    code="ts.backtesting.basket_series(series, [{weights}], [{cost} / 100] * len(series), RebalFreq.{rebal_freq})",
    run=lambda c, p: ts.backtesting.basket_series(c.xs, c.weights(p["weights"]), [float(p["cost"]) / 100] * len(c.xs), RebalFreq(p["rebal_freq"])))


REGISTRY = {f["id"]: f for f in F}


def catalog():
    """프런트엔드에 보낼 목록(실행 함수 제외)"""
    return {"categories": CATS,
            "functions": [{k: v for k, v in f.items() if k != "run"} for f in F]}
