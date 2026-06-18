import streamlit as st
import math
import json
import os
from datetime import datetime
from PIL import Image

# Configuración de la página
st.set_page_config(page_title="Calculadora Puente Warren - UNICA", layout="centered")

# Inicializar estado de la sesión
if 'ingresado' not in st.session_state:
    st.session_state.ingresado = False
if 'history' not in st.session_state:
    st.session_state.history = []

# ============================
# PANTALLA DE HOME (INICIO)
# ============================
if not st.session_state.ingresado:
    # Logo de la Universidad en la esquina superior derecha
    try:
        logo_uni = Image.open("logo.png")
        col_izq, col_der = st.columns([4, 1])
        with col_der:
            st.image(logo_uni, width=100)
    except:
        pass

    st.markdown("<h1 style='text-align: center;'>Proyecto Integrador</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Análisis Estructural: Armaduras Warren</h3>", unsafe_allow_html=True)
    st.markdown("---")

    # Imagen generada por Gemini
    try:
        img_gemini = Image.open("Gemini_Generated_Image_eui7skeui7skeui7.png")
        st.image(img_gemini, use_container_width=True)
    except:
        st.warning("⚠️ Sube el archivo 'Gemini_Generated_Image_eui7skeui7skeui7.png' para ver la imagen central.")

    st.write("##")
    if st.button("INGRESAR A LA CALCULADORA", use_container_width=True):
        st.session_state.ingresado = True
        st.rerun()

