import streamlit as st
import pandas as pd
import os
from datetime import datetime
from supabase import create_client

# ✅ Verificación de sesión y rol
if "usuario" not in st.session_state:
    st.error("⚠️ No has iniciado sesión.")
    st.stop()

rol = st.session_state.usuario.get("Rol", "").lower()
if rol not in ["admin", "gerente", "ejecutivo"]:
    st.error("🚫 No tienes permiso para acceder a este módulo.")
    st.stop()
    
# Configuración de conexión a Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

RUTA_DATOS = "datos_generales.csv"

def cargar_datos_generales():
    if os.path.exists(RUTA_DATOS):
        return pd.read_csv(RUTA_DATOS).set_index("Parametro").to_dict()["Valor"]
    else:
        return {}

def safe_number(x):
    return 0 if (x is None or (isinstance(x, float) and pd.isna(x))) else x

st.title("🗂️ Gestión de Rutas Guardadas")

# Cargar rutas desde Supabase
respuesta = supabase.table("Rutas").select("*").execute()
valores = cargar_datos_generales()
valores_por_defecto = {
    "Rendimiento Camion": 2.5,
    "Costo Diesel": 24.0,
    "Pago x KM (General)": 1.50,
    "Bono ISR IMSS RL": 462.66,
    "Bono ISR IMSS Tramo": 185.06,
    "Pago Vacio": 100.0,
    "Pago Tramo": 300.0,
    "Bono Rendimiento": 250.0,
    "Bono Modo Team": 650.0,
    "Tipo de cambio USD": 17.5,
    "Tipo de cambio MXP": 1.0
}

