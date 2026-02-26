import streamlit as st
import pulp as pl
import pandas as pd
import plotly.express as px
import io

# Configuración de la página
st.set_page_config(page_title="Simplex: Nómina y Turnos Ideales", layout="wide")

# --- INICIALIZAR VARIABLES EN MEMORIA (Para la carga del Excel) ---
if 'data_loaded' not in st.session_state:
    st.session_state.update({
        'venta': 15000.0, 'tope': 20.0,
        's_coc': 350.0, 's_ven': 300.0, 's_bar': 320.0, 's_sup': 500.0, 's_caj': 300.0, 's_hos': 250.0,
        'c_coc': 8, 'c_sal': 12, 'c_bar': 15,
        'sup_m': False, 'sup_i': True, 'sup_v': False,
        'caj_m': True, 'caj_i': False, 'caj_v': True,
        'hos_m': False, 'hos_i': True, 'hos_v': True,
        'data_loaded': True, 'last_upload': None
    })
    # Listas de demanda por defecto [Bloque 1, B2, B3, B4, B5]
    st.session_state['dem_c'] = [15.0, 30.0, 20.0, 60.0, 25.0]
    st.session_state['ext_c'] = [1.0, 0.0, 0.0, 0.5, 1.5]
    st.session_state['dem_s'] = [20.0, 45.0, 30.0, 85.0, 30.0]
    st.session_state['ext_s'] = [1.0, 0.0, 0.0, 0.5, 1.5]
    st.session_state['dem_b'] = [5.0, 20.0, 15.0, 70.0, 40.0]
    st.session_state['ext_b'] = [1.0, 0.0, 0.0, 0.5, 1.5]

# --- FUNCIÓN PARA CREAR EL MACHOTE EXCEL ---
def generar_machote():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Pestaña 1: Variables Generales
        var_data = {
            "Parametro": [
                "Venta Proyectada ($)", "Tope Maximo Nomina (%)", 
                "Salario Cocinero ($)", "Salario Vendedor ($)", "Salario Barra ($)",
                "Salario Supervisor ($)", "Salario Cajero ($)", "Salario Hostess ($)",
                "Capacidad Cocina (cmd/hr)", "Capacidad Salon (cmd/hr)", "Capacidad Barra (cmd/hr)",
                "Supervisor Matutino (Si/No)", "Supervisor Intermedio (Si/No)", "Supervisor Vespertino (Si/No)",
                "Cajero Matutino (Si/No)", "Cajero Intermedio (Si/No)", "Cajero Vespertino (Si/No)",
                "Hostess Matutino (Si/No)", "Hostess Intermedio (Si/No)", "Hostess Vespertino (Si/No)"
            ],
            "Valor": [
                15000, 20, 350, 300, 320, 500, 300, 250, 8, 12, 15,
                "No", "Si", "No", "Si", "No", "Si", "No", "Si", "Si"
            ]
        }
        pd.DataFrame(var_data).to_excel(writer, sheet_name="Variables", index=False)
        
        # Pestaña 2: Demanda
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
st.markdown("LLena los datos manualmente o usa la *Carga Rápida por Excel* para automatizar el proceso. Revisa tus números y presiona el botón al final para calcular.")

col_down, col_up = st.columns([1, 2])
with col_down:
    st.info("⬇️ *Paso 1: Descarga la plantilla*")
    st.download_button(label="📥 Descargar Machote de Excel", data=generar_machote(), file_name="Machote_Planeacion.xlsx", mime="application/vnd.ms-excel")

