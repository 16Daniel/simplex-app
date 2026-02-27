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

# --- INICIALIZAR VARIABLES EN MEMORIA (Para la carga del Excel) ---
if 'data_loaded' not in st.session_state:
    st.session_state.update({
        'venta': 15000.0, 'tope': 20.0,
        'sup_m': False, 'sup_i': True, 'sup_v': False,
        'caj_m': True, 'caj_i': False, 'caj_v': True,
        'hos_m': False, 'hos_i': True, 'hos_v': True,
        'data_loaded': True, 'last_upload': None
    })
    st.session_state['dem_c'] = [15.0, 30.0, 20.0, 60.0, 25.0]
    st.session_state['ext_c'] = [1.0, 0.0, 0.0, 0.5, 1.5]
    st.session_state['dem_s'] = [20.0, 45.0, 30.0, 85.0, 30.0]
    st.session_state['ext_s'] = [1.0, 0.0, 0.0, 0.5, 1.5]
    st.session_state['dem_b'] = [5.0, 20.0, 15.0, 70.0, 40.0]
    st.session_state['ext_b'] = [1.0, 0.0, 0.0, 0.5, 1.5]

# --- FUNCIÓN PARA CREAR EL MACHOTE EXCEL (Simplificado) ---
def generar_machote():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        var_data = {
            "Parametro": [
                "Venta Proyectada ($)", "Tope Maximo Nomina (%)", 
                "Supervisor Matutino (Si/No)", "Supervisor Intermedio (Si/No)", "Supervisor Vespertino (Si/No)",
                "Cajero Matutino (Si/No)", "Cajero Intermedio (Si/No)", "Cajero Vespertino (Si/No)",
                "Hostess Matutino (Si/No)", "Hostess Intermedio (Si/No)", "Hostess Vespertino (Si/No)"
            ],
            "Valor": [15000, 20, "No", "Si", "No", "Si", "No", "Si", "No", "Si", "Si"]
        }
        pd.DataFrame(var_data).to_excel(writer, sheet_name="Variables", index=False)
        
        dem_data = {
            "Bloque": ["10 a 14 hrs", "14 a 17 hrs", "17 a 18 hrs", "18 a 22 hrs", "22 a 01 hrs"],
            "Cmd_Cocina": [15, 30, 20, 60, 25], "Ext_Cocina": [1.0, 0.0, 0.0, 0.5, 1.5],
            "Cmd_Salon":  [20, 45, 30, 85, 30], "Ext_Salon":  [1.0, 0.0, 0.0, 0.5, 1.5],
            "Cmd_Barra":  [5,  20, 15, 70, 40], "Ext_Barra":  [1.0, 0.0, 0.0, 0.5, 1.5]
        }
        pd.DataFrame(dem_data).to_excel(writer, sheet_name="Demanda", index=False)
    return output.getvalue()

# --- ENCABEZADO Y CARGA MASIVA ---
st.title("🍔 SIMPLEX: NÓMINA Y TURNOS IDEALES")
st.markdown("Carga tu proyección de ventas y comandas. El sistema usará tus capacidades y salarios guardados para optimizar tu nómina.")

col_down, col_up = st.columns([1, 2])
with col_down:
    st.info("⬇️ *Paso 1: Descarga la plantilla (Simplificada)*")
    st.download_button(label="📥 Descargar Machote de Excel", data=generar_machote(), file_name="Machote_Planeacion.xlsx", mime="application/vnd.ms-excel")

with col_up:
    uploaded_file = st.file_uploader("⬆️ *Paso 2: Sube tu Machote lleno aquí*", type=["xlsx"])
    if uploaded_file and uploaded_file.name != st.session_state['last_upload']:
        try:
            df_v = pd.read_excel(uploaded_file, sheet_name="Variables")
            df_d = pd.read_excel(uploaded_file, sheet_name="Demanda")
            v = df_v['Valor'].tolist()
            st.session_state.update({
                'venta': float(v[0]), 'tope': float(v[1]),
                'sup_m': str(v[2]).strip().lower() == 'si', 'sup_i': str(v[3]).strip().lower() == 'si', 'sup_v': str(v[4]).strip().lower() == 'si',
                'caj_m': str(v[5]).strip().lower() == 'si', 'caj_i': str(v[6]).strip().lower() == 'si', 'caj_v': str(v[7]).strip().lower() == 'si',
                'hos_m': str(v[8]).strip().lower() == 'si', 'hos_i': str(v[9]).strip().lower() == 'si', 'hos_v': str(v[10]).strip().lower() == 'si',
            })
            st.session_state['dem_c'] = df_d['Cmd_Cocina'].tolist()
            st.session_state['ext_c'] = df_d['Ext_Cocina'].tolist()
            st.session_state['dem_s'] = df_d['Cmd_Salon'].tolist()
            st.session_state['ext_s'] = df_d['Ext_Salon'].tolist()
            st.session_state['dem_b'] = df_d['Cmd_Barra'].tolist()
            st.session_state['ext_b'] = df_d['Ext_Barra'].tolist()
            st.session_state['last_upload'] = uploaded_file.name
            st.rerun() 
        except Exception as e:
            st.error(f"Error al leer el Excel. Detalles: {e}")

