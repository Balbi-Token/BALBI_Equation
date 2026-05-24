# balbi_core.py
# Autor: Vinícius Cabral Balbi
# Núcleo de cálculos da Equação de Balbi e métodos comparativos

import math
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, Dict

class TipoDuto(Enum):
    CIRCULAR = "Circular"
    RETANGULAR = "Retangular"

class Regime(Enum):
    LAMINAR = "Laminar"
    TRANSICAO = "Transição"
    TURBULENTO = "Turbulento Industrial"
    TURBULENTO_ALTA_VEL = "Turbulento Alta Velocidade"

@dataclass
class Duto:
    tipo: TipoDuto
    diametro_mm: float = None
    largura_mm: float = None
    altura_mm: float = None
    comprimento_m: float = 1.0
    rugosidade_absoluta_mm: float = 0.15
    c_base: float = 0.042  # Para dutos rígidos lisos (padrão)

@dataclass
class Fluido:
    nome: str = "Ar Padrão (20°C, 1 atm)"
    rho_kg_m3: float = 1.20
    mu_pa_s: float = 1.81e-5
    nu_m2_s: float = 1.50e-5  # mu/rho
    fator_vmax_vm_turb: float = 1.08474

@dataclass
class ResultadoBalbi:
    """Resultados completos da Equação de Balbi"""
    area_m2: float
    perimetro_m: float
    dh_m: float
    raio_m: float
    vm_ms: float
    re: float
    regime: Regime
    alfa: float
    vmax_ms: float
    k_balbi: float
    lambda_m: float
    dpl_pa_m: float
    dp_total_pa: float

@dataclass
class ResultadoComparativo:
    """Resultados de todos os métodos comparados"""
    balbi_pa_m: float
    colebrook_pa_m: float
    static_regain_pa_m: float
    equal_friction_pa_m: float
    zhang_sarica_pa_m: float
    metodos_dict: Dict[str, float]

def calcular_dh_e_area(duto: Duto) -> Tuple[float, float, float]:
    """Retorna (area_m2, perimetro_m, dh_m)"""
    if duto.tipo == TipoDuto.CIRCULAR:
        d = duto.diametro_mm / 1000.0
        area = math.pi * (d ** 2) / 4.0
        perim = math.pi * d
        dh = d
    else:
        B = duto.largura_mm / 1000.0
        H = duto.altura_mm / 1000.0
        area = B * H
        perim = 2.0 * (B + H)
        dh = 4.0 * area / perim
    return area, perim, dh

def calcular_regime(re: float) -> Regime:
    if re <= 2000:
        return Regime.LAMINAR
    elif re <= 4000:
        return Regime.TRANSICAO
    elif re <= 200000:
        return Regime.TURBULENTO
    else:
        return Regime.TURBULENTO_ALTA_VEL

def calcular_alfa(re: float) -> float:
    """Fator de regime contínuo α(Re) - Equação de Balbi"""
    return 1.0 + 1.0 / (1.0 + (re / 2800.0) ** 4)

def calcular_k_balbi(re: float, rugosidade_m: float, dh_m: float, raio_m: float, 
                     nu_m2_s: float, vm_ms: float, regime: Regime, c_base: float = 0.042) -> float:
    """Calcula k_Balbi conforme a faixa de regime"""
    if regime == Regime.LAMINAR:
        return raio_m / (nu_m2_s / vm_ms)
    elif regime == Regime.TRANSICAO:
        k_lam = raio_m / (nu_m2_s / vm_ms)
        k_turb = c_base * (re ** 0.25) * ((rugosidade_m / dh_m) ** 0.1)
        f = (re - 2000) / 2000.0
        f = max(0.0, min(1.0, f))
        return k_lam * (1 - f) + k_turb * f
    elif regime == Regime.TURBULENTO:
        k = c_base * (re ** 0.25) * ((rugosidade_m / dh_m) ** 0.1)
        k = max(k, 0.1)
        k_max = raio_m / (nu_m2_s / vm_ms) if vm_ms > 0 else 1e6
        return min(k, k_max)
    else:
        return 0.8

def calcular_equacao_balbi(duto: Duto, fluido: Fluido, vazao_m3h: float) -> ResultadoBalbi:
    """Função principal da Equação de Balbi"""
    area, perim, dh = calcular_dh_e_area(duto)
    raio = dh / 2.0
    
    vazao_m3s = vazao_m3h / 3600.0
    vm = vazao_m3s / area if area > 0 else 0
    
    re = (vm * dh) / fluido.nu_m2_s if vm > 0 and dh > 0 else 0
    
    regime = calcular_regime(re)
    alfa = calcular_alfa(re)
    
    # Velocidade de pico
    if regime == Regime.LAMINAR:
        vmax = 2.0 * vm
    elif regime == Regime.TRANSICAO:
        f = (re - 2000) / 2000.0
        f = max(0.0, min(1.0, f))
        razao = 2.0 * (1 - f) + fluido.fator_vmax_vm_turb * f
        vmax = vm * razao
    else:
        vmax = vm * fluido.fator_vmax_vm_turb
    
    rug_m = duto.rugosidade_absoluta_mm / 1000.0
    k_balbi = calcular_k_balbi(re, rug_m, dh, raio, fluido.nu_m2_s, vm, regime, duto.c_base)
    
    lambda_m = (fluido.nu_m2_s / vm) * k_balbi if vm > 0 else 0
    
    if raio > 0 and lambda_m > 0:
        dpl_pa_m = (2.0 * fluido.mu_pa_s * vmax * alfa) / (raio * lambda_m) / 1000.0
    else:
        dpl_pa_m = 0
    
    dp_total = dpl_pa_m * duto.comprimento_m
    
    return ResultadoBalbi(
        area_m2=area,
        perimetro_m=perim,
        dh_m=dh,
        raio_m=raio,
        vm_ms=vm,
        re=re,
        regime=regime,
        alfa=alfa,
        vmax_ms=vmax,
        k_balbi=k_balbi,
        lambda_m=lambda_m,
        dpl_pa_m=dpl_pa_m,
        dp_total_pa=dp_total
    )