# ============================
# PANTALLA DE LA CALCULADORA
# ============================
else:
    # Header con logo pequeño
    try:
        logo_uni = Image.open("logo.png")
        st.sidebar.image(logo_uni, width=80)
    except:
        pass

    st.sidebar.button("⬅️ Volver al Inicio", on_click=lambda: st.session_state.update(ingresado=False))
    st.title("🏗️ Calculadora de Armadura Tipo Warren")
    st.markdown("---")

    class WarrenTruss:
        def __init__(self, L, H, panels, P_total):
            self.L = L
            self.H = H
            self.panels = panels
            self.P_total = P_total
            self.results = {}
            self._analyze()

        def _analyze(self):
            L, H, n, Pt = self.L, self.H, self.panels, self.P_total
            d = L / n
            diag_len = math.hypot(d, H)
            sin_a = H / diag_len if diag_len != 0 else 0
            angle_deg = math.degrees(math.atan2(H, d))
            load_nodes = max(1, n - 1)
            P_node = Pt / load_nodes
            Ra = Rb = Pt / 2

            V, shear = [], Ra
            for i in range(n):
                V.append(shear)
                if i < load_nodes:
                    shear -= P_node

            bot_forces = []
            for i in range(n):
                x_right = (i + 1) * d
                M = Ra * x_right
                if i > 0:
                    for j in range(1, i + 1):
                        M -= P_node * (j * d)
                bot_forces.append(M / H if H != 0 else 0)

            top_forces = []
            for i in range(n):
                x_mid = (i + 0.5) * d
                M = Ra * x_mid - sum(P_node * (j * d) for j in range(1, i + 1) if j * d < x_mid)
                top_forces.append(-M / H if H != 0 else 0)

            diag_forces = [V[i] / sin_a if sin_a != 0 else 0 for i in range(n)]

            members = []
            for i, f in enumerate(top_forces):
                members.append({"id": f"CS{i+1}", "name": f"Cordon Superior {i+1}", "type": "top_chord", "force": round(f, 3), "length": round(d, 3), "stress_type": "Compresión" if f < 0 else "Tensión"})
            for i, f in enumerate(bot_forces):
                members.append({"id": f"CI{i+1}", "name": f"Cordon Inferior {i+1}", "type": "bot_chord", "force": round(f, 3), "length": round(d, 3), "stress_type": "Tensión" if f > 0 else "Compresión"})
            for i, f in enumerate(diag_forces):
                members.append({"id": f"D{i+1}", "name": f"Diagonal {i+1}", "type": "diagonal", "force": round(f, 3), "length": round(diag_len, 3), "stress_type": "Tensión" if f > 0 else "Compresión"})

            self.results = {
                "L": L, "H": H, "panels": n, "P_total": Pt, "P_node": round(P_node, 3), "Ra": round(Ra, 3), "Rb": round(Rb, 3),
                "d": round(d, 3), "diag": round(diag_len, 3), "angle_deg": round(angle_deg, 2), "members": members,
                "max_force": round(max(abs(m["force"]) for m in members), 3), "n_members": len(members), "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        def evaluate_safety(self, material="Acero A36", A_cm2=50.0):
            A_mm2 = A_cm2 * 100.0
            Fy_MPa = {"Acero A36": 250.0, "Acero A572": 345.0, "Aluminio 6061": 276.0}.get(material, 250.0)
            allowable_MPa = Fy_MPa / 1.67
            member_evals, critical, warnings = [], [], []

            for m in self.results["members"]:
                sigma_MPa = (abs(m["force"]) * 1000.0) / A_mm2 if A_mm2 != 0 else float('inf')
                ratio = sigma_MPa / allowable_MPa
                status, color = ("FALLA", "danger") if ratio > 1.0 else (("LIMITE", "warn") if ratio > 0.85 else ("SEGURO", "safe"))
                if status == "FALLA": critical.append(m["id"])
                if status == "LIMITE": warnings.append(m["id"])
                member_evals.append({**m, "sigma_MPa": round(sigma_MPa, 2), "allowable_MPa": round(allowable_MPa, 2), "ratio": round(ratio, 3), "status": status, "color": color})

            verdict, v_level = ("PELIGROSO", "danger") if critical else (("PRECAUCIÓN", "warn") if warnings else ("SEGURO", "safe"))
            sugg = []
            hl = self.results["H"] / self.results["L"]
            if critical:
                sugg.append(f"Aumentar sección transversal a mínimo {((self.results['max_force']*1000/allowable_MPa)*1.15/100):.2f} cm²")
                sugg.append("Cambiar a Acero A572 (mayor resistencia)")
            elif warnings:
                sugg.append(f"Aumentar sección en 20% (aprox. {(A_cm2*1.2):.2f} cm²)")
            else:
                sugg.append("Diseño dentro de parámetros admisibles")

            if hl < 0.10: sugg.append("Aumentar altura del puente (H/L < 0.10)")

            return {"verdict": verdict, "v_level": v_level, "material": material, "section_area_cm2": round(A_cm2, 1), "allowable_MPa": round(allowable_MPa, 1), "member_evals": member_evals, "suggestions": sugg}

    st.sidebar.header("📋 Parámetros")
    with st.sidebar.form("params_form"):
        L = st.number_input("Longitud L (m)", min_value=1.0, value=20.0)
        H = st.number_input("Altura H (m)", min_value=0.5, value=3.0)
        n = st.slider("Paneles", 2, 20, 6)
        P = st.number_input("Carga P (kN)", min_value=1.0, value=500.0)
        A_cm2 = st.number_input("Área (cm²)", min_value=1.0, value=50.0)
        mat = st.selectbox("Material", ["Acero A36", "Acero A572", "Aluminio 6061"])
        submit = st.form_submit_button("CALCULAR")

    tab1, tab2, tab3 = st.tabs(["📊 Resumen", "📋 Miembros", "📈 Diagrama"])
    if submit:
        truss = WarrenTruss(L, H, n, P)
        safety = truss.evaluate_safety(mat, A_cm2)
        res = truss.results
        with tab1:
            st.write(f"### ESTADO: {safety['verdict']}")
            st.caption(f"σ_adm = {safety['allowable_MPa']} MPa")
            c1, c2, c3 = st.columns(3)
            c1.metric("Ra/Rb", f"{res['Ra']} kN")
            c2.metric("Fuerza Máx", f"{res['max_force']} kN")
            c3.metric("Ángulo", f"{res['angle_deg']}°")
            for s in safety["suggestions"]: st.info(s)
        with tab2:
            import pandas as pd
            st.dataframe(pd.DataFrame(safety["member_evals"])[["id", "stress_type", "force", "sigma_MPa", "status"]], use_container_width=True)
        with tab3:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ax.plot([0, L], [0, 0], 'b-'); ax.plot([0, L], [H, H], 'r-')
            ax.set_aspect('equal'); st.pyplot(fig)
