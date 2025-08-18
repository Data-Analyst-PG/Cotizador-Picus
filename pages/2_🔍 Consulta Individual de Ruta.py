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
respuesta = supabase.table("Rutas_Picus").select("*").execute()
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
    
def safe_text(texto):
    return str(texto).encode("latin-1", "replace").decode("latin-1")
    
st.markdown("---")
st.subheader("📥 Generar PDF de esta Ruta")
# Extraer desde el diccionario
id_ruta = ruta["ID_Ruta"]
fecha = ruta["Fecha"]
tipo = ruta["Tipo"]
modo = ruta["Modo de Viaje"]
cliente = ruta["Cliente"]
origen = ruta["Origen"]
destino = ruta["Destino"]
km = ruta["KM"]

rendimiento_camion = ruta["Rendimiento Camion"]
moneda_ingreso = ruta["Moneda"]
ingreso_original = ruta["Ingreso_Original"]
tipo_cambio_flete = ruta["Tipo de cambio"]
ingreso_flete = ruta["Ingreso Flete"]
moneda_cruce = ruta["Moneda_Cruce"]
ingreso_cruce = ruta["Ingreso Cruce"]
tipo_cambio_cruce = ruta["Tipo cambio Cruce"]
moneda_costo_cruce = ruta["Moneda Costo Cruce"]
costo_cruce_original = ruta["Costo Cruce"]
costo_cruce_convertido = ruta["Costo Cruce Convertido"]
casetas = ruta["Casetas"]
diesel_camion = ruta["Costo_Diesel_Camion"]
sueldo = ruta["Sueldo_Operador"]
bono = ruta["Bono"]

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
    
pdf = FPDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

# Encabezado
pdf.set_font("Arial", "B", 16)
pdf.cell(0, 10, "Consulta Individual de Ruta", ln=True)
pdf.ln(5)

# Datos principales
pdf.set_font("Arial", "", 12)
pdf.cell(0, 10, safe_text(f"ID de Ruta: {id_ruta}"), ln=True)
pdf.cell(0, 10, safe_text(f"Fecha: {fecha}"), ln=True)
pdf.cell(0, 10, safe_text(f"Tipo: {tipo}"), ln=True)
pdf.cell(0, 10, safe_text(f"Modo: {modo}"), ln=True)
pdf.cell(0, 10, safe_text(f"Cliente: {cliente}"), ln=True)
pdf.cell(0, 10, safe_text(f"Origen → Destino: {origen} - {destino}"), ln=True)
pdf.cell(0, 10, safe_text(f"KM: {km:,.2f}"), ln=True)
pdf.ln(5)

# Resultados de utilidad
pdf.set_font("Arial", "B", 12)
pdf.cell(0, 10, "Resultados de Utilidad:", ln=True)
pdf.set_font("Arial", "", 12)
pdf.cell(0, 10, safe_text(f"Ingreso Total: ${ingreso_total:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Costo Total: ${costo_total:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Utilidad Bruta: ${utilidad_bruta:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"% Utilidad Bruta: {porcentaje_bruta:.2f}%"), ln=True)
pdf.cell(0, 10, safe_text(f"Costos Indirectos (35%): ${costos_indirectos:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Utilidad Neta: ${utilidad_neta:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"% Utilidad Neta: {porcentaje_neta:.2f}%"), ln=True)
pdf.ln(5)

# Detalles completos de Costos e Ingresos
pdf.set_font("Arial", "B", 12)
pdf.cell(0, 10, "Detalles de Costos e Ingresos:", ln=True)
pdf.set_font("Arial", "", 12)

pdf.cell(0, 10, safe_text(f"Rendimiento Camión: {rendimiento_camion} km/L"), ln=True)
pdf.cell(0, 10, safe_text(f"Moneda Flete: {moneda_ingreso}"), ln=True)
pdf.cell(0, 10, safe_text(f"Ingreso Flete Original: ${ingreso_original:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Tipo de cambio: {tipo_cambio_flete}"), ln=True)
pdf.cell(0, 10, safe_text(f"Ingreso Flete Convertido: ${ingreso_flete:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Moneda Cruce: {moneda_cruce}"), ln=True)
pdf.cell(0, 10, safe_text(f"Ingreso Cruce Original: ${ingreso_cruce:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Tipo cambio Cruce: {tipo_cambio_cruce}"), ln=True)
pdf.cell(0, 10, safe_text(f"Ingreso Cruce Convertido: ${ingreso_cruce:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Moneda Costo Cruce: {moneda_costo_cruce}"), ln=True)
pdf.cell(0, 10, safe_text(f"Costo Cruce Original: ${costo_cruce_original:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Costo Cruce Convertido: ${costo_cruce_convertido:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Casetas: ${casetas:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Diesel Camión: ${diesel_camion:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Sueldo Operador: ${sueldo:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Bono: ${bono:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Ingreso Total: ${ingreso_total:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Costo Total Ruta: ${costo_total:,.2f}"), ln=True)

pdf.ln(5)
pdf.set_font("Arial", "B", 12)
pdf.cell(0, 10, "Extras:", ln=True)
pdf.set_font("Arial", "", 12)

pdf.cell(0, 10, safe_text(f"Movimiento Local: ${movimiento_local:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Puntualidad: ${puntualidad:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Pensión: ${pension:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Estancia: ${estancia:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Fianza: ${fianza_termo:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Pistas Extra: ${pistas_extra:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Stop: ${stop:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Falso: ${falso:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Gatas: ${gatas:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Accesorios: ${accesorios:,.2f}"), ln=True)
pdf.cell(0, 10, safe_text(f"Guías: ${guias:,.2f}"), ln=True)

temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
pdf.output(temp_file.name)

with open(temp_file.name, "rb") as file:
    st.download_button(
        label=" 📄Descargar PDF",
        data=file,
        file_name=f"Consulta_{ruta['Cliente']}_{ruta['Origen']}_{ruta['Destino']}.pdf",
        mime="application/pdf"
    )
