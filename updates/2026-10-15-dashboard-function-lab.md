# 2026-10-15 · 대시보드 확장: 함수 실험실, 포트폴리오 백테스트, 날짜·이자 계산기

## 요약

대시보드가 gs_quant 시계열 함수 9개만 쓰던 것을, GS 계정 없이 쓸 수 있는 기능 대부분으로 넓혔습니다. 화면을 4개 탭으로 나누고, 새로 넣은 모든 함수와 입력 항목에 초보자용 설명을 붙였습니다.

## ✨ 새 탭

### 함수 실험실 (`#lab`)

- 계정 없이 동작하는 gs_quant 함수 **87가지**를 9개 분류로 정리
  - 수익률·가격 변환(7): `returns`, `prices`, `index`, `change`, `annualize`, `excess_returns`, `geometrically_aggregate`
  - 위험·변동성(10): `volatility`, `vol_swap_volatility`, `exponential_volatility`, `exponential_spread_volatility`, `std`, `exponential_std`, `var`, `max_drawdown`, `range_`, 이동 샤프 지수(`get_ratio_pure` + `excess_returns`)
  - 시장 비교·관계(5): `beta`, `correlation`, `corr_swap_correlation`, `cov`, `compare`
  - 추세·기술적 지표(8): `moving_average`, `smoothed_moving_average`, `exponential_moving_average`, `macd`, `bollinger_bands`, `relative_strength_index`, `trend`, `seasonally_adjusted`
  - 기초 통계(12): `mean`, `median`, `mode`, `min_`, `max_`, `sum_`, `product`, `percentile`, `percentiles`, `zscores`, `winsorize`, `count`
  - 데이터 정리(19): `diff`, `lag`, `smooth_spikes`, `smooth_outliers`, `repeat`, `consecutive`, `filter_`, `filter_dates`, `date_range`, `value`, `first`, `last`, `last_value`, `interpolate`, `align`, `union`, `append`, `prepend`, `bucketize`
  - 산술·논리 연산(17): `add`, `subtract`, `multiply`, `divide`, `floordiv`, `abs_`, `exp`, `log`, `power`, `sqrt`, `floor`, `ceil`, `weighted_sum`, `if_`, `and_`, `or_`, `not_`
  - 날짜·달력(8): `day`, `month`, `year`, `quarter`, `weekday`, `day_count_fractions`, `day_countdown`, `generate_series`
  - 포트폴리오(1): `basket_series`
- 함수마다 표시하는 것
  - 무엇인가요(쉬운 설명) / 어떻게 읽나요(결과 해석) / 언제 쓰나요(활용 사례)
  - 파라미터별 입력칸과 마우스 오버 설명(기본값 포함)
  - 결과 차트(입력 데이터를 오른쪽 축에 겹쳐 보기 가능), 숫자 하나로 나오는 결과는 크게 표시
  - 같은 계산을 하는 파이썬 코드
- 함수 이름·설명 검색
- 입력 데이터를 가격 또는 일별 수익률로 바꿔 넣을 수 있음(함수마다 알맞은 기본값)

### 포트폴리오 백테스트 (`#backtest`)

- `gs_quant.timeseries.backtesting.basket_series`로 2~8개 종목 포트폴리오 계산
- 비중, 리밸런싱 주기(매일·매주·매월), 매매 비용(%), 기간 설정
- 자산 성장 곡선: 선택한 주기의 포트폴리오, 다른 리밸런싱 주기, "사서 그대로 두기", 개별 종목 비교
- 성과 표: 기간 수익률, 연평균 수익률, 변동성, 최대 낙폭, 샤프 지수
- "쉽게 읽기" 자동 해설: 성과 요약, 종목 간 평균 상관관계에 따른 분산 효과, 가장 효율적인 종목
- 예시 포트폴리오 4종: 주식60·채권40, 국내 반도체, 주식·금·채권, 미국 빅테크 5

### 날짜·이자 계산기 (`#dates`)

- `gs_quant.datetime`의 `business_day_count`, `business_day_offset`, `day_count_fraction`, `is_business_day` 사용
- 달력 일수, 영업일 수(주말 제외), N영업일 뒤 날짜, 기간 비율
- 일수 계산 관행 6종(ACT/365F, ACT/360 등) 비교
- 세전 이자와 한국 이자소득세 15.4%를 뺀 세후 이자

## 🔧 개선

- 상단 탭 메뉴 추가, 마지막으로 본 탭 기억, 주소 해시(`#lab` 등)로 탭 바로 열기
- 같은 종목·기간 시세는 10분간 캐시해 함수 실험실 반응 속도 개선
- 툴팁이 동적으로 생성된 항목(함수 목록, 파라미터)에도 동작하도록 확장

## ✅ 검증

- 87개 함수 모두 실제 시세(AAPL, MSFT, 005930.KS, 2년)로 실행해 결과가 나오는 것을 자동 테스트로 확인
- 4개 탭을 헤드리스 Chrome으로 열어 화면 렌더링 확인
- 확인 중 고친 문제: `bollinger_bands` 결과 열 이름 중복, `filter_dates` 날짜 형식 불일치, `basket_series`가 100에서 시작해 다른 곡선(1에서 시작)과 축이 맞지 않던 문제, 숨겨진 패널에서 그린 백테스트 차트가 보이지 않던 문제

## 계정이 있어야 해서 넣지 않은 것

- Marquee 데이터셋 조회, 파생상품 가격·위험 계산, 포트폴리오 위험 리포트, 전략 백테스트 엔진, 팩터 모델, 바스켓·지수 관리
- GS 데이터로 계산하는 `measures` 계열 지표(200개 이상)
- 공휴일 달력(영업일 계산은 주말만 제외)
