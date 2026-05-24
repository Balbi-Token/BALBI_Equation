# app.py
# Equação de Balbi - Calculadora Profissional
# Versão fiel à calculadora HTML
# Autor: Vinícius Cabral Balbi

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import io
import base64
import math
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

st.set_page_config(
    page_title="Equação de Balbi - Calculadora",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS para deixar igual ao HTML
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #003366 0%, #0066cc 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .card-resultado {
        background: #e6f0ff;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .resultado-grande {
        font-size: 2rem;
        font-weight: bold;
        color: #006400;
        text-align: center;
    }
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-laminar { background: #87CEEB; color: #003366; }
    .badge-transicao { background: #FFD700; color: #333; }
    .badge-turbulento { background: #DC143C; color: white; }
</style>
""", unsafe_allow_html=True)

# ==================== FUNÇÕES DE CÁLCULO (IGUAIS AO HTML) ====================

def calcular_dh_e_area(tipo, diametro, largura, altura):
    if tipo == "Circular":
        d = diametro / 1000
        area = math.pi * (d ** 2) / 4
        perim = math.pi * d
        dh = d
    else:
        B = largura / 1000
        H = altura / 1000
        area = B * H
        perim = 2 * (B + H)
        dh = 4 * area / perim
    return area, perim, dh

def resolver_colebrook(re, rug_rel):
    if re < 2300:
        return 64 / re
    f = 0.02
    for _ in range(30):
        arg = rug_rel / 3.7 + 2.51 / (re * math.sqrt(f))
        f_new = 1 / (-2 * math.log10(arg)) ** 2
        if abs(f_new - f) < 1e-6:
            return f_new
        f = f_new
    return f

def calcular():
    tipo = st.session_state.tipo
    comprimento = st.session_state.comprimento
    vazao = st.session_state.vazao
    rugosidade_mm = st.session_state.rugosidade_mm
    
    if tipo == "Circular":
        diametro = st.session_state.diametro
        largura = None
        altura = None
    else:
        diametro = None
        largura = st.session_state.largura
        altura = st.session_state.altura
    
    area, perim, dh = calcular_dh_e_area(tipo, diametro, largura, altura)
    raio = dh / 2
    
    vm = (vazao / 3600) / area
    nu = 0.0000150
    mu = 0.0000181
    rho = 1.20
    re = (vm * dh) / nu if vm > 0 else 0
    
    # Fator de regime α
    alfa = 1 + 1 / (1 + (re / 2800) ** 4)
    
    # Velocidade de pico
    relacao_vmax = 1.08474
    vmax = vm * relacao_vmax
    
    # k_Balbi
    if re <= 2000:
        k_balbi = raio / (nu / vm) if vm > 0 else 1
    elif re <= 4000:
        k_lam = raio / (nu / vm) if vm > 0 else 1
        k_turb = 0.042 * (re ** 0.25) * ((rugosidade_mm/1000 / dh) ** 0.1)
        f = (re - 2000) / 2000
        k_balbi = k_lam * (1 - f) + k_turb * f
    else:
        k_balbi = 0.042 * (re ** 0.25) * ((rugosidade_mm/1000 / dh) ** 0.1)
        if k_balbi < 0.1:
            k_balbi = 0.1
        k_max = raio / (nu / vm) if vm > 0 else 1e6
        if k_balbi > k_max:
            k_balbi = k_max
    
    lambda_m = (nu / vm) * k_balbi if vm > 0 else 0
    dpl_balbi = ((2 * mu * vmax * alfa) / (raio * lambda_m)) / 1000 if raio > 0 and lambda_m > 0 else 0
    
    # Colebrook-White
    rug_rel = (rugosidade_mm/1000) / dh
    f_cole = resolver_colebrook(re, rug_rel)
    dpl_cole = f_cole * (rho / 2) * (vm ** 2 / dh) if dh > 0 else 0
    
    # Equal Friction
    equal_friction = st.session_state.equal_friction
    dpl_ef = equal_friction
    
    # Static Regain
    v0 = st.session_state.v0
    eta = st.session_state.eta
    if vm > 0 and v0 > vm:
        dpl_sr = (rho / 2) * (v0**2 - vm**2) * (1 - eta/100) / comprimento
        dpl_sr = max(dpl_sr, 0)
    else:
        dpl_sr = 0
    
    # Salvar nos session_state
    st.session_state.dh = dh
    st.session_state.vm = vm
    st.session_state.re = re
    st.session_state.alfa = alfa
    st.session_state.k_balbi = k_balbi
    st.session_state.lambda_m = lambda_m
    st.session_state.dpl_balbi = dpl_balbi
    st.session_state.dpl_cole = dpl_cole
    st.session_state.dpl_ef = dpl_ef
    st.session_state.dpl_sr = dpl_sr
    st.session_state.area = area
    st.session_state.perim = perim
    st.session_state.raio = raio
    st.session_state.vmax = vmax
    st.session_state.regime = re

# ==================== INTERFACE ====================

st.markdown("""
<div class="main-header">
    <h1>🏆 Calculadora da Equação de Balbi</h1>
    <p>Método Explícito Unificado para Perda de Carga em Dutos</p>
    <p style="font-size:0.85rem;">Vinícius Cabral Balbi | ASHRAE Member</p>
</div>
""", unsafe_allow_html=True)

# Sidebar - EXATAMENTE os mesmos campos do HTML
with st.sidebar:
    st.markdown("### 📐 Entradas Geométricas")
    
    tipo = st.selectbox("Tipo de Duto", ["Retangular", "Circular"], key="tipo")
    
    if tipo == "Circular":
        diametro = st.number_input("Diâmetro (mm)", min_value=50, max_value=2000, value=500, key="diametro")
        largura = altura = None
    else:
        col1, col2 = st.columns(2)
        with col1:
            largura = st.number_input("Largura (mm)", min_value=50, max_value=2000, value=500, key="largura")
        with col2:
            altura = st.number_input("Altura (mm)", min_value=50, max_value=2000, value=300, key="altura")
        diametro = None
    
    comprimento = st.number_input("Comprimento L (m)", min_value=0.5, max_value=100.0, value=2.0, key="comprimento")
    vazao = st.number_input("Vazão Q (m³/h)", min_value=10, max_value=50000, value=2100, key="vazao")
    
    st.markdown("---")
    st.markdown("### 🧪 Condição da Parede")
    
    rug_preset = st.selectbox("Material", [
        "Chapa Galvanizada (ε = 0,15 mm)",
        "Duto Liso (ε = 0,0015 mm)",
        "Duto Rugoso (ε = 1,5 mm)"
    ], key="rug_preset")
    
    if rug_preset == "Chapa Galvanizada (ε = 0,15 mm)":
        rugosidade_mm = 0.15
    elif rug_preset == "Duto Liso (ε = 0,0015 mm)":
        rugosidade_mm = 0.0015
    else:
        rugosidade_mm = 1.5
    
    st.session_state.rugosidade_mm = rugosidade_mm
    
    st.markdown("---")
    st.markdown("### 🔧 Métodos Comparativos")
    
    equal_friction = st.number_input("Equal Friction - ΔP/L fixo (Pa/m)", value=0.5, step=0.1, key="equal_friction")
    v0 = st.number_input("Static Regain - Velocidade anterior v₀ (m/s)", value=4.0, step=0.5, key="v0")
    eta = st.slider("Static Regain - Eficiência η (%)", 50, 95, 75, key="eta")
    
    if st.button("🔄 Calcular", use_container_width=True):
        calcular()

# Inicializar session_state
if "dh" not in st.session_state:
    calcular()

# ==================== EXIBIÇÃO DOS RESULTADOS ====================

# Badge de regime
if st.session_state.re <= 2000:
    badge_class = "badge-laminar"
    regime_text = "Laminar Clássico"
elif st.session_state.re <= 4000:
    badge_class = "badge-transicao"
    regime_text = "Transição Crítica"
else:
    badge_class = "badge-turbulento"
    regime_text = "Turbulento Industrial"

st.markdown(f"""
<div style="text-align:center; margin: 10px 0;">
    <span class="badge {badge_class}">{regime_text} (Re = {st.session_state.re:,.0f})</span>
</div>
""", unsafe_allow_html=True)

# Cards de resultados principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Diâmetro Hidráulico D_h", f"{st.session_state.dh:.4f} m")
with col2:
    st.metric("Velocidade Média v_m", f"{st.session_state.vm:.2f} m/s")
with col3:
    st.metric("Número de Reynolds", f"{st.session_state.re:,.0f}")
with col4:
    st.metric("Fator de Regime α", f"{st.session_state.alfa:.4f}")

st.markdown("---")

# Resultados de perda de carga
col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    <div class="card-resultado">
        <div class="resultado-grande">{st.session_state.dpl_balbi:.4f}</div>
        <div style="text-align:center;"><strong>🏆 Equação de Balbi</strong> ΔP/L (Pa/m)</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="card-resultado">
        <div class="resultado-grande" style="color:#003366;">{st.session_state.dpl_cole:.4f}</div>
        <div style="text-align:center;"><strong>Colebrook-White</strong> ΔP/L (Pa/m)</div>
    </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    <div class="card-resultado">
        <div><strong>Equal Friction</strong> ΔP/L = {st.session_state.dpl_ef:.4f} Pa/m</div>
        <div style="font-size:0.8rem; color:#666;">⚠️ Arbitrário - NÃO considera rugosidade, vazão ou geometria</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="card-resultado">
        <div><strong>Static Regain</strong> ΔP/L = {st.session_state.dpl_sr:.4f} Pa/m</div>
        <div style="font-size:0.8rem; color:#666;">Empírico - depende de v₀={v0} m/s, η={eta}%</div>
    </div>
    """, unsafe_allow_html=True)

# ==================== GRÁFICO DE PERFIL DE VELOCIDADES (CORRETO) ====================
st.markdown("---")
st.markdown("## 📈 Perfil de Velocidades")

R = st.session_state.raio
lambda_m = st.session_state.lambda_m
alfa = st.session_state.alfa
vmax = st.session_state.vmax
vm = st.session_state.vm

# Gerar pontos para o gráfico
r_values = np.linspace(0, R, 100)
dist_parede = R - r_values

# Perfil da Equação de Balbi (EXPONENCIAL, com cantos arredondados)
termo_exp = np.power(dist_parede / lambda_m, alfa)
u_balbi = vmax * (1 - np.exp(-termo_exp))
# Garantir que na parede seja zero
u_balbi[r_values >= R*0.99] = 0

# Perfil de potência 1/7 (Nikuradse)
u_cole = vmax * np.power(dist_parede / R, 1/7)
u_cole = np.where(dist_parede > 0, u_cole, 0)
u_cole = np.clip(u_cole, 0, vmax)

# Perfil laminar (parabólico) - só para referência
u_lam = 2 * vm * (1 - (r_values/R)**2)

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=r_values, y=u_balbi,
    mode='lines',
    name='Equação de Balbi',
    line=dict(color='#006400', width=3),
    fill='tozeroy',
    fillcolor='rgba(0,100,0,0.1)'
))