st.divider()

# --- BARRA LATERAL ---
st.sidebar.header("💰 1. Variables Financieras (Diarias)")
venta_proyectada = st.sidebar.number_input("Venta Proyectada del Día ($)", value=st.session_state['venta'], step=500.0)
max_nomina_pct = st.sidebar.slider("Tope Máximo de Nómina (%)", min_value=10.0, max_value=40.0, value=st.session_state['tope'])
presupuesto_nomina = venta_proyectada * (max_nomina_pct / 100)
st.sidebar.success(f"Presupuesto máximo: *$ {presupuesto_nomina:,.2f}*")

st.sidebar.header("👔 2. Personal Fijo (Turnos)")
sup_m = st.sidebar.checkbox("Supervisor Matutino", value=st.session_state['sup_m'], key="sm")
sup_i = st.sidebar.checkbox("Supervisor Intermedio", value=st.session_state['sup_i'], key="si")
sup_v = st.sidebar.checkbox("Supervisor Vespertino", value=st.session_state['sup_v'], key="sv")

caja_m = st.sidebar.checkbox("Cajero Matutino", value=st.session_state['caj_m'], key="cm")
caja_i = st.sidebar.checkbox("Cajero Intermedio", value=st.session_state['caj_i'], key="ci")
caja_v = st.sidebar.checkbox("Cajero Vespertino", value=st.session_state['caj_v'], key="cv")

hos_m = st.sidebar.checkbox("Hostess Matutino", value=st.session_state['hos_m'], key="hm")
hos_i = st.sidebar.checkbox("Hostess Intermedio", value=st.session_state['hos_i'], key="hi")
hos_v = st.sidebar.checkbox("Hostess Vespertino", value=st.session_state['hos_v'], key="hv")

# --- CONFIGURACIÓN MAESTRA (OCULTA) ---
st.sidebar.markdown("---")
st.sidebar.header("🔐 Configuración Maestra")
st.sidebar.write("Variables fijas. Solo modificar con autorización.")
pwd = st.sidebar.text_input("Contraseña:", type="password")

if pwd == "M@5terkey":
    st.sidebar.success("Acceso Concedido")
    with st.sidebar.expander("Ajustar Salarios y Capacidades", expanded=True):
        new_s_coc = st.number_input("Salario Cocinero ($)", value=config_data['s_coc'])
        new_s_ven = st.number_input("Salario Vendedor ($)", value=config_data['s_ven'])
        new_s_bar = st.number_input("Salario Barra ($)", value=config_data['s_bar'])
        new_s_sup = st.number_input("Salario Supervisor ($)", value=config_data['s_sup'])
        new_s_caj = st.number_input("Salario Cajero ($)", value=config_data['s_caj'])
        new_s_hos = st.number_input("Salario Hostess ($)", value=config_data['s_hos'])
        
        new_c_coc = st.number_input("Capacidad Cocina (cmd/hr)", value=config_data['c_coc'])
        new_c_sal = st.number_input("Capacidad Salón (cmd/hr)", value=config_data['c_sal'])
        new_c_bar = st.number_input("Capacidad Barra (cmd/hr)", value=config_data['c_bar'])
        
        if st.button("💾 Guardar Cambios"):
            config_data.update({
                's_coc': new_s_coc, 's_ven': new_s_ven, 's_bar': new_s_bar,
                's_sup': new_s_sup, 's_caj': new_s_caj, 's_hos': new_s_hos,
                'c_coc': new_c_coc, 'c_sal': new_c_sal, 'c_bar': new_c_bar
            })
            save_config(config_data)
            st.sidebar.info("¡Configuración guardada! Aplicará para todos los cálculos.")

