import streamlit as st
import pandas as pd
from supabase import create_client
import os
import tempfile
from fpdf import FPDF
import base64

# ✅ Verificación de sesión y rol
if "usuario" not in st.session_state:
    st.error("⚠️ No has iniciado sesión.")
    st.stop()

rol = st.session_state.usuario.get("Rol", "").lower()
if rol not in ["admin", "gerente", "ejecutivo", "visitante"]:
    st.error("🚫 No tienes permiso para acceder a este módulo.")
    st.stop()

# ✅ Conexión a Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ✅ Valores por defecto
valores_por_defecto = {
    "Rendimiento Camion": 2.5,
    "Costo Diesel": 24.0,
}

# ✅ Ruta para valores locales
RUTA_DATOS = "datos_generales.csv"

# ✅ Cargar valores desde CSV o usar los por defecto
if os.path.exists(RUTA_DATOS):
    df_datos = pd.read_csv(RUTA_DATOS).set_index("Parametro")["Valor"].to_dict()
    valores = {**valores_por_defecto, **df_datos}
else:
    valores = valores_por_defecto.copy()

# ✅ Cargar rutas desde Supabase
respuesta = supabase.table("Rutas").select("*").execute()
df = pd.DataFrame(respuesta.data)

# ✅ Asegurar formato correcto
if not df.empty:
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.strftime("%Y-%m-%d")
    df["Ingreso Total"] = pd.to_numeric(df["Ingreso Total"], errors="coerce").fillna(0)
    df["Costo_Total_Ruta"] = pd.to_numeric(df["Costo_Total_Ruta"], errors="coerce").fillna(0)

st.title("🔍 Consulta Individual de Ruta")

def safe_number(x):
    return 0 if pd.isna(x) else x

def mostrar_resultados(ingreso_total, costo_total, utilidad_bruta, costos_indirectos, utilidad_neta, porcentaje_bruta, porcentaje_neta):
    st.markdown("---")
    st.subheader("📊 Ingresos y Utilidades")

    def colored_bold(label, value, condition):
        color = "green" if condition else "red"
        return f"<strong>{label}:</strong> <span style='color:{color}; font-weight:bold'>{value}</span>"

    st.write(f"**Ingreso Total:** ${ingreso_total:,.2f}")
    st.write(f"**Costo Total:** ${costo_total:,.2f}")
    st.markdown(colored_bold("Utilidad Bruta", f"${utilidad_bruta:,.2f}", utilidad_bruta >= 0), unsafe_allow_html=True)
    st.markdown(colored_bold("% Utilidad Bruta", f"{porcentaje_bruta:.2f}%", porcentaje_bruta >= 50), unsafe_allow_html=True)
    st.write(f"**Costos Indirectos (35%):** ${costos_indirectos:,.2f}")
    st.markdown(colored_bold("Utilidad Neta", f"${utilidad_neta:,.2f}", utilidad_neta >= 0), unsafe_allow_html=True)
    st.markdown(colored_bold("% Utilidad Neta", f"{porcentaje_neta:.2f}%", porcentaje_neta >= 15), unsafe_allow_html=True)
    
if df.empty:
    st.warning("⚠️ No hay rutas guardadas todavía.")
    st.stop()

st.subheader("📌 Selecciona Tipo de Ruta")
tipo_ruta_especifica = st.selectbox("Ruta Larga o Tramo", df["Ruta_Tipo"].unique())
df_ruta_tipo = df[df["Ruta_Tipo"] == tipo_ruta_especifica]

tipo_sel = st.selectbox("Tipo (IMPORTACION / EXPORTACION / VACIO)", df_ruta_tipo["Tipo"].unique())
df_tipo = df_ruta_tipo[df_ruta_tipo["Tipo"] == tipo_sel]

rutas_unicas = df_tipo[["Origen", "Destino"]].drop_duplicates()
opciones_ruta = list(rutas_unicas.itertuples(index=False, name=None))

