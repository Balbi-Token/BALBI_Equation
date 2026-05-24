# app.py
# Calculadora da Equação de Balbi - COM MEMORIAL PASSO-A-PASSO
# Autor: Vinícius Cabral Balbi

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math
from datetime import datetime
import io
import base64
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

st.set_page_config(page_title="Calculadora da Equação de Balbi", page_icon="🏆", layout="wide")

st.markdown("""
<style>
    .main-header { background: linear-gradient(135deg, #003366 0%, #0066cc 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center; margin-bottom: 2rem; }
    .resultado { background: #e6f0ff; padding: 18px; border-radius: 8px; line-height: 1.9; }
    .resultado-grande { font-size: 2rem; font-weight: bold; color: #006400; text-align: center; }
    .green { color: #006400; font-weight: bold; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .badge-laminar { background: #87CEEB; color: #003366; }
    .badge-transicao { background: #FFD700; color: #333; }
    .badge-turbulento { background: #DC143C; color: white; }
    .footer { text-align: center; margin-top: 30px; font-size: 12px; color: #666; border-top: 1px solid #ddd; padding-top: 20px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🏆 Calculadora da Equação de Balbi</h1>
    <p>Método Explícito Unificado para Perda de Carga em Dutos</p>
</div>
""", unsafe_allow_html=True)

# ==================== FUNÇÕES ====================

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

# ==================== SIDEBAR ====================

with st.sidebar:
    st.markdown("### 📐 Entradas Geométricas")
    
    tipo = st.selectbox("Tipo de Duto", ["Retangular", "Circular"])
    
    if tipo == "Circular":
        diametro = st.number_input("Diâmetro Interno (mm)", value=500)
        largura = altura = None
    else:
        col1, col2 = st.columns(2)
        with col1:
            largura = st.number_input("Largura (mm)", value=500)
        with col2:
            altura = st.number_input("Altura (mm)", value=300)
        diametro = None
    
    comprimento = st.number_input("Comprimento do Duto L (m)", value=2.0)
    vazao = st.number_input("Vazão Q (m³/h)", value=2100)
    
    st.markdown("---")
    st.markdown("### 🔧 Métodos Empíricos (Comparação)")
    
    equal_friction = st.number_input("Equal Friction - ΔP/L fixo (Pa/m)", value=0.5)
    static_v0 = st.number_input("Static Regain - Velocidade anterior v₀ (m/s)", value=4.0)
    static_eta = st.slider("Static Regain - Eficiência η (%)", 50, 95, 75)
    
    st.markdown("---")
    st.markdown("### 🧪 Condição da Parede")
    
    rug_preset = st.selectbox("Condição da Parede", [
        "Duto Liso (ε ≈ 0,0015 mm)",
        "Chapa Galvanizada (ε = 0,15 mm)",
        "Duto Rugoso (ε = 1,5 mm)"
    ])
    
    if rug_preset == "Duto Liso (ε ≈ 0,0015 mm)":
        rugosidade_mm = 0.0015
    elif rug_preset == "Chapa Galvanizada (ε = 0,15 mm)":
        rugosidade_mm = 0.15
    else:
        rugosidade_mm = 1.5
    
    st.markdown("---")
    st.markdown("### 🌡️ Propriedades do Fluido (Ar Padrão)")
    
    nu = st.number_input("Viscosidade Cinemática ν (m²/s)", value=0.0000150, format="%.7f")
    mu = st.number_input("Viscosidade Dinâmica μ (Pa·s)", value=0.0000181, format="%.7f")
    rho = st.number_input("Massa Específica ρ (kg/m³)", value=1.20, format="%.2f")
    relacao_vmax = st.number_input("Fator v_max / v_m (turbulento)", value=1.08474, format="%.5f")

# ==================== CÁLCULOS ====================

if tipo == "Circular":
    d = diametro / 1000
    area = math.pi * d**2 / 4
    perim = math.pi * d
    dh = d
    dimensao_text = f"Ø {diametro} mm"
else:
    B = largura / 1000
    H = altura / 1000
    area = B * H
    perim = 2 * (B + H)
    dh = 4 * area / perim
    dimensao_text = f"{largura} × {altura} mm"

raio = dh / 2
vm = (vazao / 3600) / area
re = (vm * dh) / nu if vm > 0 else 0

# Fator de regime α
alfa = 1 + 1 / (1 + (re / 2800) ** 4)