fig.add_trace(go.Scatter(
    x=r_values, y=u_cole,
    mode='lines',
    name='Lei de Potência 1/7 (Nikuradse)',
    line=dict(color='#003366', width=2, dash='dash')
))

if st.session_state.re <= 2000:
    fig.add_trace(go.Scatter(
        x=r_values, y=u_lam,
        mode='lines',
        name='Perfil Laminar (Poiseuille)',
        line=dict(color='#888', width=2, dash='dot')
    ))

# Espelhar para o lado negativo (visualização completa do duto)
r_neg = -r_values[::-1]
u_balbi_neg = u_balbi[::-1]
u_cole_neg = u_cole[::-1]
u_lam_neg = u_lam[::-1]

# Adicionar versões espelhadas
fig.add_trace(go.Scatter(
    x=r_neg, y=u_balbi_neg,
    mode='lines',
    name='_espelho_balbi',
    line=dict(color='#006400', width=3),
    fill='tozeroy',
    fillcolor='rgba(0,100,0,0.1)',
    showlegend=False
))

fig.add_trace(go.Scatter(
    x=r_neg, y=u_cole_neg,
    mode='lines',
    name='_espelho_cole',
    line=dict(color='#003366', width=2, dash='dash'),
    showlegend=False
))

fig.update_layout(
    title=f"Perfil de Velocidades - {tipo} {f'Ø{diametro}mm' if tipo=='Circular' else f'{largura}×{altura}mm'}",
    xaxis_title="Posição Radial (m)",
    yaxis_title="Velocidade u(r) (m/s)",
    height=450,
    template="plotly_white",
    hovermode="x unified",
    showlegend=True,
    xaxis=dict(
        tickmode='array',
        tickvals=[-R, 0, R],
        ticktext=[f"-{R:.3f}", "0", f"{R:.3f}"]
    )
)

