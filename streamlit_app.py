import streamlit as st
import pulp as pl
import pandas as pd
import plotly.express as px
import io
import json
import os

# Configuración de la página
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

# --- INICIALIZAR VARIABLES EN MEMORIA ---
dias_semana = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
bloques = ["10:00 a 14:00 (4 hrs)", "14:00 a 17:00 (3 hrs)", "17:00 a 18:00 (1 hr)", "18:00 a 22:00 (4 hrs)", "22:00 a 01:00 (3 hrs)"]
horas_por_bloque = [4, 3, 1, 4, 3]

if 'data_loaded' not in st.session_state:
    st.session_state['tope'] = 20.0
    st.session_state['sup_m'] = False
    st.session_state['sup_i'] = True
    st.session_state['sup_v'] = False
    st.session_state['caj_m'] = True
    st.session_state['caj_i'] = False
    st.session_state['caj_v'] = True
    st.session_state['hos_m'] = False
    st.session_state['hos_i'] = True
    st.session_state['hos_v'] = True
    st.session_state['config_unlocked'] = False
    st.session_state['last_upload'] = None
    
    # Datos Semanales por defecto
    st.session_state['ventas'] = {d: 15000.0 for d in dias_semana}
    st.session_state['ventas']['Viernes'] = 25000.0
    st.session_state['ventas']['Sábado'] = 30000.0
    st.session_state['ventas']['Domingo'] = 22000.0
    
    st.session_state['demanda'] = {}
    for d in dias_semana:
        # Damos un empujoncito extra los fines de semana de ejemplo
        factor = 1.5 if d in ["Viernes", "Sábado", "Domingo"] else 1.0
        st.session_state['demanda'][d] = {
            'c_c': [15*factor, 30*factor, 20*factor, 60*factor, 25*factor],
            'e_c': [1.0, 0.0, 0.0, 0.5, 1.5],
            'c_s': [20*factor, 45*factor, 30*factor, 85*factor, 30*factor],
            'e_s': [1.0, 0.0, 0.0, 0.5, 1.5],
            'c_b': [5*factor, 20*factor, 15*factor, 70*factor, 40*factor],
            'e_b': [1.0, 0.0, 0.0, 0.5, 1.5]
        }
    st.session_state['data_loaded'] = True

# --- FUNCIÓN PARA CREAR EL MACHOTE EXCEL SEMANAL ---
def generar_machote():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Pestaña 1: Ventas Diarias
        ventas_data = {"Día": dias_semana, "Venta Proyectada ($)": [st.session_state['ventas'][d] for d in dias_semana]}
        pd.DataFrame(ventas_data).to_excel(writer, sheet_name="Ventas_Diarias", index=False)
        
        # Pestaña 2: Demanda Semanal
        filas = []
        for d in dias_semana:
            for i, b in enumerate(bloques):
                filas.append({
                    "Día": d, "Bloque": b,
                    "Cmds_Cocina": st.session_state['demanda'][d]['c_c'][i], "Extra_Cocina": st.session_state['demanda'][d]['e_c'][i],
                    "Cmds_Salon": st.session_state['demanda'][d]['c_s'][i],  "Extra_Salon": st.session_state['demanda'][d]['e_s'][i],
                    "Cmds_Barra": st.session_state['demanda'][d]['c_b'][i],  "Extra_Barra": st.session_state['demanda'][d]['e_b'][i]
                })
        pd.DataFrame(filas).to_excel(writer, sheet_name="Demanda_Semanal", index=False)
    return output.getvalue()

# --- ENCABEZADO Y CARGA MASIVA ---
st.title("🍔 SIMPLEX: NÓMINA Y TURNOS IDEALES")
st.markdown("Carga tu proyección de ventas y comandas de *TODA LA SEMANA*. El sistema calculará tu plantilla ideal de Domingo a Sábado.")

col_down, col_up = st.columns([1, 2])
with col_down:
    st.info("⬇️ *Paso 1: Descargar Plantilla Semanal*")
    st.download_button(label="📥 Descargar Machote de Excel", data=generar_machote(), file_name="Machote_Semanal.xlsx", mime="application/vnd.ms-excel")