st.subheader("📌 Selecciona Ruta (Origen → Destino)")
ruta_sel = st.selectbox("Ruta", opciones_ruta, format_func=lambda x: f"{x[0]} → {x[1]}")
origen_sel, destino_sel = ruta_sel

df_filtrada = df_tipo[(df_tipo["Origen"] == origen_sel) & (df_tipo["Destino"] == destino_sel)]

if df_filtrada.empty:
    st.warning("⚠️ No hay rutas con esa combinación.")
    st.stop()

st.subheader("📌 Selecciona Cliente")
opciones = df_filtrada.index.tolist()
index_sel = st.selectbox(
    "Cliente",
    opciones,
    format_func=lambda x: f"{df.loc[x, 'Cliente']} ({df.loc[x, 'Origen']} → {df.loc[x, 'Destino']})"
)

ruta = df.loc[index_sel]
    
# Campos simulables
st.markdown("---")
st.subheader("⚙️ Ajustes para Simulación")
costo_diesel_input = st.number_input("Costo del Diesel ($/L)", value=float(valores.get("Costo Diesel", 24.0)))
rendimiento_input = st.number_input("Rendimiento Camión (km/L)", value=float(valores.get("Rendimiento Camion", 2.65)))


if st.button("🔁 Simular"):
    st.session_state["simular"] = True

# Mostrar resultados simulados si está activo
if st.session_state.get("simular", False):
    ingreso_total = safe_number(ruta["Ingreso Total"])
    costo_diesel_camion = (safe_number(ruta["KM"]) / rendimiento_input) * costo_diesel_input

    costo_total = (
        costo_diesel_camion +
        safe_number(ruta["Sueldo_Operador"]) +
        safe_number(ruta["Bono"]) +
        safe_number(ruta["Casetas"]) +
        safe_number(ruta["Costo Cruce Convertido"]) +
        safe_number(ruta["Costo_Extras"])
    )

    utilidad_bruta = ingreso_total - costo_total
    costos_indirectos = ingreso_total * 0.35
    utilidad_neta = utilidad_bruta - costos_indirectos
    porcentaje_bruta = (utilidad_bruta / ingreso_total * 100) if ingreso_total > 0 else 0
    porcentaje_neta = (utilidad_neta / ingreso_total * 100) if ingreso_total > 0 else 0

    st.success("🔧 Estás viendo una simulación. Los valores han sido ajustados con los parámetros ingresados.")
    mostrar_resultados(ingreso_total, costo_total, utilidad_bruta, costos_indirectos, utilidad_neta, porcentaje_bruta, porcentaje_neta)

    # Botón para volver a valores reales
    if st.button("🔄 Volver a valores reales"):
        st.session_state["simular"] = False
        st.rerun()

# Mostrar resultados reales por defecto
else:
    ingreso_total = safe_number(ruta["Ingreso Total"])
    costo_total = safe_number(ruta["Costo_Total_Ruta"])
    utilidad_bruta = ingreso_total - costo_total
    costos_indirectos = ingreso_total * 0.35
    utilidad_neta = utilidad_bruta - costos_indirectos
    porcentaje_bruta = (utilidad_bruta / ingreso_total * 100) if ingreso_total > 0 else 0
    porcentaje_neta = (utilidad_neta / ingreso_total * 100) if ingreso_total > 0 else 0

    mostrar_resultados(ingreso_total, costo_total, utilidad_bruta, costos_indirectos, utilidad_neta, porcentaje_bruta, porcentaje_neta)

    
