import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
from supabase import create_client
import re

# ---------------------------
# CONEXIÓN A SUPABASE
# ---------------------------
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ---------------------------
# VERIFICACIÓN DE SESIÓN Y ROL
# ---------------------------
if "usuario" not in st.session_state:
    st.error("⚠️ No has iniciado sesión.")
    st.stop()

rol = st.session_state.usuario.get("Rol", "").lower()
if rol not in ["admin", "gerente"]:
    st.error("🚫 No tienes permiso para acceder a este módulo.")
    st.stop()

# ---------------------------
# TITULO
# ---------------------------
st.title("📝 Generador de Cotización para Clientes")

# ---------------------------
# CARGAR RUTAS DE SUPABASE
# ---------------------------
respuesta = supabase.table("Rutas").select("*").execute()

if respuesta.data:
    df = pd.DataFrame(respuesta.data)
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
    fecha = st.date_input("Fecha de cotización", value=date.today(), format="DD/MM/YYYY")

    # ---------------------------
    # DATOS DE CLIENTE Y EMPRESA
    # ---------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Datos del Cliente")
        cliente_nombre = st.text_input("Nombre del Cliente")
        cliente_direccion = st.text_input("Dirección del Cliente")
        cliente_mail = st.text_input("Email del Cliente")
        cliente_telefono = st.text_input("Teléfono del Cliente")
        cliente_ext = st.text_input("Ext Cliente")

    with col2:
        st.subheader("Datos de la Empresa")
        empresa_nombre = st.text_input("Nombre de tu Empresa", "PICUS")
        empresa_direccion = st.text_input("Dirección de la Empresa")
        empresa_mail = st.text_input("Email de la Empresa")
        empresa_telefono = st.text_input("Teléfono de la Empresa")
        empresa_ext = st.text_input("Ext Empresa")

    # ---------------------------
    # SELECCIÓN DE RUTAS SIN FILTRO
    # ---------------------------
    ids_seleccionados = st.multiselect(
        "Elige las rutas que deseas incluir:",
        df["ID_Ruta"] + " | " + df["Tipo"] + " | " + df["Origen"] + " → " + df["Destino"]
    )

    # ---------------------------
    # MONEDA Y TIPO DE CAMBIO
    # ---------------------------
    moneda_default = None
    if ids_seleccionados:
        id_ruta = ids_seleccionados[0].split(" | ")[0]
        ruta_data = df[df["ID_Ruta"] == id_ruta].iloc[0]
        moneda_default = ruta_data["Moneda"]

    st.subheader("Moneda y Tipo de Cambio para la Cotización")
    moneda_cotizacion = st.selectbox("Moneda Principal de la Cotización", ["MXP", "USD"], index=0 if moneda_default == "MXP" else 1)
    tipo_cambio = st.number_input("Tipo de Cambio USD/MXP", min_value=0.0, value=18.0)

    def convertir_moneda(valor, origen, destino, tipo_cambio):
        if origen == destino:
            return valor
        if origen == "MXP" and destino == "USD":
            return valor / tipo_cambio
        if origen == "USD" and destino == "MXP":
            return valor * tipo_cambio
        return valor

    # ---------------------------
    # SELECCIÓN DE CONCEPTOS POR RUTA
    # ---------------------------
    rutas_conceptos = {}

    for ruta in ids_seleccionados:
        st.markdown(f"**Selecciona los conceptos para la ruta {ruta}**")
        conceptos = st.multiselect(
            f"Conceptos para {ruta}",
            options=["Ingreso_Original", "Cruce_Original", "Movimiento_Local", "Puntualidad", "Pension", "Estancia",
                     "Pistas_Extra", "Stop", "Falso", "Gatas", "Accesorios", "Casetas", "Fianza", "Guias"],
            default=["Ingreso_Original", "Casetas"]
        )
        rutas_conceptos[ruta] = conceptos

# ---------------------------
# BOTÓN PARA GENERAR PDF
# ---------------------------
def safe_text(text):
    return text.encode('latin-1', 'ignore').decode('latin-1')