if respuesta.data:
    df = pd.DataFrame(respuesta.data)
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date

    st.subheader("📋 Rutas Registradas")
    st.dataframe(df, use_container_width=True)
    st.markdown(f"**Total de rutas registradas:** {len(df)}")
    st.markdown("---")

    st.subheader("🗑️ Eliminar rutas")
    ids_disponibles = df["ID_Ruta"].tolist()
    ids_a_eliminar = st.multiselect("Selecciona los ID de ruta a eliminar", ids_disponibles)

    if st.button("Eliminar rutas seleccionadas") and ids_a_eliminar:
        for idr in ids_a_eliminar:
            supabase.table("Rutas").delete().eq("ID_Ruta", idr).execute()
        st.success("✅ Rutas eliminadas correctamente.")
        st.rerun()

    st.markdown("---")
    st.subheader("✏️ Editar Ruta Existente")

    id_editar = st.selectbox("Selecciona el ID de Ruta a editar", ids_disponibles)
    ruta = df[df["ID_Ruta"] == id_editar].iloc[0]

    # Datos Generales (fuera del formulario)
    st.markdown("### ⚙️ Configurar Datos Generales")
    with st.expander("Editar Datos Generales"):
        col1, col2 = st.columns(2)
        for i, key in enumerate(valores_por_defecto.keys()):
            col = col1 if i % 2 == 0 else col2
            valores[key] = col.number_input(f"{key}", value=float(valores.get(key, valores_por_defecto[key])), step=0.1)

    if st.button("Guardar Datos Generales"):
        guardar_datos_generales(valores)
        st.success("✅ Datos Generales actualizados correctamente.")

    st.markdown("---")

    with st.form("editar_ruta"):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", ruta["Fecha"])
            tipo = st.selectbox("Tipo", ["IMPORTACION", "EXPORTACION", "VACIO"], index=["IMPORTACION", "EXPORTACION", "VACIO"].index(ruta["Tipo"]))
            ruta_tipo = st.selectbox("Ruta Tipo", ["Ruta Larga", "Tramo"])
            cliente = st.text_input("Cliente", value=ruta["Cliente"])
            origen = st.text_input("Origen", value=ruta["Origen"])
            destino = st.text_input("Destino", value=ruta["Destino"])
            Modo_de_Viaje = st.selectbox("Modo de Viaje", ["Operador", "Team"], index=["Operador", "Team"].index(ruta["Modo de Viaje"]))
            km = st.number_input("Kilómetros", min_value=0.0, value=float(ruta["KM"]))
            moneda_ingreso = st.selectbox("Moneda Flete", ["MXP", "USD"], index=["MXN", "USD"].index(ruta["Moneda"]))
            ingreso_original = st.number_input("Ingreso Flete Original", min_value=0.0, value=float(ruta["Ingreso_Original"]))
        with col2:
            moneda_cruce = st.selectbox("Moneda Cruce", ["MXP", "USD"], index=["MXP", "USD"].index(ruta["Moneda_Cruce"]))
            ingreso_cruce = st.number_input("Ingreso Cruce Original", min_value=0.0, value=float(ruta["Cruce_Original"]))
            moneda_costo_cruce = st.selectbox("Moneda Costo Cruce", ["MXP", "USD"], index=["MXP", "USD"].index(ruta["Moneda Costo Cruce"]))
            costo_cruce = st.number_input("Costo Cruce", min_value=0.0, value=float(ruta["Costo Cruce"]))
            movimiento_local = st.number_input("Movimiento Local (MXP)", min_value=0.0, value=float(ruta["Movimiento_Local"]))
            puntualidad = st.number_input("Puntualidad (MXP)", min_value=0.0, value=float(ruta["Puntualidad"]))
            pension = st.number_input("Pensión (MXP)", min_value=0.0, value=float(ruta["Pension"]))
            estancia = st.number_input("Estancia (MXP)", min_value=0.0, value=float(ruta["Estancia"]))
            fianza = st.number_input("Fianza (MXP)", min_value=0.0, value=float(ruta["Fianza"]))
            casetas = st.number_input("Casetas (MXP)", min_value=0.0, value=float(ruta["Casetas"]))
            
        st.markdown("---")
        st.subheader("🧾 Costos Extras Adicionales")
        col3, col4 = st.columns(2)
        with col3:
            pistas_extra = st.number_input("Pistas Extra (MXP)", min_value=0.0, value=float(ruta["Pistas_Extra"]))
            stop = st.number_input("Stop (MXP)", min_value=0.0, value=float(ruta["Stop"]))
            falso = st.number_input("Falso (MXP)", min_value=0.0, value=float(ruta["Falso"]))
        with col4:
            gatas = st.number_input("Gatas (MXP)", min_value=0.0, value=float(ruta["Gatas"]))
            accesorios = st.number_input("Accesorios (MXP)", min_value=0.0, value=float(ruta["Accesorios"]))
            guias = st.number_input("Guías (MXP)", min_value=0.0, value=float(ruta["Guias"]))

        guardar = st.form_submit_button("💾 Guardar cambios")

        if guardar:
             tc_usd = valores.get("Tipo de cambio USD", 17.5)
             tc_mxp = valores.get("Tipo de cambio MXP", 1.0)
             tipo_cambio_flete = tc_usd if moneda_ingreso == "USD" else tc_mxp
             tipo_cambio_cruce = tc_usd if moneda_cruce == "USD" else tc_mxp
             tipo_cambio_costo_cruce = tc_usd if moneda_costo_cruce == "USD" else tc_mxp

             ingreso_flete_convertido = ingreso_original * tipo_cambio_flete
             ingreso_cruce_convertido = ingreso_cruce * tipo_cambio_cruce
             ingreso_total = ingreso_flete_convertido + ingreso_cruce_convertido
             costo_cruce_convertido = costo_cruce * tipo_cambio_costo_cruce

             rendimiento_camion = valores.get("Rendimiento Camion", 1)
             costo_diesel = valores.get("Costo Diesel", 1)
             costo_diesel_camion = (km / rendimiento_camion) * costo_diesel

             # Pago por KM general
             pago_km = valores.get("Pago x KM (General)", 1.5)
             bono = 0.0

             # 🧩 Cálculo condicional por tipo de ruta (larga vs tramo)
             if ruta_tipo == "Tramo":
                 sueldo = valores.get("Pago Tramo", 300.0)
                 bono = valores.get("Bono ISR IMSS Tramo", 185.06)
                 Modo_de_Viaje = "Operador"  # Forzar
                 costo_diesel_camion = 0.0   # Si decides no considerar diesel en tramos
             elif tipo in ["IMPORTACION", "EXPORTACION"]:
                 sueldo = km * pago_km
                 bono_isr = valores.get("Bono ISR IMSS RL", 0)
                 bono_rendimiento = valores.get("Bono Rendimiento", 0)
                 bono = bono_isr + bono_rendimiento
             elif tipo == "VACIO":
                 if km <= 100:
                     sueldo = valores.get("Pago Vacio", 100.0)
                 else:
                     sueldo = km * pago_km
                 bono = 0.0

             extras = sum(map(safe_number, [movimiento_local, puntualidad, pension, estancia, fianza, pistas_extra, stop, falso, gatas, accesorios, guias]))

             costo_total = costo_diesel_camion + sueldo + bono + casetas + extras + costo_cruce_convertido

             ruta_actualizada = {
                 "Modo de Viaje": Modo_de_Viaje,
                 "Fecha": fecha.isoformat(),
                 "Tipo": tipo,
                 "Ruta_Tipo": ruta_tipo,
                 "Cliente": cliente,
                 "Origen": origen,
                 "Destino": destino,
                 "KM": km,
                 "Moneda": moneda_ingreso,
                 "Ingreso_Original": ingreso_original,
                 "Tipo de cambio": tipo_cambio_flete,
                 "Ingreso Flete": ingreso_flete_convertido,
                 "Moneda_Cruce": moneda_cruce,
                 "Cruce_Original": ingreso_cruce,
                 "Tipo cambio Cruce": tipo_cambio_cruce,
                 "Ingreso Cruce": ingreso_cruce_convertido,
                 "Ingreso Total": ingreso_total,
                 "Moneda Costo Cruce": moneda_costo_cruce,
                 "Costo Cruce": costo_cruce,
                 "Costo Cruce Convertido": costo_cruce_convertido,
                 "Pago por KM": pago_km,
                 "Sueldo_Operador": sueldo,
                 "Bono": bono,
                 "Casetas": casetas,
                 "Movimiento_Local": movimiento_local,
                 "Puntualidad": puntualidad,
                 "Pension": pension,
                 "Estancia": estancia,
                 "Fianza": fianza,
                 "Pistas_Extra": pistas_extra,
                 "Stop": stop,
                 "Falso": falso,
                 "Gatas": gatas,
                 "Accesorios": accesorios,
                 "Guias": guias,
                 "Costo_Diesel_Camion": costo_diesel_camion,
                 "Costo_Extras": extras,
                 "Costo_Total_Ruta": costo_total,
                 "Costo Diesel": costo_diesel,
                 "Rendimiento Camion": rendimiento_camion,
             }

             try:
                 supabase.table("Rutas").update(ruta_actualizada).eq("ID_Ruta", id_editar).execute()
                 st.success("✅ Ruta actualizada exitosamente.")
                 st.stop()
             except Exception as e:
                 st.error(f"❌ Error al actualizar ruta: {e}")
else:
    st.warning("⚠️ No hay rutas guardadas todavía.")