with col_up:
    uploaded_file = st.file_uploader("⬆️ *Paso 2: Sube tu Excel Lleno Aquí*", type=["xlsx"])
    if uploaded_file and uploaded_file.name != st.session_state['last_upload']:
        try:
            df_v = pd.read_excel(uploaded_file, sheet_name="Ventas_Diarias")
            df_d = pd.read_excel(uploaded_file, sheet_name="Demanda_Semanal")
            
            for _, row in df_v.iterrows():
                if row['Día'] in st.session_state['ventas']:
                    st.session_state['ventas'][row['Día']] = float(row['Venta Proyectada ($)'])
            
            for d in dias_semana:
                df_dia = df_d[df_d['Día'] == d].reset_index()
                if not df_dia.empty:
                    st.session_state['demanda'][d]['c_c'] = df_dia['Cmds_Cocina'].tolist()
                    st.session_state['demanda'][d]['e_c'] = df_dia['Extra_Cocina'].tolist()
                    st.session_state['demanda'][d]['c_s'] = df_dia['Cmds_Salon'].tolist()
                    st.session_state['demanda'][d]['e_s'] = df_dia['Extra_Salon'].tolist()
                    st.session_state['demanda'][d]['c_b'] = df_dia['Cmds_Barra'].tolist()
                    st.session_state['demanda'][d]['e_b'] = df_dia['Extra_Barra'].tolist()
                    
            st.session_state['last_upload'] = uploaded_file.name
            st.rerun() 
        except Exception as e:
            st.error(f"Error al leer el Excel. Asegúrate de no borrar columnas. Detalles: {e}")

st.divider()

# --- BARRA LATERAL ---
st.sidebar.header("💰 1. Variables Globales")
max_nomina_pct = st.sidebar.slider("Tope Máximo de Nómina (%)", min_value=10.0, max_value=40.0, value=st.session_state['tope'])
st.session_state['tope'] = max_nomina_pct

st.sidebar.header("👔 2. Fijos (Para toda la semana)")
sup_m = st.sidebar.checkbox("Supervisor Matutino", value=st.session_state['sup_m'], key="sm")
sup_i = st.sidebar.checkbox("Supervisor Intermedio", value=st.session_state['sup_i'], key="si")
sup_v = st.sidebar.checkbox("Supervisor Vespertino", value=st.session_state['sup_v'], key="sv")

caja_m = st.sidebar.checkbox("Cajero Matutino", value=st.session_state['caj_m'], key="cm")
caja_i = st.sidebar.checkbox("Cajero Intermedio", value=st.session_state['caj_i'], key="ci")
caja_v = st.sidebar.checkbox("Cajero Vespertino", value=st.session_state['caj_v'], key="cv")

hos_m = st.sidebar.checkbox("Hostess Matutino", value=st.session_state['hos_m'], key="hm")
hos_i = st.sidebar.checkbox("Hostess Intermedio", value=st.session_state['hos_i'], key="hi")
hos_v = st.sidebar.checkbox("Hostess Vespertino", value=st.session_state['hos_v'], key="hv")

# --- CONFIGURACIÓN MAESTRA ---
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

# Extraer variables maestras 
s_coc, s_ven, s_bar = config_data['s_coc'], config_data['s_ven'], config_data['s_bar']
s_sup, s_caj, s_hos = config_data['s_sup'], config_data['s_caj'], config_data['s_hos']
c_coc, c_sal, c_bar = config_data['c_coc'], config_data['c_sal'], config_data['c_bar']

# --- ÁREA PRINCIPAL: DEMANDA SEMANAL (PESTAÑAS) ---
st.subheader("📋 3. Proyección Diaria (Carga de Trabajo y Ventas)")
st.write("Navega por las pestañas para validar la venta y comandas de cada día.")

tabs = st.tabs(dias_semana)

for idx, d in enumerate(dias_semana):
    with tabs[idx]:
        c1, c2 = st.columns([1, 3])
        with c1:
            st.session_state['ventas'][d] = st.number_input(f"Venta Proyectada {d} ($)", value=st.session_state['ventas'][d], step=500.0, key=f"v_{d}")
            pto_dia = st.session_state['ventas'][d] * (max_nomina_pct / 100)
            st.info(f"Presupuesto del Día: *$ {pto_dia:,.2f}*")
        
        with c2:
            st.markdown(f"*Carga de Trabajo: {d}*")
            cols = st.columns(7)
            cols[0].markdown("*Horario*")
            cols[1].markdown("*Cmds Cocina*")
            cols[2].markdown("*Ext Cocina (hrs)*")
            cols[3].markdown("*Cmds Salón*")
            cols[4].markdown("*Ext Salón (hrs)*")
            cols[5].markdown("*Cmds Barra*")
            cols[6].markdown("*Ext Barra (hrs)*")
            
            for i in range(5):
                cc = st.columns(7)
                cc[0].write(bloques[i][:11]) # Acorta el nombre del bloque
                st.session_state['demanda'][d]['c_c'][i] = cc[1].number_input("cc", value=float(st.session_state['demanda'][d]['c_c'][i]), step=5.0, key=f"cc_{d}_{i}", label_visibility="collapsed")
                st.session_state['demanda'][d]['e_c'][i] = cc[2].number_input("ec", value=float(st.session_state['demanda'][d]['e_c'][i]), step=0.5, key=f"ec_{d}_{i}", label_visibility="collapsed")
                st.session_state['demanda'][d]['c_s'][i] = cc[3].number_input("cs", value=float(st.session_state['demanda'][d]['c_s'][i]), step=5.0, key=f"cs_{d}_{i}", label_visibility="collapsed")
                st.session_state['demanda'][d]['e_s'][i] = cc[4].number_input("es", value=float(st.session_state['demanda'][d]['e_s'][i]), step=0.5, key=f"es_{d}_{i}", label_visibility="collapsed")
                st.session_state['demanda'][d]['c_b'][i] = cc[5].number_input("cb", value=float(st.session_state['demanda'][d]['c_b'][i]), step=5.0, key=f"cb_{d}_{i}", label_visibility="collapsed")
                st.session_state['demanda'][d]['e_b'][i] = cc[6].number_input("eb", value=float(st.session_state['demanda'][d]['e_b'][i]), step=0.5, key=f"eb_{d}_{i}", label_visibility="collapsed")