# Extraer variables maestras para el cálculo
s_coc, s_ven, s_bar = config_data['s_coc'], config_data['s_ven'], config_data['s_bar']
s_sup, s_caj, s_hos = config_data['s_sup'], config_data['s_caj'], config_data['s_hos']
c_coc, c_sal, c_bar = config_data['c_coc'], config_data['c_sal'], config_data['c_bar']

# --- ÁREA PRINCIPAL: DEMANDA ---
st.subheader("📋 3. Proyección de Carga de Trabajo por Área")

bloques = ["10:00 a 14:00 (4 hrs)", "14:00 a 17:00 (3 hrs)", "17:00 a 18:00 (1 hr)", "18:00 a 22:00 (4 hrs)", "22:00 a 01:00 (3 hrs)"]
horas_por_bloque = [4, 3, 1, 4, 3]

dem_c, ext_c, dem_s, ext_s, dem_b, ext_b = [], [], [], [], [], []

cols = st.columns(7)
cols[0].markdown("*Horario (hrs)*")
cols[1].markdown("*Cmds Cocina*")
cols[2].markdown("*Extra Cocina (hrs)*")
cols[3].markdown("*Cmds Salón*")
cols[4].markdown("*Extra Salón (hrs)*")
cols[5].markdown("*Cmds Barra*")
cols[6].markdown("*Extra Barra (hrs)*")

for i in range(5):
    with st.container():
        cc = st.columns(7)
        cc[0].write(bloques[i])
        dem_c.append(cc[1].number_input(f"cc{i}", value=float(st.session_state['dem_c'][i]), step=5.0, label_visibility="collapsed"))
        ext_c.append(cc[2].number_input(f"ec{i}", value=float(st.session_state['ext_c'][i]), step=0.5, label_visibility="collapsed"))
        dem_s.append(cc[3].number_input(f"cs{i}", value=float(st.session_state['dem_s'][i]), step=5.0, label_visibility="collapsed"))
        ext_s.append(cc[4].number_input(f"es{i}", value=float(st.session_state['ext_s'][i]), step=0.5, label_visibility="collapsed"))
        dem_b.append(cc[5].number_input(f"cb{i}", value=float(st.session_state['dem_b'][i]), step=5.0, label_visibility="collapsed"))
        ext_b.append(cc[6].number_input(f"eb{i}", value=float(st.session_state['ext_b'][i]), step=0.5, label_visibility="collapsed"))

st.divider()