with col_up:
    uploaded_file = st.file_uploader("⬆️ *Paso 2: Sube tu Machote lleno aquí*", type=["xlsx"])
    if uploaded_file and uploaded_file.name != st.session_state['last_upload']:
        try:
            # Leer excel
            df_v = pd.read_excel(uploaded_file, sheet_name="Variables")
            df_d = pd.read_excel(uploaded_file, sheet_name="Demanda")
            
            # Mapear Variables
            v = df_v['Valor'].tolist()
            st.session_state.update({
                'venta': float(v[0]), 'tope': float(v[1]),
                's_coc': float(v[2]), 's_ven': float(v[3]), 's_bar': float(v[4]),
                's_sup': float(v[5]), 's_caj': float(v[6]), 's_hos': float(v[7]),
                'c_coc': int(v[8]), 'c_sal': int(v[9]), 'c_bar': int(v[10]),
                'sup_m': str(v[11]).strip().lower() == 'si', 'sup_i': str(v[12]).strip().lower() == 'si', 'sup_v': str(v[13]).strip().lower() == 'si',
                'caj_m': str(v[14]).strip().lower() == 'si', 'caj_i': str(v[15]).strip().lower() == 'si', 'caj_v': str(v[16]).strip().lower() == 'si',
                'hos_m': str(v[17]).strip().lower() == 'si', 'hos_i': str(v[18]).strip().lower() == 'si', 'hos_v': str(v[19]).strip().lower() == 'si',
            })
            
            # Mapear Demanda
            st.session_state['dem_c'] = df_d['Cmd_Cocina'].tolist()
            st.session_state['ext_c'] = df_d['Ext_Cocina'].tolist()
            st.session_state['dem_s'] = df_d['Cmd_Salon'].tolist()
            st.session_state['ext_s'] = df_d['Ext_Salon'].tolist()
            st.session_state['dem_b'] = df_d['Cmd_Barra'].tolist()
            st.session_state['ext_b'] = df_d['Ext_Barra'].tolist()
            
            st.session_state['last_upload'] = uploaded_file.name
            st.rerun() 
        except Exception as e:
            st.error(f"Error al leer el Excel. Verifica que no cambiaste el formato original. Detalles: {e}")

st.divider()

# --- BARRA LATERAL: FINANZAS Y SALARIOS ---
st.sidebar.header("💰 1. Variables Financieras")
venta_proyectada = st.sidebar.number_input("Venta Proyectada del Día ($)", value=st.session_state['venta'], step=500.0)
max_nomina_pct = st.sidebar.slider("Tope Máximo de Nómina (%)", min_value=10.0, max_value=40.0, value=st.session_state['tope'])
presupuesto_nomina = venta_proyectada * (max_nomina_pct / 100)
st.sidebar.success(f"Presupuesto máximo: *$ {presupuesto_nomina:,.2f}*")

st.sidebar.header("💸 2. Salarios por Turno ($)")
salario_cocinero = st.sidebar.number_input("Cocinero ($)", value=st.session_state['s_coc'], step=10.0)
salario_vendedor = st.sidebar.number_input("Vendedor/Mesero ($)", value=st.session_state['s_ven'], step=10.0)
salario_barra = st.sidebar.number_input("Barra ($)", value=st.session_state['s_bar'], step=10.0)
salario_sup = st.sidebar.number_input("Supervisor ($)", value=st.session_state['s_sup'], step=10.0)
salario_caja = st.sidebar.number_input("Cajero ($)", value=st.session_state['s_caj'], step=10.0)
salario_hostess = st.sidebar.number_input("Hostess ($)", value=st.session_state['s_hos'], step=10.0)

# Corrección de los keys duplicados aplicados aquí:
st.sidebar.header("👔 3. Supervisor")
sup_m = st.sidebar.checkbox("Turno Matutino", value=st.session_state['sup_m'], key="sup_mat")
sup_i = st.sidebar.checkbox("Turno Intermedio", value=st.session_state['sup_i'], key="sup_int")
sup_v = st.sidebar.checkbox("Turno Vespertino", value=st.session_state['sup_v'], key="sup_ves")

st.sidebar.header("🧮 4. Cajero")
caja_m = st.sidebar.checkbox("Turno Matutino", value=st.session_state['caj_m'], key="caj_mat")
caja_i = st.sidebar.checkbox("Turno Intermedio", value=st.session_state['caj_i'], key="caj_int")
caja_v = st.sidebar.checkbox("Turno Vespertino", value=st.session_state['caj_v'], key="caj_ves")