# =====================
# 📋 Detalles y Costos
# =====================
st.markdown("---")
st.subheader("📋 Detalles y Costos de la Ruta")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"**Fecha:** {ruta['Fecha']}")
    st.markdown(f"**ID de Ruta:** {ruta['ID_Ruta']}")
    st.markdown(f"**Tipo:** {ruta['Tipo']}")
    st.markdown(f"**Modo:** {ruta['Modo de Viaje']}")
    st.markdown(f"**Cliente:** {ruta['Cliente']}")
    st.markdown(f"**Origen → Destino:** {ruta['Origen']} → {ruta['Destino']}")
    st.markdown(f"**KM:** {ruta['KM']:,}")
    st.markdown(f"**Rendimiento Camión:** {ruta['Rendimiento Camion']} km/L")
    st.markdown(f"**Moneda Flete:** {ruta['Moneda']}")
    st.markdown(f"**Ingreso Flete Original:** ${ruta['Ingreso_Original']:,}")
    st.markdown(f"**Tipo de cambio:** {ruta['Tipo de cambio']}")
    st.markdown(f"**Ingreso Flete Convertido:** ${ruta['Ingreso Flete']:,}")

with col2:
    st.markdown(f"**Moneda Cruce:** {ruta['Moneda_Cruce']}")
    st.markdown(f"**Ingreso Cruce Original:** ${ruta['Cruce_Original']:,}")
    st.markdown(f"**Tipo cambio Cruce:** {ruta['Tipo cambio Cruce']}")
    st.markdown(f"**Ingreso Cruce Convertido:** ${ruta['Ingreso Cruce']:,}")
    st.markdown(f"**Moneda Costo Cruce:** {ruta['Moneda Costo Cruce']}")
    st.markdown(f"**Costo Cruce Original:** ${ruta['Costo Cruce']:,}")
    st.markdown(f"**Costo Cruce Convertido:** ${ruta['Costo Cruce Convertido']:,}")
    st.markdown(f"**Casetas:** ${ruta['Casetas']:,}")
    st.markdown(f"**Diesel Camión:** ${ruta['Costo_Diesel_Camion']:,}")
    st.markdown(f"**Sueldo Operador:** ${ruta['Sueldo_Operador']:,}")
    st.markdown(f"**Bono:** ${ruta['Bono']:,}")
    st.markdown(f"**Ingreso Total:** ${ruta['Ingreso Total']:,}")
    st.markdown(f"**Costo Total Ruta:** ${ruta['Costo_Total_Ruta']:,}")

with col3:
    st.markdown("**🔧 Extras:**")
    st.markdown(f"- Movimiento Local: ${ruta['Movimiento_Local']:,}")
    st.markdown(f"- Puntualidad: ${ruta['Puntualidad']:,}")
    st.markdown(f"- Pensión: ${ruta['Pension']:,}")
    st.markdown(f"- Estancia: ${ruta['Estancia']:,}")
    st.markdown(f"- Fianza: ${ruta['Fianza']:,}")
    st.markdown(f"- Pistas Extra: ${ruta['Pistas_Extra']:,}")
    st.markdown(f"- Stop: ${ruta['Stop']:,}")
    st.markdown(f"- Falso: ${ruta['Falso']:,}")
    st.markdown(f"- Gatas: ${ruta['Gatas']:,}")
    st.markdown(f"- Accesorios: ${ruta['Accesorios']:,}")
    st.markdown(f"- Guías: ${ruta['Guias']:,}")
    

