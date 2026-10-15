# GS Quant 한국어 시작 가이드

GS Quant를 처음 쓰는 분을 위해 설치부터 첫 분석까지 단계별로 정리했습니다.

## 목차

1. [GS Quant로 할 수 있는 일](#1-gs-quant로-할-수-있는-일)
2. [설치](#2-설치)
3. [계정 없이 쓰기: 시계열 분석](#3-계정-없이-쓰기-시계열-분석)
4. [초보자용 대시보드](#4-초보자용-대시보드)
5. [계정이 있을 때: Marquee 연결](#5-계정이-있을-때-marquee-연결)
6. [더 배우기](#6-더-배우기)

## 1. GS Quant로 할 수 있는 일

| 모듈 | 하는 일 | GS 계정 필요 |
| --- | --- | --- |
| `gs_quant.timeseries` | 수익률, 변동성, 이동평균, 베타, 상관관계 등 시계열 분석 | 대부분 불필요 |
| `gs_quant.data` | Marquee 데이터셋 조회 (시세, 변동성 곡면 등) | 필요 |
| `gs_quant.instrument`, `gs_quant.risk` | 스왑·옵션 같은 파생상품 정의와 가격·위험 계산 | 정의는 불필요, 계산은 필요 |
| `gs_quant.markets.portfolio` | 포트폴리오 구성과 위험 분석 | 필요 |
| `gs_quant.backtests` | 전략 백테스트 | 필요 |

> GS 계정(클라이언트 ID·시크릿)은 골드만삭스 기관 고객에게만 발급됩니다. 개인 투자자라면 3번과 4번 섹션부터 시작하세요.

## 2. 설치

Python 3.10 이상이 필요합니다.

```bash
git clone https://github.com/HyeonbinJung/gs-quant-easy.git
cd gs-quant-easy
python -m venv .venv
```

가상환경을 켭니다.

```bash
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

패키지를 설치합니다. 대시보드를 쓰려면 `flask`도 함께 설치합니다.

```bash
pip install -e . flask
```

설치를 확인합니다.

```bash
python -c "import gs_quant; print(gs_quant.__version__)"
```

## 3. 계정 없이 쓰기: 시계열 분석

`gs_quant.timeseries` 함수는 pandas `Series`를 받아 바로 계산하므로, 가격 데이터만 있으면 계정 없이 쓸 수 있습니다.

```python
import pandas as pd
import gs_quant.timeseries as ts

# 날짜를 인덱스로 하는 가격 시계열
prices = pd.Series(
    [100, 102, 101, 105, 107, 106, 110],
    index=pd.bdate_range("2026-01-01", periods=7),
)
```

### 수익률과 위험

```python
ts.returns(prices)          # 일별 수익률 (0.02 = 2%)
ts.volatility(prices, 5)    # 최근 5일 기준 연환산 변동성(%)
ts.max_drawdown(prices)     # 고점 대비 최대 낙폭 (-0.1 = -10%)
```

### 추세와 기술적 지표

```python
ts.moving_average(prices, 3)              # 3일 이동평균
ts.bollinger_bands(prices, 5)             # 볼린저 밴드 (하단, 상단)
ts.relative_strength_index(prices, 14)    # RSI (0~100, 70 이상 과열)
ts.zscores(prices)                        # 평균 대비 몇 표준편차 떨어져 있는지
```

### 다른 자산과 비교

```python
benchmark = pd.Series(
    [50, 50.5, 50.2, 51, 51.8, 51.5, 52.5],
    index=prices.index,
)

ts.beta(prices, benchmark, 5)       # 시장이 1% 움직일 때 몇 % 움직이는지
ts.correlation(prices, benchmark)   # 같이 움직이는 정도 (-1 ~ 1)
```

### 창(Window) 지정

이동평균, 변동성처럼 "최근 N일"로 계산하는 함수는 `w` 인자로 구간을 정합니다.

```python
from gs_quant.timeseries import Window

ts.volatility(prices, Window(22, 22))   # 22일 구간, 처음 22개 값은 계산에서 제외
ts.volatility(prices, "1m")             # 1개월처럼 기간 문자열도 가능
```

주식시장은 한 달에 약 22일, 1년에 약 252일 열립니다.

## 4. 초보자용 대시보드

코드 없이 화면에서 분석해 보고 싶다면 대시보드를 실행하세요.

```bash
python dashboard/app.py
```

브라우저에서 http://localhost:5050 을 열면 됩니다.

- 티커 입력: 미국 주식은 `AAPL`, 한국 코스피 종목은 `005930.KS`, 코스닥 종목은 `247540.KQ`처럼 입력합니다.
- 용어 설명: 모든 지표 이름과 <kbd>?</kbd> 아이콘에 마우스를 올리면 쉬운 설명과 사용한 gs_quant 함수가 나타납니다.
- 시세 데이터: Yahoo Finance 공개 시세를 사용합니다. 인터넷 연결이 없으면 예시 데이터로 계산하고 화면에 안내가 표시됩니다.

## 5. 계정이 있을 때: Marquee 연결

기관 고객으로 클라이언트 ID와 시크릿을 받았다면 세션을 열고 GS 데이터와 가격 계산 기능을 쓸 수 있습니다.

```python
from gs_quant.session import GsSession, Environment

GsSession.use(
    Environment.PROD,
    client_id="발급받은_클라이언트_ID",
    client_secret="발급받은_시크릿",
    scopes=("read_product_data",),
)
```

> 클라이언트 시크릿은 코드에 직접 쓰지 말고 환경 변수 등으로 관리하세요.

### 데이터셋 조회

```python
from datetime import date
from gs_quant.data import Dataset

ds = Dataset("데이터셋_ID")
df = ds.get_data(date(2026, 1, 1), date(2026, 3, 31), bbid=["EURUSD"])
```

### 파생상품 가격 계산

```python
from gs_quant.common import PayReceive, Currency
from gs_quant.instrument import IRSwap
import gs_quant.risk as risk

swap = IRSwap(PayReceive.Pay, "10y", Currency.USD)   # 10년 만기 USD 금리스왑(고정금리 지급)
swap.price()                 # 현재 가치
swap.calc(risk.IRDelta)      # 금리 민감도
```

## 6. 더 배우기

- [gs_quant/documentation/](gs_quant/documentation/README.md): 기능별 튜토리얼과 예제 노트북
- [gs_quant/content/](gs_quant/content/README.md): GS Quant로 만든 리서치 사례
- [Goldman Sachs Developer](https://developer.gs.com/docs/gsquant/): 공식 문서 (영문)

## 자주 쓰는 용어

| 용어 | 뜻 |
| --- | --- |
| 변동성 (Volatility) | 가격이 출렁이는 정도. 1년 기준 %로 표시하며 높을수록 위험 |
| 최대 낙폭 (MDD) | 최고점에서 최저점까지 가장 크게 떨어진 비율 |
| 베타 (Beta) | 시장 대비 민감도. 1보다 크면 시장보다 크게 움직임 |
| 상관관계 (Correlation) | 두 자산이 같은 방향으로 움직이는 정도 (-1 ~ 1) |
| RSI | 최근 상승·하락 힘의 비율. 70 이상 과열, 30 이하 침체 |
| Z-점수 | 평균에서 표준편차 몇 배만큼 떨어져 있는지 |
| 금리스왑 (IRS) | 고정금리와 변동금리를 서로 교환하는 파생상품 |
| 델타 (Delta) | 기초 변수(금리, 가격)가 조금 변할 때 상품 가치가 변하는 정도 |
