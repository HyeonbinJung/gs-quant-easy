# 2026-10-15 · 한국어 문서와 초보자용 대시보드 추가

## 요약

원본 GS Quant(2.2.1) 포크에 한국어 문서를 추가하고, 금융 초보자도 쓸 수 있는 웹 대시보드를 만들었습니다. 라이브러리 코드(`gs_quant/`)는 변경하지 않아 원본 업데이트를 계속 받을 수 있습니다.

## ✨ 새 기능: 초보자용 대시보드 (`dashboard/`)

- `dashboard/app.py`: Flask 서버. `gs_quant.timeseries` 함수로 지표를 계산
- `dashboard/index.html`: 한국어 화면 (Chart.js 차트)
- 실행: `python dashboard/app.py` → http://localhost:5050 (`PORT` 환경 변수로 변경 가능)

### 화면 구성

- 종목 입력(최대 5개), 분석 기간(6개월~5년), 이동 구간(10·22·63일), 비교 기준(S&P 500, KOSPI, 나스닥)
- 한국·미국 주식 예시 버튼 (삼성전자, SK하이닉스, 에코프로비엠, 애플, 엔비디아, 테슬라, S&P500 ETF)
- 요약 카드 8개: 현재가, 기간 수익률, 연평균 수익률, 변동성, 최대 낙폭, 샤프 지수, RSI, 베타
- 차트: 수익률 비교, 가격과 볼린저 밴드, 변동성 추이, 고점 대비 하락폭, RSI, Z-점수, 베타 추이
- 종목 간 상관관계 표 (분산 효과를 색으로 표시)
- 용어 사전

### 초보자 지원

- **마우스 오버 설명**: 모든 지표 이름, 입력 항목, 차트 제목의 `?` 아이콘에 마우스를 올리면(모바일은 탭) 쉬운 설명과 사용한 gs_quant 함수가 표시됨
- **색깔 해석 문구**: 각 수치 아래에 "안정적 (낮음)", "과열 구간", "위험 대비 수익 좋음" 같은 해석을 초록·노랑·빨강으로 표시
- "처음이신가요?" 3단계 안내

### 사용한 gs_quant 함수

`returns`, `volatility`, `max_drawdown`, `moving_average`, `bollinger_bands`, `relative_strength_index`, `zscores`, `beta`, `correlation`

### 데이터

- GS Marquee 계정 없이 쓸 수 있도록 Yahoo Finance 공개 시세(수정 종가)를 사용
- 존재하지 않는 티커는 "종목을 찾을 수 없습니다" 안내
- 네트워크 오류 시 예시 데이터로 계산하고 화면 상단에 안내 표시
- 샤프 지수는 무위험 금리를 0으로 단순화해 계산 (gs_quant `sharpe_ratio`는 GS 금리 데이터가 필요하기 때문)

## 🌐 한국어 문서

- `README.md`: 한국어로 다시 쓰고 배지, 목차, 대시보드·설치·시작하기·문서 표 섹션 추가
- `GETTING_STARTED.ko.md` (신규): 설치, 계정 없이 쓰는 시계열 분석, 대시보드, Marquee 연결, 용어 표
- `CONTRIBUTING.md`: 한국어 번역. DCO 양식은 법적 문서라 영문 원문을 유지하고 참고 번역을 덧붙임. 필요 Python 버전을 `pyproject.toml`에 맞춰 3.9+에서 3.10+으로 수정
- `CODE_OF_CONDUCT.md`: 한국어 번역 (기여자 서약 1.4)
- `gs_quant/documentation/README.md`, `gs_quant/content/README.md`: 소개 문단 번역, 파일 목록은 원문 유지

## 🗂️ 기타

- `.gitignore`에 `.venv/` 추가
- `updates/` 폴더 신설: 이후 변경 내역은 `YYYY-MM-DD-주제.md` 형식으로 기록