st.markdown("---")
if st.button("📥 Generar PDF de esta Ruta"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        # 🔽 Extraer valores desde `ruta`
        id_ruta = ruta["ID_Ruta"]
        fecha = ruta["Fecha"]
        tipo = ruta["Tipo"]
        modo = ruta["Modo de Viaje"]
        cliente = ruta["Cliente"]
        origen = ruta["Origen"]
        destino = ruta["Destino"]
        km = ruta["KM"]
        ingreso_flete = ruta["Ingreso Flete"]
        ingreso_cruce = ruta["Ingreso Cruce"]
        costo_cruce = ruta["Costo Cruce Convertido"]
        diesel_camion = ruta["Costo_Diesel_Camion"]
        sueldo = ruta["Sueldo_Operador"]
        bono = ruta["Bono"]
        casetas = ruta["Casetas"]
        extras = ruta["Costo_Extras"]

        movimiento_local = ruta["Movimiento_Local"]
        puntualidad = ruta["Puntualidad"]
        pension = ruta["Pension"]
        estancia = ruta["Estancia"]
        fianza_termo = ruta["Fianza"]
        pistas_extra = ruta["Pistas_Extra"]
        stop = ruta["Stop"]
        falso = ruta["Falso"]
        gatas = ruta["Gatas"]
        accesorios = ruta["Accesorios"]
        guias = ruta["Guias"]

        porc_utilidad_bruta = porcentaje_bruta
        porc_utilidad_neta = porcentaje_neta
        costo_indirecto = costos_indirectos

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Encabezado
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Consulta Individual de Ruta", ln=True)
        pdf.ln(5)

        # Datos principales
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"ID de Ruta: {id_ruta}", ln=True)
        pdf.cell(0, 10, f"Fecha: {fecha}", ln=True)
        pdf.cell(0, 10, f"Tipo: {tipo}", ln=True)
        pdf.cell(0, 10, f"Modo: {modo}", ln=True)
        pdf.cell(0, 10, f"Cliente: {cliente}", ln=True)
        pdf.cell(0, 10, f"Origen → Destino: {origen} → {destino}", ln=True)
        pdf.cell(0, 10, f"KM: {km:,.2f}", ln=True)
        pdf.ln(5)

        # Resultados de utilidad
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Resultados de Utilidad:", ln=True)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Ingreso Total: ${ingreso_total:,.2f}", ln=True)
        pdf.cell(0, 10, f"Costo Total: ${costo_total:,.2f}", ln=True)
        pdf.cell(0, 10, f"Utilidad Bruta: ${utilidad_bruta:,.2f}", ln=True)
        pdf.cell(0, 10, f"% Utilidad Bruta: {porc_utilidad_bruta:.2f}%", ln=True)
        pdf.cell(0, 10, f"Costos Indirectos (35%): ${costo_indirecto:,.2f}", ln=True)
        pdf.cell(0, 10, f"Utilidad Neta: ${utilidad_neta:,.2f}", ln=True)
        pdf.cell(0, 10, f"% Utilidad Neta: {porc_utilidad_neta:.2f}%", ln=True)
        pdf.ln(5)

        # Detalle de Costos y Extras
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Detalle de Costos y Extras:", ln=True)
        pdf.set_font("Arial", "", 12)
        campos_detalle = {
            "Ingreso Flete": ingreso_flete,
            "Ingreso Cruce": ingreso_cruce,
            "Costo Cruce": costo_cruce,
            "Diesel Camión": diesel_camion,
            "Sueldo Operador": sueldo,
            "Bono": bono,
            "Casetas": casetas,
            "Extras": extras,
        }
        for k, v in campos_detalle.items():
            pdf.cell(0, 10, f"{k}: ${v:,.2f}", ln=True)
        pdf.ln(5)

        # Costos Detallados de Extras
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Costos Detallados de Extras:", ln=True)
        pdf.set_font("Arial", "", 12)
        extras_detalle = {
            "Movimiento Local": movimiento_local,
            "Puntualidad": puntualidad,
            "Pension": pension,
            "Estancia": estancia,
            "Fianza": fianza_termo,
            "Pistas Extra": pistas_extra,
            "Stop": stop,
            "Falso": falso,
            "Gatas": gatas,
            "Accesorios": accesorios,
            "Guias": guias,
        }
        for k, v in extras_detalle.items():
            pdf.cell(0, 10, f"{k}: ${v:,.2f}", ln=True)

        pdf.output(tmp_file.name)
        with open(tmp_file.name, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="Consulta_Ruta_{id_ruta}.pdf">📄 Descargar PDF</a>'
            st.markdown(href, unsafe_allow_html=True)