st.divider()

# --- OPTIMIZACIÓN SEMANAL ---
if st.button("🚀 Calcular Plantilla Semanal", type="primary"):
    
    resultados_diarios = {}
    costo_total_semana = 0
    venta_total_semana = sum(st.session_state['ventas'].values())
    dias_inviables = []
    
    capacidades = {'Cocina': c_coc, 'Salon': c_sal, 'Barra': c_bar}
    roles = ['Cocina', 'Salon', 'Barra']
    turnos = ['M', 'I', 'V']
    
    qty_caja_m, qty_caja_i, qty_caja_v = (1 if caja_m else 0), (1 if caja_i else 0), (1 if caja_v else 0)
    qty_sup_m, qty_sup_i, qty_sup_v = (1 if sup_m else 0), (1 if sup_i else 0), (1 if sup_v else 0)
    qty_hos_m, qty_hos_i, qty_hos_v = (1 if hos_m else 0), (1 if hos_i else 0), (1 if hos_v else 0)
    
    costo_fijo_diario = ((qty_caja_m + qty_caja_i + qty_caja_v) * s_caj) + \
                        ((qty_sup_m + qty_sup_i + qty_sup_v) * s_sup) + \
                        ((qty_hos_m + qty_hos_i + qty_hos_v) * s_hos)
    
    # Bucle para resolver CADA DÍA independiente
    for d in dias_semana:
        modelo = pl.LpProblem(f"Optimizacion_{d}", pl.LpMinimize)
        vars_personal = pl.LpVariable.dicts(f"Pers_{d}", [(r, t) for r in roles for t in turnos], lowBound=0, cat='Integer')
        
        # Objetivo: Minimizar personal
        modelo += pl.lpSum([vars_personal[(r, t)] for r in roles for t in turnos])
        
        demandas = {'Cocina': st.session_state['demanda'][d]['c_c'], 'Salon': st.session_state['demanda'][d]['c_s'], 'Barra': st.session_state['demanda'][d]['c_b']}
        extras = {'Cocina': st.session_state['demanda'][d]['e_c'], 'Salon': st.session_state['demanda'][d]['e_s'], 'Barra': st.session_state['demanda'][d]['e_b']}
        
        # Restricciones Operativas
        for r in roles:
            for i in range(5):
                req_horas = (demandas[r][i] / capacidades[r]) + extras[r][i]
                if i == 0:   gente = vars_personal[(r, 'M')]
                elif i == 1: gente = vars_personal[(r, 'M')] + vars_personal[(r, 'I')]
                elif i == 2: gente = vars_personal[(r, 'M')] + vars_personal[(r, 'I')] + vars_personal[(r, 'V')]
                elif i == 3: gente = vars_personal[(r, 'I')] + vars_personal[(r, 'V')]
                elif i == 4: gente = vars_personal[(r, 'V')]
                modelo += (gente * horas_por_bloque[i]) >= req_horas

        # Restricción Financiera Diaria
        presupuesto_diario = st.session_state['ventas'][d] * (max_nomina_pct / 100)
        costo_var = pl.lpSum([
            vars_personal[('Cocina', t)] * s_coc +
            vars_personal[('Salon', t)] * s_ven +
            vars_personal[('Barra', t)] * s_bar 
            for t in turnos
        ])
        
        modelo += (costo_var + costo_fijo_diario) <= presupuesto_diario
        status = modelo.solve()
        
        if pl.LpStatus[status] == 'Optimal':
            c_dia = pl.value(costo_var) + costo_fijo_diario
            costo_total_semana += c_dia
            
            # Guardar el resultado del día
            resultados_diarios[d] = {
                'M': [vars_personal[('Cocina','M')].varValue, vars_personal[('Salon','M')].varValue, vars_personal[('Barra','M')].varValue, qty_caja_m, qty_sup_m, qty_hos_m],
                'I': [vars_personal[('Cocina','I')].varValue, vars_personal[('Salon','I')].varValue, vars_personal[('Barra','I')].varValue, qty_caja_i, qty_sup_i, qty_hos_i],
                'V': [vars_personal[('Cocina','V')].varValue, vars_personal[('Salon','V')].varValue, vars_personal[('Barra','V')].varValue, qty_caja_v, qty_sup_v, qty_hos_v],
                'Costo': c_dia
            }
        else:
            dias_inviables.append(d)

    # --- RESULTADOS ---
    if dias_inviables:
        st.error(f"⚠️ *Presupuesto Inviable en los siguientes días:* {', '.join(dias_inviables)}. \n El presupuesto de nómina de esos días no alcanza para cubrir la demanda. Aumenta la venta proyectada o el Tope de Nómina.")
    else:
        st.success("✅ ¡Semana Optimizada con Éxito!")
        
        pct_semanal_real = (costo_total_semana / venta_total_semana) * 100
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label="💰 Costo Nómina Semanal", value=f"$ {costo_total_semana:,.2f}")
        kpi2.metric(label="📈 % Nómina Semanal (Real)", value=f"{pct_semanal_real:.1f} %")
        kpi3.metric(label="🎯 Venta Total Esperada", value=f"$ {venta_total_semana:,.2f}")
        
        # --- TABLA MAESTRA SEMANAL ---
        st.subheader("📅 Tu Plantilla Maestra Semanal (Turnos a Contratar)")
        
        filas_maestras = []
        for d in dias_semana:
            # Turno Matutino
            filas_maestras.append({
                "Día": d, "Turno": "Matutino (10 a 18)", 
                "Cocineros": int(resultados_diarios[d]['M'][0]), "Salón": int(resultados_diarios[d]['M'][1]), "Barra": int(resultados_diarios[d]['M'][2]),
                "Cajero": resultados_diarios[d]['M'][3], "Supervisor": resultados_diarios[d]['M'][4], "Hostess": resultados_diarios[d]['M'][5],
                "Costo del Día": f"$ {resultados_diarios[d]['Costo']:,.2f}" # Solo lo mostramos en la primera línea del día
            })
            # Turno Intermedio
            filas_maestras.append({
                "Día": "", "Turno": "Intermedio (14 a 22)", 
                "Cocineros": int(resultados_diarios[d]['I'][0]), "Salón": int(resultados_diarios[d]['I'][1]), "Barra": int(resultados_diarios[d]['I'][2]),
                "Cajero": resultados_diarios[d]['I'][3], "Supervisor": resultados_diarios[d]['I'][4], "Hostess": resultados_diarios[d]['I'][5],
                "Costo del Día": "" 
            })
            # Turno Vespertino
            filas_maestras.append({
                "Día": "", "Turno": "Vespertino (17 a 01)", 
                "Cocineros": int(resultados_diarios[d]['V'][0]), "Salón": int(resultados_diarios[d]['V'][1]), "Barra": int(resultados_diarios[d]['V'][2]),
                "Cajero": resultados_diarios[d]['V'][3], "Supervisor": resultados_diarios[d]['V'][4], "Hostess": resultados_diarios[d]['V'][5],
                "Costo del Día": "" 
            })
            
        st.dataframe(pd.DataFrame(filas_maestras).set_index("Día"), use_container_width=True)
        
        # --- RESUMEN EJECUTIVO SEMANAL ---
        st.subheader("💡 Resumen Ejecutivo Semanal")
        st.markdown(f"""
        ✔️ *Venta Semanal:* Tienes una proyección de ventas totales de *$ {venta_total_semana:,.2f}* para toda la semana.
        
        ✔️ *Tope Financiero:* Con tu límite configurado del *{max_nomina_pct:.1f} %* , el sistema cuidó matemáticamente que NINGÚN DÍA superara su presupuesto individual.
        
        ✔️ *Resultado Exitoso:* El costo total de tu plantilla de Domingo a Sábado será de *$ {costo_total_semana:,.2f}* . Esto promedia un *{pct_semanal_real:.1f} %* de nómina total semanal. ¡La operación y las finanzas están cubiertas y aseguradas para toda la semana! 🚀
        """)