st.sidebar.header("💁‍♀️ 5. Hostess")
hos_m = st.sidebar.checkbox("Turno Matutino", value=st.session_state['hos_m'], key="hos_mat")
hos_i = st.sidebar.checkbox("Turno Intermedio", value=st.session_state['hos_i'], key="hos_int")
hos_v = st.sidebar.checkbox("Turno Vespertino", value=st.session_state['hos_v'], key="hos_ves")

st.sidebar.header("⚡ 6. Capacidad Productiva")
cap_cocina = st.sidebar.number_input("Comandas Cocina / hr", value=st.session_state['c_coc'], step=1)
cap_salon = st.sidebar.number_input("Comandas Salón / hr", value=st.session_state['c_sal'], step=1)
cap_barra = st.sidebar.number_input("Comandas Barra / hr", value=st.session_state['c_bar'], step=1)

# --- ÁREA PRINCIPAL: DEMANDA ---
st.subheader("📋 7. Proyección de Carga de Trabajo por Área")
st.write("Verifica la información cargada. Si algo cambió, puedes modificarlo directamente en estas casillas antes de calcular.")

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
    
    capacidades = {'Cocina': cap_cocina, 'Salon': cap_salon, 'Barra': cap_barra}
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
    
    costo_fijo += (qty_caja_m + qty_caja_i + qty_caja_v) * salario_caja
    costo_fijo += (qty_sup_m + qty_sup_i + qty_sup_v) * salario_sup
    costo_fijo += (qty_hos_m + qty_hos_i + qty_hos_v) * salario_hostess
    
    costo_var = pl.lpSum([
        vars_personal[('Cocina', t)] * salario_cocinero +
        vars_personal[('Salon', t)] * salario_vendedor +
        vars_personal[('Barra', t)] * salario_barra 
        for t in turnos
    ])
    
    modelo += (costo_var + costo_fijo) <= presupuesto_nomina
    status = modelo.solve()
    
    if pl.LpStatus[status] == 'Optimal':
        st.success("✅ ¡Cálculo Exitoso! Aquí tienes tu plantilla óptima:")
        
        costo_total = pl.value(costo_var) + costo_fijo
        pct_real = (costo_total / venta_proyectada) * 100
        
        # --- MÉTRICAS VISUALES ---
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label="💰 Costo Total de Nómina", value=f"$ {costo_total:,.2f}")
        kpi2.metric(label="📈 % de la Venta Proyectada", value=f"{pct_real:.1f} %")
        kpi3.metric(label="🎯 Presupuesto Máximo", value=f"$ {presupuesto_nomina:,.2f}")
        
        # --- TABLA DE RESULTADOS ---
        def fmt(qty, price):
            return f"{int(qty)} ($ {int(qty) * price:,.2f})"

        c_m, c_i, c_v = int(vars_personal[('Cocina', 'M')].varValue), int(vars_personal[('Cocina', 'I')].varValue), int(vars_personal[('Cocina', 'V')].varValue)
        s_m, s_i, s_v = int(vars_personal[('Salon', 'M')].varValue), int(vars_personal[('Salon', 'I')].varValue), int(vars_personal[('Salon', 'V')].varValue)
        b_m, b_i, b_v = int(vars_personal[('Barra', 'M')].varValue), int(vars_personal[('Barra', 'I')].varValue), int(vars_personal[('Barra', 'V')].varValue)
        
        tot_c = c_m + c_i + c_v
        tot_s = s_m + s_i + s_v
        tot_b = b_m + b_i + b_v
        tot_caja = qty_caja_m + qty_caja_i + qty_caja_v
        tot_sup = qty_sup_m + qty_sup_i + qty_sup_v
        tot_hos = qty_hos_m + qty_hos_i + qty_hos_v
        
        resultados = {
            "Turno": ["Matutino (10 a 18 hrs)", "Intermedio (14 a 22 hrs)", "Vespertino (17 a 01 hrs)", "🔥 TOTAL DEL DÍA 🔥"],
            "Cocinero": [fmt(c_m, salario_cocinero), fmt(c_i, salario_cocinero), fmt(c_v, salario_cocinero), fmt(tot_c, salario_cocinero)],
            "Vendedor (Salón)": [fmt(s_m, salario_vendedor), fmt(s_i, salario_vendedor), fmt(s_v, salario_vendedor), fmt(tot_s, salario_vendedor)],
            "Barra": [fmt(b_m, salario_barra), fmt(b_i, salario_barra), fmt(b_v, salario_barra), fmt(tot_b, salario_barra)],
            "Cajero": [fmt(qty_caja_m, salario_caja), fmt(qty_caja_i, salario_caja), fmt(qty_caja_v, salario_caja), fmt(tot_caja, salario_caja)],
            "Supervisor": [fmt(qty_sup_m, salario_sup), fmt(qty_sup_i, salario_sup), fmt(qty_sup_v, salario_sup), fmt(tot_sup, salario_sup)],
            "Hostess": [fmt(qty_hos_m, salario_hostess), fmt(qty_hos_i, salario_hostess), fmt(qty_hos_v, salario_hostess), fmt(tot_hos, salario_hostess)]
        }
        st.table(pd.DataFrame(resultados).set_index("Turno"))
        
        # --- EXPLICACIÓN DIRECTA (100% BLINDADA) ---
        st.subheader("💡 Resumen Ejecutivo")
        
        st.markdown(f"""
        ✔️ *Presupuesto Disponible:* Tienes un límite de *$ {presupuesto_nomina:,.2f}* . Esto equivale al *{max_nomina_pct:.1f} %* de tu venta proyectada de *$ {venta_proyectada:,.2f}* .
        
        ✔️ *Costo Fijo (Administrativo):* Separamos *$ {costo_fijo:,.2f}* para pagar a Supervisores, Cajeros y Hostess en los turnos que elegiste.
        
        ✔️ *Costo Variable (Operativo):* Con el dinero restante, el sistema armó la plantilla exacta para Cocina, Salón y Barra con un costo de *$ {pl.value(costo_var):,.2f}* .
        
        ✔️ *Resultado Exitoso:* El costo total de tu nómina planeada es de *$ {costo_total:,.2f}* . Representa exactamente el *{pct_real:.1f} %* de tu venta. ¡Lograste la meta! 🚀
        """)
        
        # --- GRÁFICOS POR BLOQUE ---
        st.subheader("📊 Gráficas de Cobertura por Bloque (Personal vs Trabajo)")
        st.write("Estas gráficas te muestran, bloque por bloque, si las horas de trabajo que rinde tu personal superan a las horas que te exige la operación (comandas + extra).")
        
        nombres_bloques = ['10-14 hrs', '14-17 hrs', '17-18 hrs', '18-22 hrs', '22-01 hrs']
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
            
            df_plot = pd.DataFrame({'Bloque Horario': nombres_bloques * 2, 'Horas': req_b + prov_b, 'Indicador': ['Horas NECESARIAS (Demanda + Extra)']*5 + ['Horas PROGRAMADAS (Tu Personal)']*5})
            fig = px.bar(df_plot, x='Bloque Horario', y='Horas', color='Indicador', barmode='group', text_auto='.1f', color_discrete_map={'Horas NECESARIAS (Demanda + Extra)': '#d62728', 'Horas PROGRAMADAS (Tu Personal)': '#2ca02c'})
            fig.update_layout(title=f"Balance de Horas en {rol} (Vista por Bloques)", xaxis_title="Bloques de Horario", yaxis_title="Cantidad de Horas-Hombre (hrs)", legend_title=None, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            tab_obj.plotly_chart(fig, use_container_width=True)

        generar_grafico('Cocina', tab1)
        generar_grafico('Salon', tab2)
        generar_grafico('Barra', tab3)

    else:
        st.error(f"⚠️ *Inviable:* El presupuesto de $ {presupuesto_nomina:,.2f} no alcanza para pagar la demanda ingresada. Sube la proyección de ventas ($) o el % de nómina.")