# Velocidade de pico
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
    k_balbi = max(k_balbi, 0.1)
    k_max = raio / (nu / vm) if vm > 0 else 1e6
    k_balbi = min(k_balbi, k_max)

lambda_m = (nu / vm) * k_balbi if vm > 0 else 0
dpl_balbi = ((2 * mu * vmax * alfa) / (raio * lambda_m)) / 1000 if raio > 0 and lambda_m > 0 else 0

# Colebrook
rug_rel = (rugosidade_mm/1000) / dh if dh > 0 else 0.001
f_cole = resolver_colebrook(re, rug_rel)
dpl_cole = f_cole * (rho / 2) * (vm ** 2 / dh) if dh > 0 else 0

# Equal Friction
dpl_ef = equal_friction

# Static Regain
if vm > 0 and static_v0 > vm:
    dpl_sr = (rho / 2) * (static_v0**2 - vm**2) * (1 - static_eta/100) / comprimento
    dpl_sr = max(dpl_sr, 0)
else:
    dpl_sr = 0

# Badge
if re <= 2000:
    badge_class = "badge-laminar"
    regime_text = "Laminar Clássico"
elif re <= 4000:
    badge_class = "badge-transicao"
    regime_text = "Transição Crítica"
else:
    badge_class = "badge-turbulento"
    regime_text = "Turbulento Industrial"

st.markdown(f"""
<div style="text-align:center; margin: 15px 0;">
    <span class="badge {badge_class}">{regime_text} (Re = {re:,.0f})</span>
</div>
""", unsafe_allow_html=True)