# --- OPTIMIZACIÓN ---
if st.button("🚀 Calcular Plantilla Óptima", type="primary"):
    modelo = pl.LpProblem("Optimizacion_Alitas", pl.LpMinimize)
    roles = ['Cocina', 'Salon', 'Barra']
    turnos = ['M', 'I', 'V']
    
    vars_personal = pl.LpVariable.dicts("Pers", [(r, t) for r in roles for t in turnos], lowBound=0, cat='Integer')
    modelo += pl.lpSum([vars_personal[(r, t)] for r in roles for t in turnos])
    
    capacidades = {'Cocina': c_coc, 'Salon': c_sal, 'Barra': c_bar}
    demandas = {'Cocina': dem_c, 'Salon': dem_s, 'Barra': dem_b}
    extras = {'Cocina': ext_c, 'Salon': ext_s, 'Barra': ext_b}
    
    for r in roles:
        cap, dem, ext = capacidades[r], demandas[r], extras[r]
        for i in range(5):
            req_horas = (dem[i] / cap) + ext[i]
            if i == 0:   gente = vars_personal[(r, 'M')]
            elif i == 1: gente = vars_personal[(r, 'M')] + vars_personal[(r, 'I')]
            elif i == 2: gente = vars_personal[(r, 'M')] + vars_personal[(r, 'I')] + vars_personal[(r, 'V')]
            elif i == 3: gente = vars_personal[(r, 'I')] + vars_personal[(r, 'V')]
            elif i == 4: gente = vars_personal[(r, 'V')]
            modelo += (gente * horas_por_bloque[i]) >= req_horas

    costo_fijo = 0
    qty_caja_m, qty_caja_i, qty_caja_v = (1 if caja_m else 0), (1 if caja_i else 0), (1 if caja_v else 0)
    qty_sup_m, qty_sup_i, qty_sup_v = (1 if sup_m else 0), (1 if sup_i else 0), (1 if sup_v else 0)
    qty_hos_m, qty_hos_i, qty_hos_v = (1 if hos_m else 0), (1 if hos_i else 0), (1 if hos_v else 0)
    
    costo_fijo += (qty_caja_m + qty_caja_i + qty_caja_v) * s_caj
    costo_fijo += (qty_sup_m + qty_sup_i + qty_sup_v) * s_sup
    costo_fijo += (qty_hos_m + qty_hos_i + qty_hos_v) * s_hos
    
    costo_var = pl.lpSum([
        vars_personal[('Cocina', t)] * s_coc +
        vars_personal[('Salon', t)] * s_ven +
        vars_personal[('Barra', t)] * s_bar 
        for t in turnos
    ])
    
    modelo += (costo_var + costo_fijo) <= presupuesto_nomina
    status = modelo.solve()
    
    if pl.LpStatus[status] == 'Optimal':
        st.success("✅ ¡Cálculo Exitoso! Aquí tienes tu plantilla óptima:")
        
        costo_total = pl.value(costo_var) + costo_fijo
        pct_real = (costo_total / venta_proyectada) * 100
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label="💰 Costo Total de Nómina", value=f"$ {costo_total:,.2f}")
        kpi2.metric(label="📈 % de la Venta Proyectada", value=f"{pct_real:.1f} %")
        kpi3.metric(label="🎯 Presupuesto Máximo", value=f"$ {presupuesto_nomina:,.2f}")
        
        def fmt(qty, price):
            return f"{int(qty)} ($ {int(qty) * price:,.2f})"

        c_m, c_i, c_v = int(vars_personal[('Cocina', 'M')].varValue), int(vars_personal[('Cocina', 'I')].varValue), int(vars_personal[('Cocina', 'V')].varValue)
        s_m, s_i, s_v = int(vars_personal[('Salon', 'M')].varValue), int(vars_personal[('Salon', 'I')].varValue), int(vars_personal[('Salon', 'V')].varValue)
        b_m, b_i, b_v = int(vars_personal[('Barra', 'M')].varValue), int(vars_personal[('Barra', 'I')].varValue), int(vars_personal[('Barra', 'V')].varValue)
        
        tot_c, tot_s, tot_b = c_m + c_i + c_v, s_m + s_i + s_v, b_m + b_i + b_v
        tot_caja, tot_sup, tot_hos = qty_caja_m + qty_caja_i + qty_caja_v, qty_sup_m + qty_sup_i + qty_sup_v, qty_hos_m + qty_hos_i + qty_hos_v
        
        resultados = {
            "Turno": ["Matutino (10 a 18 hrs)", "Intermedio (14 a 22 hrs)", "Vespertino (17 a 01 hrs)", "🔥 TOTAL DEL DÍA 🔥"],
            "Cocinero": [fmt(c_m, s_coc), fmt(c_i, s_coc), fmt(c_v, s_coc), fmt(tot_c, s_coc)],
            "Vendedor (Salón)": [fmt(s_m, s_ven), fmt(s_i, s_ven), fmt(s_v, s_ven), fmt(tot_s, s_ven)],
            "Barra": [fmt(b_m, s_bar), fmt(b_i, s_bar), fmt(b_v, s_bar), fmt(tot_b, s_bar)],
            "Cajero": [fmt(qty_caja_m, s_caj), fmt(qty_caja_i, s_caj), fmt(qty_caja_v, s_caj), fmt(tot_caja, s_caj)],
            "Supervisor": [fmt(qty_sup_m, s_sup), fmt(qty_sup_i, s_sup), fmt(qty_sup_v, s_sup), fmt(tot_sup, s_sup)],
            "Hostess": [fmt(qty_hos_m, s_hos), fmt(qty_hos_i, s_hos), fmt(qty_hos_v, s_hos), fmt(tot_hos, s_hos)]
        }
        st.table(pd.DataFrame(resultados).set_index("Turno"))
        
        st.subheader("💡 Resumen Ejecutivo")
        st.markdown(f"""
        ✔️ *Presupuesto Disponible:* Tienes un límite de *$ {presupuesto_nomina:,.2f}* . Esto equivale al *{max_nomina_pct:.1f} %* de tu venta proyectada de *$ {venta_proyectada:,.2f}* .
        
        ✔️ *Costo Fijo (Administrativo):* Separamos *$ {costo_fijo:,.2f}* para pagar a Supervisores, Cajeros y Hostess en los turnos que elegiste.
        
        ✔️ *Costo Variable (Operativo):* Con el dinero restante, el sistema armó la plantilla exacta para Cocina, Salón y Barra con un costo de *$ {pl.value(costo_var):,.2f}* .
        
        ✔️ *Resultado Exitoso:* El costo total de tu nómina planeada es de *$ {costo_total:,.2f}* . Representa exactamente el *{pct_real:.1f} %* de tu venta. ¡Lograste la meta! 🚀
        """)
        
        st.divider()

        # --- NUEVO GRÁFICO: EL PULSO DEL RESTAURANTE (CARGA DE TRABAJO) ---
        st.subheader("🌋 El Pulso del Restaurante (Volumen de Comandas)")
        st.info("💡 *¿Qué representa este gráfico?* \n Muestra el volumen bruto de comandas (el Rush) a lo largo del día. Fíjate en el punto más alto de la montaña: es el cuello de botella. El sistema justifica la contratación de tu turno Intermedio precisamente para cubrir y aplastar esta montaña sin que el servicio colapse.")
        
        nombres_bloques_cortos = ['10-14 hrs', '14-17 hrs', '17-18 hrs', '18-22 hrs', '22-01 hrs']
        df_rush = pd.DataFrame({
            'Bloque Horario': nombres_bloques_cortos * 3,
            'Comandas': dem_c + dem_s + dem_b,
            'Área': ['Cocina']*5 + ['Salón']*5 + ['Barra']*5
        })
        fig_rush = px.area(df_rush, x='Bloque Horario', y='Comandas', color='Área', 
                           title="La Montaña Rusa de tu Operación",
                           color_discrete_map={'Cocina': '#FF7F0E', 'Salón': '#1F77B4', 'Barra': '#2CA02C'})
        st.plotly_chart(fig_rush, use_container_width=True)

        # --- GRÁFICOS DE COBERTURA ---
        st.subheader("📊 Cobertura por Bloque (Personal vs Trabajo)")
        st.info("💡 *¿Cómo leer estos gráficos?* \n * *Barra Roja:* Es la exigencia de tu operación (las horas necesarias para sacar comandas + limpieza). \n * *Barra Verde:* Es la capacidad del personal que el sistema te asignó. \n * *La Regla de Oro:* Mientras tu barra verde sea igual o ligeramente más alta que la roja, tu operación está a salvo. Si sobra mucha barra verde, el sistema evitó contratar más gente para no quemar tu presupuesto de nómina.")
        
        tab1, tab2, tab3 = st.tabs(["🔥 Cocina", "🏃 Salón", "🍺 Barra"])
        
        def generar_grafico(rol, tab_obj):
            req_b, prov_b = [], []
            for i in range(5):
                req_b.append(round((demandas[rol][i] / capacidades[rol]) + extras[rol][i], 1))
                if i == 0:   g = vars_personal[(rol, 'M')].varValue
                elif i == 1: g = vars_personal[(rol, 'M')].varValue + vars_personal[(rol, 'I')].varValue
                elif i == 2: g = vars_personal[(rol, 'M')].varValue + vars_personal[(rol, 'I')].varValue + vars_personal[(rol, 'V')].varValue
                elif i == 3: g = vars_personal[(rol, 'I')].varValue + vars_personal[(rol, 'V')].varValue
                elif i == 4: g = vars_personal[(rol, 'V')].varValue
                prov_b.append(round(g * horas_por_bloque[i], 1))
            
            df_plot = pd.DataFrame({'Bloque Horario': nombres_bloques_cortos * 2, 'Horas': req_b + prov_b, 'Indicador': ['Horas NECESARIAS (Demanda + Extra)']*5 + ['Horas PROGRAMADAS (Tu Personal)']*5})
            fig = px.bar(df_plot, x='Bloque Horario', y='Horas', color='Indicador', barmode='group', text_auto='.1f', color_discrete_map={'Horas NECESARIAS (Demanda + Extra)': '#d62728', 'Horas PROGRAMADAS (Tu Personal)': '#2ca02c'})
            fig.update_layout(title=f"Balance de Horas en {rol}", xaxis_title="Bloques de Horario", yaxis_title="Cantidad de Horas-Hombre (hrs)", legend_title=None, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            tab_obj.plotly_chart(fig, use_container_width=True)

        generar_grafico('Cocina', tab1)
        generar_grafico('Salon', tab2)
        generar_grafico('Barra', tab3)

    else:
        st.error(f"⚠️ *Inviable:* El presupuesto de $ {presupuesto_nomina:,.2f} no alcanza para pagar la demanda ingresada. Sube la proyección de ventas ($) o el % de nómina.")