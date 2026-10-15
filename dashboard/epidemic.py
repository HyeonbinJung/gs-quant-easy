"""
전염병 확산 모델: gs_quant.models.epidemiology (SIR, SEIR, SEIRCM)

모델 방정식 풀이와 파라미터 추정(fit)은 gs_quant의 EpidemicModel을 그대로 쓴다.
"""

import numpy as np

from gs_quant.models.epidemiology import SEIR, SEIRCM, SIR, EpidemicModel

COMMON = [
    {"name": "N", "label": "전체 인구", "type": "float", "default": 1_000_000, "min": 100, "max": 1e10,
     "tip": "모델이 다루는 전체 사람 수입니다."},
    {"name": "I0", "label": "처음 감염자 수", "type": "float", "default": 10, "min": 1, "max": 1e9,
     "tip": "0일째에 이미 감염된 사람 수입니다."},
    {"name": "beta", "label": "전파율 (beta)", "type": "float", "default": 0.3, "min": 0, "max": 5, "step": 0.01,
     "tip": "감염자 한 명이 하루에 병을 옮기는 정도입니다. 클수록 빨리 퍼집니다. 거리두기·마스크는 이 값을 낮춥니다."},
    {"name": "gamma", "label": "회복률 (gamma)", "type": "float", "default": 0.1, "min": 0.001, "max": 1, "step": 0.01,
     "tip": "감염자가 하루에 회복(또는 격리)되는 비율입니다. 0.1이면 평균 10일 동안 전염시킬 수 있습니다(1 ÷ 0.1)."},
    {"name": "days", "label": "시뮬레이션 기간(일)", "type": "int", "default": 180, "min": 10, "max": 1000,
     "tip": "며칠 동안의 변화를 계산할지 정합니다."},
]

MODELS = {
    "SIR": {
        "title": "SIR 모델",
        "desc": "사람을 감염 가능(S), 감염(I), 회복(R) 세 그룹으로 나눕니다. 감염 가능한 사람이 감염자를 만나면 감염되고, 감염자는 일정 비율로 회복합니다. 가장 기본적인 전염병 모델입니다.",
        "params": COMMON,
        "lines": ["감염 가능 (S)", "감염 (I)", "회복 (R)"],
    },
    "SEIR": {
        "title": "SEIR 모델",
        "desc": "SIR에 '잠복기(E)' 그룹을 더한 모델입니다. 감염됐지만 아직 남에게 옮기지 않는 기간을 반영해서, 확산이 SIR보다 조금 늦게 나타납니다.",
        "params": COMMON + [
            {"name": "sigma", "label": "발병률 (sigma)", "type": "float", "default": 0.2, "min": 0.001, "max": 1, "step": 0.01,
             "tip": "잠복기 사람이 하루에 감염자(전파 가능)로 바뀌는 비율입니다. 0.2면 평균 잠복기 5일입니다(1 ÷ 0.2)."},
        ],
        "lines": ["감염 가능 (S)", "잠복 (E)", "감염 (I)", "회복 (R)"],
    },
    "SEIRCM": {
        "title": "SEIRCM 모델 (확진·사망·방역 정책)",
        "desc": "SEIR에 누적 확진자(C)와 누적 사망자(M)를 더하고, 특정 날부터 방역 정책으로 전파율이 줄어드는 효과까지 넣은 모델입니다. 코로나19 초기 연구에서 쓰인 구조입니다.",
        "params": [p for p in COMMON] + [
            {"name": "sigma", "label": "발병률 (sigma)", "type": "float", "default": 0.2, "min": 0.001, "max": 1, "step": 0.01,
             "tip": "잠복기 사람이 하루에 감염자로 바뀌는 비율입니다."},
            {"name": "epsilon", "label": "치명률 (epsilon)", "type": "float", "default": 0.01, "min": 0, "max": 1, "step": 0.001,
             "tip": "감염에서 벗어나는 사람 중 사망하는 비율입니다. 0.01이면 1%입니다."},
            {"name": "T", "label": "방역 시작일 (0=없음)", "type": "int", "default": 30, "min": 0, "max": 1000,
             "tip": "며칠째부터 방역 정책(거리두기 등)을 시작할지 정합니다. 0이면 방역 없이 계산합니다."},
            {"name": "eta", "label": "방역 효과 (eta)", "type": "float", "default": 0.5, "min": 0, "max": 1, "step": 0.05,
             "tip": "방역 시작 후 전파율이 점차 원래의 몇 배로 줄어드는지입니다. 0.5면 절반으로 줄어듭니다."},
        ],
        "lines": ["감염 가능 (S)", "잠복 (E)", "감염 (I)", "회복 (R)", "누적 확진 (C)", "누적 사망 (M)"],
    },
}


def simulate(model: str, p: dict, fit_demo: bool = False) -> dict:
    spec = MODELS[model]
    N, I0, beta, gamma, days = float(p["N"]), float(p["I0"]), float(p["beta"]), float(p["gamma"]), int(p["days"])
    t = np.arange(days)
    if model == "SIR":
        cls, init, params = SIR, [N - I0, I0, 0], (beta, gamma, N)
    elif model == "SEIR":
        cls, init, params = SEIR, [N - I0, 0, I0, 0], (beta, gamma, float(p["sigma"]), N)
    else:
        cls = SEIRCM
        init = [N - I0, 0, I0, 0, I0, 0]
        params = (beta, gamma, float(p["sigma"]), float(p["eta"]), float(p["epsilon"]), float(p["T"]))
    em = EpidemicModel(cls)
    sol = em.solve(t, init, params)

    infected_idx = spec["lines"].index("감염 (I)")
    peak_day = int(np.argmax(sol[:, infected_idx]))
    out = {
        "title": spec["title"],
        "days": t.tolist(),
        "lines": [{"name": n, "values": np.round(sol[:, i], 2).tolist()} for i, n in enumerate(spec["lines"])],
        "r0": beta / gamma,
        "peak_day": peak_day,
        "peak_infected": float(sol[peak_day, infected_idx]),
        "total_infected_pct": float((N - sol[-1, 0]) / N * 100),
    }
    if model == "SEIRCM":
        out["deaths"] = float(sol[-1, 5])

    if fit_demo and model == "SIR":
        # gs_quant EpidemicModel.fit 시연: 정답 파라미터로 만든 곡선에 잡음을 섞고, 잡음 낀 '관측치'만 보고 beta·gamma를 다시 추정한다
        rng = np.random.default_rng(0)
        noisy = sol * (1 + rng.normal(0, 0.05, sol.shape))
        noisy[:, 1] = np.maximum(noisy[:, 1], 0)
        parameters, initial_conditions = SIR.get_parameters(N - I0, I0, 0, N, beta=0.5, gamma=0.2)
        fitted = EpidemicModel(SIR, parameters=parameters, data=noisy, initial_conditions=initial_conditions)
        fitted.fit(verbose=False)
        fp = fitted.fitted_parameters
        out["fit"] = {
            "beta": float(getattr(fp["beta"], "value", fp["beta"])), "gamma": float(getattr(fp["gamma"], "value", fp["gamma"])),
            "observed": np.round(noisy[:, 1], 2).tolist(),
        }
    return out


def catalog():
    return {k: {"title": v["title"], "desc": v["desc"], "params": v["params"]} for k, v in MODELS.items()}
