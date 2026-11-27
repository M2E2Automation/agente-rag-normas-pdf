from seguranca_rag import validar_expressao_matematica_segura
import math
import numpy as np
import sympy as sp
from scipy import constants, integrate

def resolver_calculo_simbolico(expressao: str, variavel: str = "x", operacao: str = "simplificar") -> str:
    """Executa algebra, derivadas, integrais e resolucao de equacoes via SymPy."""
    x = sp.Symbol(variavel)
    expr_segura = validar_expressao_matematica_segura(expressao)
    expr = sp.sympify(expr_segura)
    if operacao == "derivar":
        res = sp.diff(expr, x)
    elif operacao == "integrar":
        res = sp.integrate(expr, x)
    elif operacao == "resolver":
        res = sp.solve(expr, x)
    else:
        res = sp.simplify(expr)
    return str(res)

def dimensao_fractal_auto_similar(n_partes: int, fator_escala: float) -> float:
    """Calcula a dimensao fractal de Hausdorff D = log(N) / log(1/r) para redes ramificadas/porosas."""
    if n_partes <= 1 or fator_escala <= 0 or fator_escala >= 1:
        raise ValueError("Parametros invalidos: requer N > 1 e 0 < r < 1.")
    return round(math.log(n_partes) / math.log(1.0 / fator_escala), 4)

def fluido_golpe_ariete_joukowsky(densidade_kg_m3: float, celeridade_onda_m_s: float, delta_v_m_s: float) -> dict:
    """Calcula a sobrepressao de golpe de ariete dP = rho * c * dV."""
    dp_pa = densidade_kg_m3 * celeridade_onda_m_s * abs(delta_v_m_s)
    dp_mca = dp_pa / (densidade_kg_m3 * constants.g)
    return {"sobrepressao_kpa": round(dp_pa / 1000.0, 2), "sobrepressao_mca": round(dp_mca, 2)}

def termo_armazenamento_latente_sensivel(
    massa_kg: float,
    cp_kj_kgk: float,
    delta_t_k: float,
    calor_latente_kj_kg: float = 0.0,
) -> dict:
    """Calcula energia termica armazenada (sensivel + latente PCM/gelo) em kWh termicos."""
    q_sensivel_kj = massa_kg * cp_kj_kgk * abs(delta_t_k)
    q_latente_kj = massa_kg * max(0.0, calor_latente_kj_kg)
    q_total_kwh = (q_sensivel_kj + q_latente_kj) / 3600.0
    return {
        "energia_sensivel_kwh": round(q_sensivel_kj / 3600.0, 2),
        "energia_latente_kwh": round(q_latente_kj / 3600.0, 2),
        "energia_total_kwh_termico": round(q_total_kwh, 2),
    }

def eletromag_profundidade_pelicular(frequencia_hz: float, resistividade_ohm_m: float = 1.72e-8, mu_r: float = 1.0) -> float:
    """Calcula a profundidade pelicular (skin depth) em mm para condutores em corrente alternada."""
    omega = 2.0 * math.pi * frequencia_hz
    mu = constants.mu_0 * mu_r
    delta_m = math.sqrt((2.0 * resistividade_ohm_m) / (omega * mu))
    return round(delta_m * 1000.0, 4)

def dimensionar_bess_energia_limpa(
    demanda_diaria_kwh: float,
    dias_autonomia: float = 1.0,
    dod_max: float = 0.85,
    eficiencia_roundtrip: float = 0.92,
) -> dict:
    """Dimensiona banco de baterias (BESS LFP) para eletrificacao e armazenamento de energia limpa."""
    capacidade_nominal_kwh = (demanda_diaria_kwh * dias_autonomia) / (dod_max * eficiencia_roundtrip)
    return {
        "capacidade_nominal_bess_kwh": round(capacidade_nominal_kwh, 2),
        "energia_util_kwh": round(demanda_diaria_kwh * dias_autonomia, 2),
        "perdas_ciclo_kwh": round(capacidade_nominal_kwh * (1.0 - eficiencia_roundtrip), 2),
    }