# ==================== RESULTADOS ====================

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    <div class="resultado">
        <strong>Diâmetro Hidráulico D_h (m)</strong><br>{dh:.4f}<br><br>
        <strong>Velocidade Média v_m (m/s)</strong><br>{vm:.2f}<br><br>
        <strong>Número de Reynolds (Re)</strong><br>{re:,.0f}<br><br>
        <strong>Fator de Regime α</strong><br>{alfa:.4f}<br><br>
        <strong>Fator k_Balbi</strong><br>{k_balbi:.4f}<br><br>
        <strong>Escala Viscosa λ (m)</strong><br>{lambda_m:.3e}
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="resultado">
        <span class="green"><strong>🏆 Equação de Balbi ΔP/L (Pa/m):</strong></span><br>
        <span style="font-size:1.5rem; font-weight:bold; color:#006400;">{dpl_balbi:.4f}</span><br><br>
        <strong>Colebrook-White ΔP/L (Pa/m):</strong><br>{dpl_cole:.4f}<br><br>
        <strong>Equal Friction ΔP/L (Pa/m):</strong><br>{dpl_ef:.4f}<br><br>
        <strong>Static Regain ΔP/L (Pa/m):</strong><br>{dpl_sr:.4f}
    </div>
    """, unsafe_allow_html=True)

# ==================== GRÁFICO PERFIL ====================

st.markdown("---")
st.markdown("## 📈 Perfil de Velocidades")

r_values = np.linspace(0, raio, 100)
dist_parede = raio - r_values
termo_exp = np.power(dist_parede / lambda_m, alfa)
u_balbi = vmax * (1 - np.exp(-termo_exp))
u_balbi[r_values >= raio * 0.99] = 0
u_cole = vmax * np.power(dist_parede / raio, 1/7)
u_cole = np.where(dist_parede > 0, u_cole, 0)

fig = go.Figure()
fig.add_trace(go.Scatter(x=r_values, y=u_balbi, mode='lines', name='Equação de Balbi', line=dict(color='#006400', width=3)))
fig.add_trace(go.Scatter(x=-r_values[::-1], y=u_balbi[::-1], mode='lines', name='_espelho', line=dict(color='#006400', width=3), showlegend=False))
fig.add_trace(go.Scatter(x=r_values, y=u_cole, mode='lines', name='Lei de Potência 1/7', line=dict(color='#003366', width=2, dash='dash')))
fig.add_trace(go.Scatter(x=-r_values[::-1], y=u_cole[::-1], mode='lines', name='_espelho_cole', line=dict(color='#003366', width=2, dash='dash'), showlegend=False))

fig.update_layout(title=f"Perfil de Velocidades - Duto {dimensao_text}", xaxis_title="Posição Radial (m)", yaxis_title="Velocidade u(r) (m/s)", height=450, template="plotly_white", xaxis=dict(tickmode='array', tickvals=[-raio, 0, raio], ticktext=[f"-{raio:.3f}", "0", f"{raio:.3f}"]))
st.plotly_chart(fig, use_container_width=True)

# ==================== GRÁFICO BARRAS ====================

st.markdown("---")
st.markdown("## 📊 Comparação entre Métodos")

fig_bar = go.Figure(data=[go.Bar(x=['Equação de Balbi', 'Colebrook-White', 'Static Regain', 'Equal Friction'], y=[dpl_balbi, dpl_cole, dpl_sr, dpl_ef], marker_color=['#006400', '#003366', '#ff8c00', '#cc0000'], text=[f"{dpl_balbi:.4f}", f"{dpl_cole:.4f}", f"{dpl_sr:.4f}", f"{dpl_ef:.4f}"], textposition='outside')])
fig_bar.update_layout(title="Perda de Carga Distribuída ΔP/L (Pa/m)", yaxis_title="ΔP/L (Pa/m)", height=400, template="plotly_white")
st.plotly_chart(fig_bar, use_container_width=True)

# ==================== EXPANDER ====================

with st.expander("🔬 Ver detalhes dos parâmetros da Equação de Balbi"):
    st.markdown(f"""
    **Parâmetros geométricos:**  
    - Área A = {area:.6f} m²  
    - Perímetro P = {perim:.6f} m  
    - D_h = {dh:.6f} m  
    - Raio R = {raio:.6f} m  

    **Parâmetros do escoamento:**  
    - v_m = {vm:.4f} m/s  
    - Re = {re:.0f}  
    - α = {alfa:.6f}  
    - v_max = {vmax:.4f} m/s  

    **Parâmetros característicos:**  
    - k_Balbi = {k_balbi:.6f}  
    - λ = {lambda_m:.3e} m = {lambda_m*1e6:.3f} μm  

    **Perda de carga:**  
    - ΔP/L = {dpl_balbi:.6f} Pa/m  
    - ΔP total = {dpl_balbi * comprimento:.6f} Pa  

    **Relação Balbi vs Colebrook:**  
    - Diferença = {((dpl_balbi - dpl_cole) / dpl_cole * 100) if dpl_cole > 0 else 0:.1f}%
    """)

# ==================== PDF PASSO-A-PASSO ====================

st.markdown("---")

def gerar_pdf_passos():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    estilo_normal = styles['Normal']
    estilo_codigo = ParagraphStyle('Codigo', parent=estilo_normal, fontName='Courier', fontSize=9, leftIndent=10)
    estilo_titulo = styles['Title']
    estilo_heading = styles['Heading2']
    
    story = []
    
    # CABEÇALHO
    story.append(Paragraph("MEMORIAL DE CÁLCULO - EQUAÇÃO DE BALBI", estilo_titulo))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(f"Documento gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", estilo_normal))
    story.append(Spacer(1, 8*mm))
    
    # 1. DADOS DE ENTRADA
    story.append(Paragraph("1. DADOS DE ENTRADA", estilo_heading))
    story.append(Spacer(1, 2*mm))
    
    dados_entrada = [
        ["Tipo de duto", tipo],
        ["Dimensões", dimensao_text],
        ["Comprimento L", f"{comprimento} m"],
        ["Vazão Q", f"{vazao} m³/h = {vazao/3600:.6f} m³/s"],
        ["Rugosidade ε", f"{rugosidade_mm:.4f} mm"],
        ["Fluido", "Ar Padrão (20°C, 1 atm)"],
        ["ρ (massa específica)", f"{rho:.2f} kg/m³"],
        ["μ (viscosidade dinâmica)", f"{mu:.2e} Pa·s"],
        ["ν (viscosidade cinemática)", f"{nu:.2e} m²/s"],
        ["v_max/v_m (turbulento)", f"{relacao_vmax:.5f}"],
    ]
    
    tabela = Table(dados_entrada, colWidths=[60*mm, 80*mm])
    tabela.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 9), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (0,-1), colors.lightgrey)]))
    story.append(tabela)
    story.append(Spacer(1, 5*mm))
    
    # 2. PARÂMETROS GEOMÉTRICOS
    story.append(Paragraph("2. PARÂMETROS GEOMÉTRICOS", estilo_heading))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(f"• Área transversal: A = {area:.6f} m²", estilo_normal))
    story.append(Paragraph(f"• Perímetro molhado: P = {perim:.6f} m", estilo_normal))
    story.append(Paragraph(f"• Diâmetro hidráulico: D_h = 4A/P = {dh:.6f} m", estilo_normal))
    story.append(Paragraph(f"• Raio equivalente: R = D_h/2 = {raio:.6f} m", estilo_normal))
    story.append(Spacer(1, 3*mm))
    
    # 3. VELOCIDADE E REYNOLDS
    story.append(Paragraph("3. VELOCIDADE MÉDIA E NÚMERO DE REYNOLDS", estilo_heading))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(f"• Velocidade média: v_m = Q/A = {vazao/3600:.6f} / {area:.6f} = {vm:.4f} m/s", estilo_normal))
    story.append(Paragraph(f"• Número de Reynolds: Re = (v_m × D_h) / ν = ({vm:.4f} × {dh:.6f}) / {nu:.2e} = {re:.0f}", estilo_normal))
    story.append(Paragraph(f"• Classificação do regime: {regime_text}", estilo_normal))
    story.append(Spacer(1, 3*mm))
    
    # 4. EQUAÇÃO DE BALBI - PARÂMETROS
    story.append(Paragraph("4. EQUAÇÃO DE BALBI - PARÂMETROS", estilo_heading))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("4.1 Fator de Regime Contínuo α(Re):", estilo_heading))
    story.append(Paragraph(f"α = 1 + 1 / [1 + (Re/2800)⁴] = 1 + 1 / [1 + ({re:.0f}/2800)⁴] = {alfa:.6f}", estilo_codigo))
    story.append(Spacer(1, 2*mm))
    
    story.append(Paragraph("4.2 Velocidade de Pico v_max:", estilo_heading))
    if re <= 2000:
        story.append(Paragraph(f"Regime laminar: v_max = 2 × v_m = {vmax:.4f} m/s", estilo_normal))
    else:
        story.append(Paragraph(f"v_max = v_m × (v_max/v_m) = {vm:.4f} × {relacao_vmax:.5f} = {vmax:.4f} m/s", estilo_normal))
    story.append(Spacer(1, 2*mm))
    
    story.append(Paragraph("4.3 Coeficiente de Acoplamento k_Balbi:", estilo_heading))
    rug_m = rugosidade_mm / 1000
    if re > 4000:
        story.append(Paragraph(f"k_Balbi = C_base × Re^0,25 × (ε/D_h)^0,1", estilo_codigo))
        story.append(Paragraph(f"Re^0,25 = {re:.0f}^0,25 = {re**0.25:.6f}", estilo_normal))
        story.append(Paragraph(f"ε/D_h = {rug_m:.6f} / {dh:.6f} = {rug_m/dh:.6e}", estilo_normal))
        story.append(Paragraph(f"(ε/D_h)^0,1 = {(rug_m/dh)**0.1:.6f}", estilo_normal))
        story.append(Paragraph(f"k_Balbi = 0,042 × {re**0.25:.4f} × {(rug_m/dh)**0.1:.4f} = {k_balbi:.6f}", estilo_normal))
    elif re <= 2000:
        story.append(Paragraph(f"Regime laminar: k_Balbi = R / (ν/v_m) = {k_balbi:.4f}", estilo_normal))
    else:
        story.append(Paragraph(f"k_Balbi (transição) = {k_balbi:.6f}", estilo_normal))
    story.append(Spacer(1, 2*mm))
    
    story.append(Paragraph("4.4 Comprimento de Onda Viscoso λ:", estilo_heading))
    story.append(Paragraph(f"λ = (ν / v_m) × k_Balbi", estilo_codigo))
    story.append(Paragraph(f"ν / v_m = {nu:.2e} / {vm:.4f} = {nu/vm:.2e} m", estilo_normal))
    story.append(Paragraph(f"λ = {nu/vm:.2e} × {k_balbi:.6f} = {lambda_m:.3e} m = {lambda_m*1e6:.3f} μm", estilo_normal))
    story.append(Spacer(1, 3*mm))
    
    # 5. PERDA DE CARGA
    story.append(Paragraph("5. PERDA DE CARGA DISTRIBUÍDA", estilo_heading))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("5.1 Fórmula geral:", estilo_heading))
    story.append(Paragraph("ΔP/L = (2 × μ × v_max × α) / (R × λ) / 1000", estilo_codigo))
    story.append(Spacer(1, 2*mm))
    
    story.append(Paragraph("5.2 Substituição dos valores:", estilo_heading))
    numerador = 2 * mu * vmax * alfa
    denominador = raio * lambda_m
    story.append(Paragraph(f"Numerador: 2 × {mu:.2e} × {vmax:.4f} × {alfa:.6f} = {numerador:.3e}", estilo_normal))
    story.append(Paragraph(f"Denominador: R × λ = {raio:.6f} × {lambda_m:.3e} = {denominador:.3e}", estilo_normal))
    story.append(Paragraph(f"Divisão bruta: {numerador:.3e} / {denominador:.3e} = {numerador/denominador:.2f} Pa/m", estilo_normal))
    story.append(Paragraph(f"Ajuste (/1000): {numerador/denominador:.2f} / 1000 = {dpl_balbi:.6f} Pa/m", estilo_normal))
    story.append(Spacer(1, 3*mm))
    
    story.append(Paragraph(f"<b>ΔP/L = {dpl_balbi:.6f} Pa/m</b>", estilo_normal))
    story.append(Paragraph(f"Perda total no trecho: ΔP = (ΔP/L) × L = {dpl_balbi:.6f} × {comprimento:.2f} = <b>{dpl_balbi * comprimento:.6f} Pa</b>", estilo_normal))
    story.append(Spacer(1, 5*mm))
    
    # 6. RESULTADOS COMPARATIVOS
    story.append(Paragraph("6. RESULTADOS COMPARATIVOS", estilo_heading))
    story.append(Spacer(1, 2*mm))
    
    tabela_comp = [
        ["Método", "ΔP/L (Pa/m)", "ΔP total (Pa)", "Característica"],
        ["🏆 Equação de Balbi", f"{dpl_balbi:.6f}", f"{dpl_balbi * comprimento:.6f}", "Explícito, não iterativo, capta rugosidade"],
        ["Colebrook-White", f"{dpl_cole:.6f}", f"{dpl_cole * comprimento:.6f}", "Implícito, exige iteração"],
        ["Static Regain", f"{dpl_sr:.6f}", f"{dpl_sr * comprimento:.6f}", f"Empírico, η={static_eta}%, v₀={static_v0} m/s"],
        ["Equal Friction", f"{dpl_ef:.6f}", f"{dpl_ef * comprimento:.6f}", f"Arbitrário, valor fixo = {equal_friction} Pa/m"],
    ]
    
    tabela_comp_pdf = Table(tabela_comp, colWidths=[45*mm, 35*mm, 35*mm, 55*mm])
    tabela_comp_pdf.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,0), colors.lightblue), ('BACKGROUND', (0,1), (0,-1), colors.lightgrey)]))
    story.append(tabela_comp_pdf)
    story.append(Spacer(1, 5*mm))
    
    # 7. ANÁLISE
    story.append(Paragraph("7. ANÁLISE DOS RESULTADOS", estilo_heading))
    diff = ((dpl_balbi - dpl_cole) / dpl_cole * 100) if dpl_cole > 0 else 0
    story.append(Paragraph(f"• Diferença Equação de Balbi vs Colebrook-White: {diff:+.1f}%", estilo_normal))
    story.append(Spacer(1, 5*mm))
    
    story.append(Paragraph("CONCLUSÃO:", estilo_heading))
    story.append(Paragraph("A Equação de Balbi é um método EXPLÍCITO (não iterativo), captura rugosidade, α(Re) contínuo, e entrega margem de segurança controlada.", estilo_normal))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

if st.button("📄 Gerar Memorial PDF (CÁLCULO PASSO-A-PASSO)", use_container_width=True):
    pdf_bytes = gerar_pdf_passos()
    b64 = base64.b64encode(pdf_bytes).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="memorial_balbi_passos.pdf">📥 Clique para baixar o PDF com todos os passos</a>', unsafe_allow_html=True)
    st.success("PDF gerado com sucesso!")

# ==================== RODAPÉ ====================

st.markdown("""
<div class="footer">
    <p><strong>📐 Fórmulas da Equação de Balbi</strong></p>
    <p>λ = (ν / v_m) × k_Balbi | ΔP/L = (2 × μ × v_max × α) / (R × λ) / 1000</p>
    <p>k_Balbi = 0,042 × Re^0,25 × (ε / D_h)^0,1 (Regime Turbulento Industrial) | α(Re) = 1 + 1 / [1 + (Re/2800)⁴]</p>
    <p>© 2025 Equação de Balbi · Vinícius Cabral Balbi · ASHRAE Member</p>
</div>
""", unsafe_allow_html=True)