st.plotly_chart(fig, use_container_width=True)

# ==================== GRÁFICO DE BARRAS ====================
st.markdown("---")
st.markdown("## 📊 Comparação entre Métodos")

fig_bar = go.Figure(data=[
    go.Bar(
        x=['Equação de Balbi', 'Colebrook-White', 'Static Regain', 'Equal Friction'],
        y=[st.session_state.dpl_balbi, st.session_state.dpl_cole, st.session_state.dpl_sr, st.session_state.dpl_ef],
        marker_color=['#006400', '#003366', '#ff8c00', '#cc0000'],
        text=[f"{st.session_state.dpl_balbi:.4f}", f"{st.session_state.dpl_cole:.4f}", f"{st.session_state.dpl_sr:.4f}", f"{st.session_state.dpl_ef:.4f}"],
        textposition='outside'
    )
])

fig_bar.update_layout(
    title="Perda de Carga Distribuída ΔP/L (Pa/m)",
    yaxis_title="ΔP/L (Pa/m)",
    height=400,
    template="plotly_white"
)

st.plotly_chart(fig_bar, use_container_width=True)

# ==================== TABELA DE PARÂMETROS ====================
with st.expander("🔬 Ver detalhes dos parâmetros da Equação de Balbi"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        **Parâmetros geométricos:**
        - Área A = {st.session_state.area:.6f} m²
        - Perímetro P = {st.session_state.perim:.6f} m
        - D_h = {st.session_state.dh:.6f} m
        - Raio R = {st.session_state.raio:.6f} m
        
        **Parâmetros do escoamento:**
        - v_m = {st.session_state.vm:.4f} m/s
        - Re = {st.session_state.re:.0f}
        - α = {st.session_state.alfa:.6f}
        - v_max = {st.session_state.vmax:.4f} m/s
        """)
    with col2:
        st.markdown(f"""
        **Parâmetros característicos:**
        - k_Balbi = {st.session_state.k_balbi:.6f}
        - λ = {st.session_state.lambda_m:.3e} m = {st.session_state.lambda_m*1e6:.3f} μm
        
        **Perda de carga:**
        - ΔP/L = {st.session_state.dpl_balbi:.6f} Pa/m
        - ΔP total = {st.session_state.dpl_balbi * comprimento:.6f} Pa
        
        **Relação Balbi vs Colebrook:**
        - Diferença = {((st.session_state.dpl_balbi - st.session_state.dpl_cole) / st.session_state.dpl_cole * 100) if st.session_state.dpl_cole > 0 else 0:.1f}%
        """)

# ==================== GERAR PDF ====================
st.markdown("---")

def gerar_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    story = []
    story.append(Paragraph("MEMORIAL DE CÁLCULO", styles['Title']))
    story.append(Paragraph("<b>EQUAÇÃO DE BALBI</b>", styles['Heading2']))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 10*mm))
    
    story.append(Paragraph("1. DADOS DE ENTRADA", styles['Heading2']))
    dados = [
        ["Tipo", tipo],
        ["Dimensões", f"{diametro if tipo=='Circular' else f'{largura}×{altura}'} mm"],
        ["Comprimento", f"{comprimento} m"],
        ["Vazão", f"{vazao} m³/h"],
        ["Rugosidade", f"{rugosidade_mm} mm"],
    ]
    for d in dados:
        story.append(Paragraph(f"• {d[0]}: {d[1]}", styles['Normal']))
    story.append(Spacer(1, 5*mm))
    
    story.append(Paragraph("2. RESULTADOS", styles['Heading2']))
    story.append(Paragraph(f"🏆 Equação de Balbi ΔP/L = {st.session_state.dpl_balbi:.6f} Pa/m", styles['Normal']))
    story.append(Paragraph(f"Colebrook-White ΔP/L = {st.session_state.dpl_cole:.6f} Pa/m", styles['Normal']))
    story.append(Paragraph(f"Static Regain ΔP/L = {st.session_state.dpl_sr:.6f} Pa/m", styles['Normal']))
    story.append(Paragraph(f"Equal Friction ΔP/L = {st.session_state.dpl_ef:.6f} Pa/m", styles['Normal']))
    story.append(Spacer(1, 10*mm))
    
    story.append(Paragraph("3. PARÂMETROS CARACTERÍSTICOS", styles['Heading2']))
    story.append(Paragraph(f"k_Balbi = {st.session_state.k_balbi:.6f}", styles['Normal']))
    story.append(Paragraph(f"λ = {st.session_state.lambda_m:.3e} m", styles['Normal']))
    story.append(Paragraph(f"α = {st.session_state.alfa:.6f}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

if st.button("📄 Gerar Memorial PDF", use_container_width=True):
    pdf_bytes = gerar_pdf()
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="memorial_balbi.pdf">📥 Clique para baixar o PDF</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.success("PDF gerado com sucesso!")

# Rodapé
st.markdown("""
---
<div style="text-align:center; font-size:0.75rem; color:#999;">
    <p><strong>📐 Fórmulas da Equação de Balbi</strong></p>
    <p>λ = (ν / v_m) × k_Balbi | ΔP/L = (2 × μ × v_max × α) / (R × λ) / 1000</p>
    <p>k_Balbi = 0,042 × Re^0,25 × (ε / D_h)^0,1 (Regime Turbulento Industrial) | α(Re) = 1 + 1 / [1 + (Re/2800)⁴]</p>
    <p>© 2025 Equação de Balbi · Vinícius Cabral Balbi · ASHRAE Member</p>
</div>
""", unsafe_allow_html=True)