def resolver_colebrook(re: float, rug_relativa: float) -> float:
    """Resolve a equação de Colebrook-White iterativamente"""
    if re < 2300:
        return 64.0 / re
    f = 0.02
    for _ in range(30):
        arg = rug_relativa / 3.7 + 2.51 / (re * math.sqrt(f))
        f_new = 1.0 / (-2.0 * math.log10(arg)) ** 2
        if abs(f_new - f) < 1e-6:
            return f_new
        f = f_new
    return f

def calcular_colebrook(duto: Duto, fluido: Fluido, vazao_m3h: float) -> float:
    """Calcula perda de carga pelo método Colebrook-White (Darcy-Weisbach)"""
    area, _, dh = calcular_dh_e_area(duto)
    vazao_m3s = vazao_m3h / 3600.0
    vm = vazao_m3s / area if area > 0 else 0
    re = (vm * dh) / fluido.nu_m2_s if vm > 0 and dh > 0 else 0
    
    rug_m = duto.rugosidade_absoluta_mm / 1000.0
    rug_rel = rug_m / dh if dh > 0 else 0.001
    
    f = resolver_colebrook(re, rug_rel)
    dpl_pa_m = f * (fluido.rho_kg_m3 / 2.0) * (vm ** 2 / dh) if dh > 0 else 0
    return dpl_pa_m

def calcular_static_regain(duto: Duto, fluido: Fluido, vazao_m3h: float, 
                           v0_ms: float = 4.0, eficiencia_percent: float = 75.0) -> float:
    """Calcula perda de carga pelo método Static Regain"""
    area, _, _ = calcular_dh_e_area(duto)
    vazao_m3s = vazao_m3h / 3600.0
    vm = vazao_m3s / area if area > 0 else 0
    
    if vm > 0 and v0_ms > vm:
        dpl_pa_m = (fluido.rho_kg_m3 / 2.0) * (v0_ms ** 2 - vm ** 2) * (1 - eficiencia_percent / 100.0) / duto.comprimento_m
        return max(dpl_pa_m, 0)
    return 0.0

def calcular_equal_friction(dpl_fixo_pa_m: float = 0.5) -> float:
    """Método Equal Friction - valor arbitrário fixo"""
    return dpl_fixo_pa_m

def calcular_zhang_sarica(resultado_balbi: ResultadoBalbi, fluido: Fluido) -> float:
    """
    Método de Zhang & Sarica (2005) para escoamento multifásico.
    Implementação simplificada baseada na correlação publicada no artigo de Al-Hadhrami et al. 2014.
    Para escoamento monofásico, aproxima-se do fator de atrito de Blasius com correção.
    """
    re = resultado_balbi.re
    if re <= 0:
        return 0
    
    # Correlação simplificada para dutos lisos (Zhang & Sarica)
    # f = 0.316 * Re^(-0.25) para turbulento liso (Blasius)
    # Com correção para rugosidade
    f_zhang = 0.316 * (re ** -0.25)
    
    # Correção empírica para diferentes regimes
    if resultado_balbi.regime == Regime.LAMINAR:
        f_zhang = 64.0 / re
    elif resultado_balbi.regime == Regime.TRANSICAO:
        f_lam = 64.0 / re
        f_turb = 0.316 * (re ** -0.25)
        frac = (re - 2000) / 2000.0
        f_zhang = f_lam * (1 - frac) + f_turb * frac
    
    dpl_pa_m = f_zhang * (fluido.rho_kg_m3 / 2.0) * (resultado_balbi.vm_ms ** 2 / resultado_balbi.dh_m) if resultado_balbi.dh_m > 0 else 0
    return dpl_pa_m

def calcular_comparativo_completo(duto: Duto, fluido: Fluido, vazao_m3h: float,
                                   equal_friction_value: float = 0.5,
                                   static_regain_v0: float = 4.0,
                                   static_regain_eta: float = 75.0) -> ResultadoComparativo:
    """Calcula todos os métodos comparativos"""
    resultado_balbi = calcular_equacao_balbi(duto, fluido, vazao_m3h)
    
    dpl_cole = calcular_colebrook(duto, fluido, vazao_m3h)
    dpl_sr = calcular_static_regain(duto, fluido, vazao_m3h, static_regain_v0, static_regain_eta)
    dpl_ef = calcular_equal_friction(equal_friction_value)
    dpl_zhang = calcular_zhang_sarica(resultado_balbi, fluido)
    
    metodos_dict = {
        "Equação de Balbi": resultado_balbi.dpl_pa_m,
        "Colebrook-White": dpl_cole,
        "Static Regain": dpl_sr,
        "Equal Friction": dpl_ef,
        "Zhang & Sarica (2005)": dpl_zhang
    }
    
    return ResultadoComparativo(
        balbi_pa_m=resultado_balbi.dpl_pa_m,
        colebrook_pa_m=dpl_cole,
        static_regain_pa_m=dpl_sr,
        equal_friction_pa_m=dpl_ef,
        zhang_sarica_pa_m=dpl_zhang,
        metodos_dict=metodos_dict
    )