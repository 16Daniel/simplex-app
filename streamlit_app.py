import streamlit as st
import pulp as pl
import pandas as pd
import plotly.express as px
import io
import json
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Simplex: Nómina y Turnos Ideales", layout="wide")

# --- MANEJO DE CONFIGURACIÓN MAESTRA (GUARDADO PERMANENTE) ---
CONFIG_FILE = "config_simplex.json"
DEFAULT_CONFIG = {
    's_coc': 350.0, 's_ven': 300.0, 's_bar': 320.0, 's_sup': 500.0, 's_caj': 300.0, 's_hos': 250.0,
    'c_coc': 8, 'c_sal': 12, 'c_bar': 15
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

config_data = load_config()

# --- CONSTANTES ---
dias_semana = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
bloques = ["10:00 a 14:00 (4 hrs)", "14:00 a 17:00 (3 hrs)", "17:00 a 18:00 (1 hr)", "18:00 a 22:00 (4 hrs)", "22:00 a 01:00 (3 hrs)"]
horas_por_bloque = [4, 3, 1, 4, 3]

# --- INICIALIZAR MEMORIA DIRECTA (BLINDADA) ---
if 'init_done' not in st.session_state:
    st.session_state['tope'] = 20.0
    st.session_state['config_unlocked'] = False
    
    for d in dias_semana:
        factor = 1.5 if d in ["Viernes", "Sábado", "Domingo"] else 1.0
        
        # Ventas iniciales
        st.session_state[f"v_{d}"] = 25000.0 if d == "Viernes" else (30000.0 if d == "Sábado" else (22000.0 if d == "Domingo" else 15000.0))
        
        # Fijos iniciales
        st.session_state[f"sm_{d}"] = False
        st.session_state[f"si_{d}"] = True
        st.session_state[f"sv_{d}"] = False
        st.session_state[f"cm_{d}"] = True
        st.session_state[f"ci_{d}"] = False
        st.session_state[f"cv_{d}"] = True
        st.session_state[f"hm_{d}"] = False
        st.session_state[f"hi_{d}"] = True
        st.session_state[f"hv_{d}"] = True
        
        # Demanda inicial por bloque
        cc_def = [15.0, 30.0, 20.0, 60.0, 25.0]
        cs_def = [20.0, 45.0, 30.0, 85.0, 30.0]
        cb_def = [5.0, 20.0, 15.0, 70.0, 40.0]
        ex_def = [1.0, 0.0, 0.0, 0.5, 1.5]
        
        for i in range(5):
            st.session_state[f"cc_{d}_{i}"] = cc_def[i] * factor
            st.session_state[f"ec_{d}_{i}"] = ex_def[i]
            st.session_state[f"cs_{d}_{i}"] = cs_def[i] * factor
            st.session_state[f"es_{d}_{i}"] = ex_def[i]
            st.session_state[f"cb_{d}_{i}"] = cb_def[i] * factor
            st.session_state[f"eb_{d}_{i}"] = ex_def[i]

    st.session_state['init_done'] = True

# --- FUNCIÓN PARA DESCARGAR MACHOTE ---
def generar_machote():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Pestaña 1: Ventas
        pd.DataFrame({"Día": dias_semana, "Venta Proyectada ($)": [st.session_state[f"v_{d}"] for d in dias_semana]}).to_excel(writer, sheet_name="Ventas", index=False)
        
        # Pestaña 2: Personal Fijo
        fijos_filas = []
        for d in dias_semana:
            fijos_filas.append({
                "Día": d,
                "Sup_Matutino": "Si" if st.session_state[f"sm_{d}"] else "No", "Sup_Intermedio": "Si" if st.session_state[f"si_{d}"] else "No", "Sup_Vespertino": "Si" if st.session_state[f"sv_{d}"] else "No",
                "Caj_Matutino": "Si" if st.session_state[f"cm_{d}"] else "No", "Caj_Intermedio": "Si" if st.session_state[f"ci_{d}"] else "No", "Caj_Vespertino": "Si" if st.session_state[f"cv_{d}"] else "No",
                "Hos_Matutino": "Si" if st.session_state[f"hm_{d}"] else "No", "Hos_Intermedio": "Si" if st.session_state[f"hi_{d}"] else "No", "Hos_Vespertino": "Si" if st.session_state[f"hv_{d}"] else "No"
            })
        pd.DataFrame(fijos_filas).to_excel(writer, sheet_name="Personal_Fijo", index=False)
        
        # Pestaña 3: Demanda
        filas = []
        for d in dias_semana:
            for i, b in enumerate(bloques):
                filas.append({
                    "Día": d, "Bloque": b,
                    "Cmds_Cocina": st.session_state[f"cc_{d}{i}"], "Extra_Cocina": st.session_state[f"ec{d}_{i}"],
                    "Cmds_Salon": st.session_state[f"cs_{d}{i}"],  "Extra_Salon": st.session_state[f"es{d}_{i}"],
                    "Cmds_Barra": st.session_state[f"cb_{d}{i}"],  "Extra_Barra": st.session_state[f"eb{d}_{i}"]
                })
        pd.DataFrame(filas).to_excel(writer, sheet_name="Demanda", index=False)
    return output.getvalue()

# --- ENCABEZADO Y CARGA MASIVA ---
st.title("🍔 SIMPLEX: NÓMINA Y TURNOS IDEALES")
st.markdown("Carga tu proyección de toda la semana. Ahora el sistema actualiza de inmediato todas las pantallas para que valides tus datos antes de calcular.")

col_down, col_up = st.columns([1, 2])
with col_down:
    st.info("⬇️ *Paso 1: Descargar Plantilla Semanal*")
    st.download_button(label="📥 Descargar Machote de Excel", data=generar_machote(), file_name="Machote_Semanal.xlsx", mime="application/vnd.ms-excel")

with col_up:
    uploaded_file = st.file_uploader("⬆️ *Paso 2: Sube tu Excel y presiona Procesar*", type=["xlsx"])
    if uploaded_file is not None:
        if st.button("⚙️ Procesar y Cargar Datos", type="primary"):
            try:
                df_v = pd.read_excel(uploaded_file, sheet_name="Ventas")
                df_f = pd.read_excel(uploaded_file, sheet_name="Personal_Fijo")
                df_d = pd.read_excel(uploaded_file, sheet_name="Demanda")
                
                # Cargar Ventas
                for _, row in df_v.iterrows():
                    dia = str(row['Día']).strip()
                    if dia in dias_semana:
                        st.session_state[f"v_{dia}"] = float(row['Venta Proyectada ($)'])
                
                # Cargar Personal Fijo
                def es_si(valor):
                    return str(valor).strip().lower() == 'si'
                
                for _, row in df_f.iterrows():
                    dia = str(row['Día']).strip()
                    if dia in dias_semana:
                        st.session_state[f"sm_{dia}"] = es_si(row['Sup_Matutino'])
                        st.session_state[f"si_{dia}"] = es_si(row['Sup_Intermedio'])
                        st.session_state[f"sv_{dia}"] = es_si(row['Sup_Vespertino'])
                        st.session_state[f"cm_{dia}"] = es_si(row['Caj_Matutino'])
                        st.session_state[f"ci_{dia}"] = es_si(row['Caj_Intermedio'])
                        st.session_state[f"cv_{dia}"] = es_si(row['Caj_Vespertino'])
                        st.session_state[f"hm_{dia}"] = es_si(row['Hos_Matutino'])
                        st.session_state[f"hi_{dia}"] = es_si(row['Hos_Intermedio'])
                        st.session_state[f"hv_{dia}"] = es_si(row['Hos_Vespertino'])

                # Cargar Demanda
                for d in dias_semana:
                    df_dia = df_d[df_d['Día'].str.strip() == d].reset_index()
                    if not df_dia.empty and len(df_dia) == 5:
                        for i in range(5):
                            st.session_state[f"cc_{d}_{i}"] = float(df_dia['Cmds_Cocina'].iloc[i])
                            st.session_state[f"ec_{d}_{i}"] = float(df_dia['Extra_Cocina'].iloc[i])
                            st.session_state[f"cs_{d}_{i}"] = float(df_dia['Cmds_Salon'].iloc[i])
                            st.session_state[f"es_{d}_{i}"] = float(df_dia['Extra_Salon'].iloc[i])
                            st.session_state[f"cb_{d}_{i}"] = float(df_dia['Cmds_Barra'].iloc[i])
                            st.session_state[f"eb_{d}_{i}"] = float(df_dia['Extra_Barra'].iloc[i])
                
                st.success("✅ ¡Datos cargados perfectamente! Se han actualizado todas las pestañas.")
                st.rerun() 
            except Exception as e:
                st.error(f"⚠️ Error al leer el Excel. Asegúrate de no cambiar los títulos de las columnas ni las hojas. Detalle: {e}")

st.divider()

# --- BARRA LATERAL ---
st.sidebar.header("💰 1. Límite Financiero")
max_nomina_pct = st.sidebar.slider("Tope Máximo de Nómina (%)", min_value=10.0, max_value=40.0, value=st.session_state['tope'], key='tope')

st.sidebar.markdown("---")
st.sidebar.header("🔐 Configuración Maestra")

if not st.session_state['config_unlocked']:
    st.sidebar.write("🔒 Variables fijas bloqueadas.")
    pwd = st.sidebar.text_input("Contraseña:", type="password", key="pwd_input")
    if st.sidebar.button("🔓 Desbloquear"):
        if pwd == "M@5terkey":
            st.session_state['config_unlocked'] = True
            st.rerun()
        else:
            st.sidebar.error("Contraseña incorrecta.")
else:
    st.sidebar.success("🔓 Modo Edición Activo")
    new_s_coc = st.sidebar.number_input("Sal. Cocinero ($)", value=config_data['s_coc'])
    new_s_ven = st.sidebar.number_input("Sal. Vendedor ($)", value=config_data['s_ven'])
    new_s_bar = st.sidebar.number_input("Sal. Barra ($)", value=config_data['s_bar'])
    new_s_sup = st.sidebar.number_input("Sal. Supervisor ($)", value=config_data['s_sup'])
    new_s_caj = st.sidebar.number_input("Sal. Cajero ($)", value=config_data['s_caj'])
    new_s_hos = st.sidebar.number_input("Sal. Hostess ($)", value=config_data['s_hos'])
    new_c_coc = st.sidebar.number_input("Cap. Cocina (cmd/hr)", value=config_data['c_coc'])
    new_c_sal = st.sidebar.number_input("Cap. Salón (cmd/hr)", value=config_data['c_sal'])
    new_c_bar = st.sidebar.number_input("Cap. Barra (cmd/hr)", value=config_data['c_bar'])
    
    if st.sidebar.button("🔒 Guardar y Bloquear"):
        config_data.update({'s_coc': new_s_coc, 's_ven': new_s_ven, 's_bar': new_s_bar, 's_sup': new_s_sup, 's_caj': new_s_caj, 's_hos': new_s_hos, 'c_coc': new_c_coc, 'c_sal': new_c_sal, 'c_bar': new_c_bar})
        save_config(config_data)
        st.session_state['config_unlocked'] = False
        st.rerun()

# Extraer configuración activa para los cálculos
s_coc, s_ven, s_bar = config_data['s_coc'], config_data['s_ven'], config_data['s_bar']
s_sup, s_caj, s_hos = config_data['s_sup'], config_data['s_caj'], config_data['s_hos']
c_coc, c_sal, c_bar = config_data['c_coc'], config_data['c_sal'], config_data['c_bar']

# --- ÁREA PRINCIPAL: PESTAÑAS DIARIAS ---
st.subheader("📅 2. Proyección Diaria")
st.write("Valida la carga de trabajo y ajusta al personal fijo para cada día.")

tabs = st.tabs(dias_semana)

for idx, d in enumerate(dias_semana):
    with tabs[idx]:
        st.number_input(f"💰 Venta Proyectada para el {d} ($)", step=500.0, key=f"v_{d}")
        
        st.markdown(f"*👔 Personal Fijo Requerido ({d}):*")
        col_sup, col_caj, col_hos = st.columns(3)
        with col_sup:
            st.checkbox("Supervisor Matutino", key=f"sm_{d}")
            st.checkbox("Supervisor Intermedio", key=f"si_{d}")
            st.checkbox("Supervisor Vespertino", key=f"sv_{d}")
        with col_caj:
            st.checkbox("Cajero Matutino", key=f"cm_{d}")
            st.checkbox("Cajero Intermedio", key=f"ci_{d}")
            st.checkbox("Cajero Vespertino", key=f"cv_{d}")
        with col_hos:
            st.checkbox("Hostess Matutino", key=f"hm_{d}")
            st.checkbox("Hostess Intermedio", key=f"hi_{d}")
            st.checkbox("Hostess Vespertino", key=f"hv_{d}")
            
        st.markdown("---")
        st.markdown(f"*📋 Carga de Trabajo (Comandas y Hrs Extra):*")
        cols = st.columns(7)
        cols[0].markdown("*Horario (hrs)*")
        cols[1].markdown("*Cmds Cocina*")
        cols[2].markdown("*Ext Cocina (hrs)*")
        cols[3].markdown("*Cmds Salón*")
        cols[4].markdown("*Ext Salón (hrs)*")
        cols[5].markdown("*Cmds Barra*")
        cols[6].markdown("*Ext Barra (hrs)*")
        
        for i in range(5):
            cc = st.columns(7)
            cc[0].write(bloques[i][:11]) 
            cc[1].number_input("cc", step=5.0, key=f"cc_{d}_{i}", label_visibility="collapsed")
            cc[2].number_input("ec", step=0.5, key=f"ec_{d}_{i}", label_visibility="collapsed")
            cc[3].number_input("cs", step=5.0, key=f"cs_{d}_{i}", label_visibility="collapsed")
            cc[4].number_input("es", step=0.5, key=f"es_{d}_{i}", label_visibility="collapsed")
            cc[5].number_input("cb", step=5.0, key=f"cb_{d}_{i}", label_visibility="collapsed")
            cc[6].number_input("eb", step=0.5, key=f"eb_{d}_{i}", label_visibility="collapsed")

st.divider()

# --- OPTIMIZACIÓN SEMANAL ---
if st.button("🚀 Calcular Plantilla Semanal", type="primary"):
    
    resultados_diarios = {}
    costo_total_semana = 0
    venta_total_semana = sum([st.session_state[f"v_{d}"] for d in dias_semana])
    dias_inviables = []
    
    capacidades = {'Cocina': c_coc, 'Salon': c_sal, 'Barra': c_bar}
    roles = ['Cocina', 'Salon', 'Barra']
    turnos = ['M', 'I', 'V']
    
    for d in dias_semana:
        modelo = pl.LpProblem(f"Optimizacion_{d}", pl.LpMinimize)
        vars_personal = pl.LpVariable.dicts(f"Pers_{d}", [(r, t) for r in roles for t in turnos], lowBound=0, cat='Integer')
        modelo += pl.lpSum([vars_personal[(r, t)] for r in roles for t in turnos])
        
        demandas = {
            'Cocina': [st.session_state[f"cc_{d}_{i}"] for i in range(5)],
            'Salon':  [st.session_state[f"cs_{d}_{i}"] for i in range(5)],
            'Barra':  [st.session_state[f"cb_{d}_{i}"] for i in range(5)]
        }
        extras = {
            'Cocina': [st.session_state[f"ec_{d}_{i}"] for i in range(5)],
            'Salon':  [st.session_state[f"es_{d}_{i}"] for i in range(5)],
            'Barra':  [st.session_state[f"eb_{d}_{i}"] for i in range(5)]
        }
        
        for r in roles:
            for i in range(5):
                req_horas = (demandas[r][i] / capacidades[r]) + extras[r][i]
                if i == 0:   gente = vars_personal[(r, 'M')]
                elif i == 1: gente = vars_personal[(r, 'M')] + vars_personal[(r, 'I')]
                elif i == 2: gente = vars_personal[(r, 'M')] + vars_personal[(r, 'I')] + vars_personal[(r, 'V')]
                elif i == 3: gente = vars_personal[(r, 'I')] + vars_personal[(r, 'V')]
                elif i == 4: gente = vars_personal[(r, 'V')]
                modelo += (gente * horas_por_bloque[i]) >= req_horas

        q_sup = sum([st.session_state[f"sm_{d}"], st.session_state[f"si_{d}"], st.session_state[f"sv_{d}"]])
        q_caj = sum([st.session_state[f"cm_{d}"], st.session_state[f"ci_{d}"], st.session_state[f"cv_{d}"]])
        q_hos = sum([st.session_state[f"hm_{d}"], st.session_state[f"hi_{d}"], st.session_state[f"hv_{d}"]])
        
        costo_fijo_diario = (q_sup * s_sup) + (q_caj * s_caj) + (q_hos * s_hos)
        presupuesto_diario = st.session_state[f"v_{d}"] * (st.session_state['tope'] / 100)
        
        costo_var = pl.lpSum([vars_personal[('Cocina', t)] * s_coc + vars_personal[('Salon', t)] * s_ven + vars_personal[('Barra', t)] * s_bar for t in turnos])
        
        modelo += (costo_var + costo_fijo_diario) <= presupuesto_diario
        status = modelo.solve()
        
        if pl.LpStatus[status] == 'Optimal':
            c_dia = pl.value(costo_var) + costo_fijo_diario
            costo_total_semana += c_dia
            
            resultados_diarios[d] = {
                'M': [vars_personal[('Cocina','M')].varValue, vars_personal[('Salon','M')].varValue, vars_personal[('Barra','M')].varValue, int(st.session_state[f"cm_{d}"]), int(st.session_state[f"sm_{d}"]), int(st.session_state[f"hm_{d}"])] ,
                'I': [vars_personal[('Cocina','I')].varValue, vars_personal[('Salon','I')].varValue, vars_personal[('Barra','I')].varValue, int(st.session_state[f"ci_{d}"]), int(st.session_state[f"si_{d}"]), int(st.session_state[f"hi_{d}"])] ,
                'V': [vars_personal[('Cocina','V')].varValue, vars_personal[('Salon','V')].varValue, vars_personal[('Barra','V')].varValue, int(st.session_state[f"cv_{d}"]), int(st.session_state[f"sv_{d}"]), int(st.session_state[f"hv_{d}"])] ,
                'Costo': c_dia
            }
        else:
            dias_inviables.append(d)

    # --- RESULTADOS ---
    if dias_inviables:
        st.error(f"⚠️ *Presupuesto Inviable en los siguientes días:* {', '.join(dias_inviables)}. \n El presupuesto de nómina no alcanza para cubrir la demanda. Aumenta la venta proyectada ($) o el % de nómina.")
    else:
        st.success("✅ ¡Semana Optimizada con Éxito!")
        pct_semanal_real = (costo_total_semana / venta_total_semana) * 100
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label="💰 Costo Nómina Semanal", value=f"$ {costo_total_semana:,.2f}")
        kpi2.metric(label="📈 % Nómina Semanal (Real)", value=f"{pct_semanal_real:.1f} %")
        kpi3.metric(label="🎯 Venta Total Esperada", value=f"$ {venta_total_semana:,.2f}")
        
        st.subheader("📅 Tu Plantilla Maestra Semanal (Turnos a Contratar)")
        
        filas_maestras = []
        for d in dias_semana:
            filas_maestras.append({
                "Día": d, "Turno": "Matutino (10 a 18 hrs)", 
                "Cocineros": int(resultados_diarios[d]['M'][0]), "Salón": int(resultados_diarios[d]['M'][1]), "Barra": int(resultados_diarios[d]['M'][2]),
                "Cajero": resultados_diarios[d]['M'][3], "Supervisor": resultados_diarios[d]['M'][4], "Hostess": resultados_diarios[d]['M'][5],
                "Costo del Día": f"$ {resultados_diarios[d]['Costo']:,.2f}" 
            })
            filas_maestras.append({
                "Día": "", "Turno": "Intermedio (14 a 22 hrs)", 
                "Cocineros": int(resultados_diarios[d]['I'][0]), "Salón": int(resultados_diarios[d]['I'][1]), "Barra": int(resultados_diarios[d]['I'][2]),
                "Cajero": resultados_diarios[d]['I'][3], "Supervisor": resultados_diarios[d]['I'][4], "Hostess": resultados_diarios[d]['I'][5],
                "Costo del Día": "" 
            })
            filas_maestras.append({
                "Día": "", "Turno": "Vespertino (17 a 01 hrs)", 
                "Cocineros": int(resultados_diarios[d]['V'][0]), "Salón": int(resultados_diarios[d]['V'][1]), "Barra": int(resultados_diarios[d]['V'][2]),
                "Cajero": resultados_diarios[d]['V'][3], "Supervisor": resultados_diarios[d]['V'][4], "Hostess": resultados_diarios[d]['V'][5],
                "Costo del Día": "" 
            })
            
        st.dataframe(pd.DataFrame(filas_maestras).set_index("Día"), use_container_width=True)
        
        st.subheader("💡 Resumen Ejecutivo Semanal")
        st.markdown(f"""
        ✔️ *Venta Semanal:* Tienes una proyección de ventas totales de *$ {venta_total_semana:,.2f}* para toda la semana.
        
        ✔️ *Tope Financiero:* Con tu límite configurado del *{st.session_state['tope']:.1f} %* , el sistema cuidó matemáticamente que NINGÚN DÍA superara su presupuesto individual.
        
        ✔️ *Resultado Exitoso:* El costo total de tu plantilla de Domingo a Sábado será de *$ {costo_total_semana:,.2f}* . Esto promedia un *{pct_semanal_real:.1f} %* de nómina total semanal. ¡La operación y las finanzas están cubiertas y aseguradas para toda la semana! 🚀
        """)