if st.button("Generar Cotización PDF"):

    class PDF(FPDF):
        def header(self):
            self.image('Cotización Picus.png', x=0, y=0, w=8.5, h=11)

    pdf = PDF(orientation='P', unit='in', format='Letter')
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "", 10)

    # ---------------------------
    # DATOS EN PLANTILLA ALINEADOS
    # ---------------------------
    # Cliente (izquierda)
    pdf.set_font("Arial", "B", 13)
    pdf.set_xy(0.85, 2.29)
    pdf.cell(0, 0.22, safe_text(f"Nombre: {cliente_nombre}"), ln=True)

    pdf.set_xy(0.85, 2.93)
    pdf.cell(0, 0.22, safe_text(f"Dirección: {cliente_direccion}"), ln=True)

    pdf.set_xy(0.85, 3.48)
    pdf.cell(0, 0.22, safe_text(f"Mail: {cliente_mail}"), ln=True)

    pdf.set_xy(0.85, 3.9)
    pdf.cell(0, 0.22, safe_text(f"Teléfono: {cliente_telefono} Ext: {cliente_ext}"), ln=True)

    # Empresa (derecha)
    pdf.set_xy(4.78, 2.29)
    pdf.cell(0, 0.22, safe_text(f"{empresa_nombre}"), ln=True, align="R")

    pdf.set_xy(4.78, 2.93)
    pdf.cell(0, 0.22, safe_text(f"{empresa_direccion}"), ln=True, align="R")
    
    pdf.set_xy(4.78, 3.48)
    pdf.cell(0, 0.22, safe_text(f"{empresa_mail}"), ln=True, align="R")

    pdf.set_xy(5.23, 3.9)
    pdf.cell(0, 0.22, safe_text(f"{empresa_telefono} Ext: {empresa_ext}"), ln=True, align="R")

    # ---------------------------
    # DETALLE DE CONCEPTOS
    # ---------------------------
    pdf.set_font("Arial", "", 8)
    for campo in conceptos:
        valor = ruta_data[campo]
        if pd.notnull(valor) and valor != 0:
            # Moneda
            if campo == "Ingreso_Original":
                moneda_original = ruta_data["Moneda"]
            elif campo == "Cruce_Original":
                moneda_original = ruta_data["Moneda_Cruce"]
            else:
                moneda_original = "MXP"

            valor_convertido = convertir_moneda(valor, moneda_original, moneda_cotizacion, tipo_cambio)

            pdf.set_xy(0.85, y)
            pdf.cell(3.55, 0.15, safe_text(campo.replace("_", " ").title()), align="R")

            pdf.set_xy(4.69, y)
            pdf.cell(0.61, 0.15, "1", align="C")

            pdf.set_xy(5.79, y)
            pdf.cell(0.61, 0.15, moneda_cotizacion, align="C")

            pdf.set_xy(6.77, y)
            pdf.cell(0.88, 0.15, f"${valor_convertido:,.2f}", align="C")

            total_global += valor_convertido
            y += 0.25  # ajusta este valor para controlar interlineado (0.15 o 0.2 si quieres más compacto)

    # ---------------------------
    # TOTAL Y LEYENDA ALINEADOS
    # ---------------------------
    if y > 10: 
        pdf.add_page()
        y = 1

    pdf.set_font("Arial", "B", 8)
    pdf.set_xy(4.69, 9.34)
    pdf.cell(0.61, 0.15, "Tarifa total", align="L")

    pdf.set_xy(5.79, 9.34)
    pdf.cell(0.61, 0.15, moneda_cotizacion, align="C")

    pdf.set_xy(6.77, 9.34)
    pdf.set_font("Arial", "B", 8)
    pdf.cell(0.88, 0.15, f"${total_global:,.2f}", align="C")

    
    # Leyenda de validez
    pdf.set_font("Arial", "", 8)
    pdf.set_xy(0.86, 9.69)
    pdf.set_font("Arial", "", 8)
    pdf.multi_cell(3.55, 0.15, safe_text("Esta cotización es válida por 15 días."), align="C")


    # ---------------------------
    # GUARDAR PDF
    # ---------------------------
    nombre_archivo_cliente = re.sub(r'[^\w\-]', '_', cliente_nombre)
    pdf_output = f'Cotizacion-{nombre_archivo_cliente}-{fecha.strftime("%d-%m-%Y")}.pdf'
    pdf.output(pdf_output)

    with open(pdf_output, "rb") as file:
        btn = st.download_button(
            label="📄 Descargar Cotización en PDF",
            data=file,
            file_name=pdf_output,
            mime="application/pdf"
        )
else:
    st.warning("⚠️ No hay rutas registradas en Supabase.")
