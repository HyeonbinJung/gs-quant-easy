<div align="center">

# 📊 GS Quant Easy

**골드만삭스 퀀트 라이브러리 [GS Quant](https://github.com/goldmansachs/gs-quant)를 한국어로, 더 쉽게**

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Language](https://img.shields.io/badge/언어-한국어-success)
![License](https://img.shields.io/badge/license-Apache%202.0-lightgrey)

[소개](#-소개) · [대시보드](#-초보자용-대시보드) · [설치](#-설치) · [시작하기](#-시작하기) · [문서](#-문서와-예제) · [업데이트 내역](updates/)

</div>

---

## 💡 소개

**GS Quant**는 세계에서 가장 강력한 위험 이전(risk transfer) 플랫폼 중 하나를 기반으로 만든 퀀트 금융용 파이썬 툴킷입니다. 25년 이상 글로벌 시장을 다뤄 온 경험을 바탕으로, 퀀트 트레이딩 전략과 위험 관리 솔루션 개발을 빠르게 할 수 있도록 설계되었습니다.

골드만삭스의 퀀트 개발자들이 트레이딩 전략 개발과 파생상품 분석을 위해 직접 만들고 관리합니다. 파생상품 구조화, 트레이딩, 위험 관리에 쓸 수 있고, 데이터 분석용 통계 패키지로도 활용할 수 있습니다.

**gs-quant-easy**는 원본 GS Quant를 포크해 다음을 더했습니다.

- 🇰🇷 한국어 문서 (README, 기여 가이드, 행동 강령, 시작 가이드)
- 🖥️ 금융 초보자용 웹 대시보드 (용어에 마우스를 올리면 쉬운 설명 표시)

> [!NOTE]
> GS Quant의 API(Marquee 데이터, 상품 가격 계산 등)를 쓰려면 클라이언트 ID와 시크릿이 필요합니다. 이는 골드만삭스 **기관 고객**에게만 제공되며, 담당 세일즈나 Marquee 세일즈 팀에 문의해야 합니다. 다만 `gs_quant.timeseries`의 분석 함수와 아래 대시보드는 **계정 없이** 사용할 수 있습니다.

## 🖥️ 초보자용 대시보드

GS 계정 없이 쓸 수 있는 gs_quant 기능을 코드 없이 화면에서 써볼 수 있는 한국어 웹 대시보드입니다. 모든 용어·입력 항목·함수에 마우스를 올리면 초보자용 설명이 나타납니다.

| 탭 | 내용 | 사용하는 gs_quant 기능 |
| --- | --- | --- |
| **종목 분석** | 수익률, 변동성, 최대 낙폭, 샤프 지수, RSI, 베타 카드와 차트. 수치마다 "안정적", "과열 구간" 같은 색깔 해석 | `timeseries` |
| **포트폴리오 백테스트** | 여러 종목을 비중대로 담고 리밸런싱 주기·매매 비용을 반영한 과거 성과, 리밸런싱 주기별 비교, 비중 변화 | `basket_series`, `backtest_basket` |
| **전략 백테스트** | 적립식 매수, 눌림목 매수, 추세 추종, 평균 회귀 전략을 과거 시세로 실행. 자산 곡선, 매매 시점, 매매 장부, 승률 | `backtests.PredefinedAssetEngine`, 트리거·액션 |
| **함수 실험실** | 계정 없이 쓸 수 있는 함수 **97가지**. 함수마다 "무엇인가요 / 어떻게 읽나요 / 언제 쓰나요", 파라미터 설명, 결과 차트, 파이썬 코드 | `timeseries`, `datetime` |
| **파생상품 살펴보기** | 금리 스왑, 스왑션, 캡·플로어, 선물환, 외환·주식 옵션, 분산 스왑, 원자재 스왑, 채권, CDS 지수 등 **15종**을 직접 만들고 만기 손익 구조 그래프로 이해 | `instrument` |
| **전염병 모델** | SIR, SEIR, SEIRCM(확진·사망·방역 정책) 확산 시뮬레이션과 파라미터 추정(fit) 시연 | `models.epidemiology` |
| **날짜·이자 계산기** | 영업일 수, N영업일 뒤 날짜, 일수 계산 관행별 기간 비율과 세전·세후 이자 | `datetime` |

- **한국·미국 주식 지원**: `005930.KS`(삼성전자), `247540.KQ`(에코프로비엠), `AAPL`(애플) 등
- 시세는 Yahoo Finance 공개 데이터를 사용하므로 GS 계정이 없어도 됩니다.
- 탭 주소를 바로 열 수 있습니다: `http://localhost:5050/#lab`, `#backtest`, `#strategy`, `#instruments`, `#epidemic`, `#dates`

```bash
pip install -e . flask
python dashboard/app.py
# → http://localhost:5050
```

포트를 바꾸려면 `PORT` 환경 변수를 지정합니다. 예: `PORT=8000 python dashboard/app.py`

## 📦 설치

**요구 사항**

- Python 3.10 이상
- pip 패키지 관리자

**PyPI에서 원본 설치**

```bash
pip install gs-quant
```

**이 저장소에서 설치 (대시보드 포함)**

```bash
git clone https://github.com/HyeonbinJung/gs-quant-easy.git
cd gs-quant-easy
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -e . flask
```

## 🚀 시작하기

설치부터 첫 분석까지 한국어로 정리한 [시작 가이드](GETTING_STARTED.ko.md)를 참고하세요. 간단한 예시는 다음과 같습니다.

```python
import pandas as pd
import gs_quant.timeseries as ts

prices = pd.Series([100, 102, 101, 105, 107, 106, 110],
                   index=pd.bdate_range("2026-01-01", periods=7))

ts.returns(prices)         # 일별 수익률
ts.volatility(prices, 5)   # 5일 기준 연환산 변동성(%)
ts.max_drawdown(prices)    # 최대 낙폭
```

## 📚 문서와 예제

| 위치 | 내용 |
| --- | --- |
| [GETTING_STARTED.ko.md](GETTING_STARTED.ko.md) | 한국어 시작 가이드 |
| [gs_quant/documentation/](gs_quant/documentation/README.md) | 기능별 튜토리얼과 예제 노트북 (데이터, 마켓, 가격·위험, 포트폴리오, 백테스트 등) |
| [gs_quant/content/](gs_quant/content/README.md) | GS Quant로 만든 리서치·사례 연구 노트북 |
| [Goldman Sachs Developer](https://developer.gs.com/docs/gsquant/) | 공식 문서, 가이드, 튜토리얼 (영문) |

## 🤝 기여하기

기여 방법은 [CONTRIBUTING.md](CONTRIBUTING.md)를, 커뮤니티 규칙은 [행동 강령](CODE_OF_CONDUCT.md)을 참고하세요.

## ❓ 도움말

원본 GS Quant에 대한 질문, 의견, 피드백은 `gs-quant@gs.com`으로 보내주세요. 이 포크(한국어 문서, 대시보드)에 대한 문의는 이 저장소의 이슈로 남겨주세요.

## 📄 라이선스

[Apache License 2.0](LICENSE). 원본 저작권은 Goldman Sachs에 있습니다.
