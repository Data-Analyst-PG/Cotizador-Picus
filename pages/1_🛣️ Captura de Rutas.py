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

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Inicializa estado si no existe
if "revisar_ruta" not in st.session_state:
    st.session_state.revisar_ruta = False

# Valores por defecto
RUTA_DATOS = "datos_generales.csv"
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

def cargar_datos_generales():
    if os.path.exists(RUTA_DATOS):
        return pd.read_csv(RUTA_DATOS).set_index("Parametro").to_dict()["Valor"]
    else:
        return valores_por_defecto.copy()

def guardar_datos_generales(valores):
    df = pd.DataFrame(valores.items(), columns=["Parametro", "Valor"])
    df.to_csv(RUTA_DATOS, index=False)

def safe_number(x):
    return 0 if (x is None or (isinstance(x, float) and pd.isna(x))) else x

# Generador de ID tipo PIC000001
def generar_nuevo_id():
    try:
        respuesta = supabase.table("Rutas").select("ID_Ruta").order("ID_Ruta", desc=True).limit(1).execute()
        if respuesta.data and respuesta.data[0].get("ID_Ruta"):
            ultimo = respuesta.data[0]["ID_Ruta"]
            numero = int(ultimo[3:]) + 1  # Asumiendo formato 'PIC000001'
        else:
            numero = 1
    except Exception as e:
        st.warning(f"⚠️ No se pudo generar el ID automáticamente: {e}")
        numero = 1
    return f"PIC{numero:06d}"

valores = cargar_datos_generales()

st.title("🚛 Captura de Rutas + Datos Generales")

with st.expander("⚙️ Configurar Datos Generales"):
    col1, col2 = st.columns(2)
    claves = list(valores_por_defecto.keys())

    for i, key in enumerate(claves):
        col = col1 if i % 2 == 0 else col2
        valores[key] = col.number_input(key, value=float(valores.get(key, valores_por_defecto[key])), step=0.1)
    if st.button("Guardar Datos Generales"):
        guardar_datos_generales(valores)
        st.success("✅ Datos Generales guardados correctamente.")

st.markdown("---")

st.subheader("🛣️ Nueva Ruta")

# Formulario principal
with st.form("captura_ruta"):
    col1, col2 = st.columns(2)

    with col1:
        fecha = st.date_input("Fecha", value=datetime.today())
        tipo = st.selectbox("Tipo de Ruta", ["IMPORTACION", "EXPORTACION", "VACIO"])
        ruta_tipo = st.selectbox("Ruta Tipo", ["Ruta Larga", "Tramo"])
        cliente = st.text_input("Nombre Cliente")
        origen = st.text_input("Origen")
        destino = st.text_input("Destino")
        Modo_de_Viaje = st.selectbox("Modo de Viaje", ["Operador", "Team"])
        km = st.number_input("Kilómetros", min_value=0.0)
        moneda_ingreso = st.selectbox("Moneda Ingreso Flete", ["MXP", "USD"])
        ingreso_flete = st.number_input("Ingreso Flete", min_value=0.0)
    with col2:
        moneda_cruce = st.selectbox("Moneda Ingreso Cruce", ["MXP", "USD"])
        ingreso_cruce = st.number_input("Ingreso Cruce", min_value=0.0)
        moneda_costo_cruce = st.selectbox("Moneda Costo Cruce", ["MXP", "USD"])
        costo_cruce = st.number_input("Costo Cruce", min_value=0.0)        
        movimiento_local = st.number_input("Movimiento Local (MXP)", min_value=0.0)
        puntualidad = st.number_input("Puntualidad", min_value=0.0)
        pension = st.number_input("Pensión (MXP)", min_value=0.0)
        estancia = st.number_input("Estancia (MXP)", min_value=0.0)
        fianza = st.number_input("Fianza (MXP)", min_value=0.0)
        casetas = st.number_input("Casetas (MXP)", min_value=0.0)

    st.markdown("---")
    st.subheader("🧾 Costos Extras Adicionales")
    col3, col4 = st.columns(2)
    with col3:
        pistas_extra = st.number_input("Pistas Extra (MXP)", min_value=0.0)
        stop = st.number_input("Stop (MXP)", min_value=0.0)
        falso = st.number_input("Falso (MXP)", min_value=0.0)
    with col4:
        gatas = st.number_input("Gatas (MXP)", min_value=0.0)
        accesorios = st.number_input("Accesorios (MXP)", min_value=0.0)
        guias = st.number_input("Guías (MXP)", min_value=0.0)

    revisar = st.form_submit_button("🔍 Revisar Ruta")

    if revisar:
        st.session_state.revisar_ruta = True
        st.session_state.datos_captura = {
            "fecha": fecha, "tipo": tipo, "ruta_tipo": ruta_tipo, "cliente": cliente, "origen": origen, "destino": destino, "Modo de Viaje": Modo_de_Viaje,
            "km": km, "moneda_ingreso": moneda_ingreso, "ingreso_flete": ingreso_flete,
            "moneda_cruce": moneda_cruce, "ingreso_cruce": ingreso_cruce,
            "moneda_costo_cruce": moneda_costo_cruce, "costo_cruce": costo_cruce,
            "movimiento_local": movimiento_local,
            "puntualidad": puntualidad, "pension": pension, "estancia": estancia,
            "fianza": fianza, "casetas": casetas,
            "pistas_extra": pistas_extra, "stop": stop, "falso": falso,
            "gatas": gatas, "accesorios": accesorios, "guias": guias
        }
        ingreso_total = (ingreso_flete * valores["Tipo de cambio USD"] if moneda_ingreso == "USD" else ingreso_flete)
        ingreso_total += (ingreso_cruce * valores["Tipo de cambio USD"] if moneda_cruce == "USD" else ingreso_cruce)
        costo_cruce_convertido = costo_cruce * (valores["Tipo de cambio USD"] if moneda_costo_cruce == "USD" else 1)

        costo_diesel_camion = (km / valores["Rendimiento Camion"]) * valores["Costo Diesel"]

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

        # Bono Team (solo si no es Tramo)
        if ruta_tipo != "Tramo" and Modo_de_Viaje == "Team":
            bono_team = valores.get("Bono Modo Team", 650)
            sueldo += bono_team

        extras = sum(map(safe_number, [movimiento_local, puntualidad, pension, estancia, fianza, pistas_extra, stop, falso, gatas, accesorios, guias]))

        costo_total = costo_diesel_camion + sueldo + bono + casetas + extras + costo_cruce_convertido

        utilidad_bruta = ingreso_total - costo_total
        costos_indirectos = ingreso_total * 0.35
        utilidad_neta = utilidad_bruta - costos_indirectos
        porcentaje_bruta = (utilidad_bruta / ingreso_total * 100) if ingreso_total > 0 else 0
        porcentaje_neta = (utilidad_neta / ingreso_total * 100) if ingreso_total > 0 else 0

        def colored_bold(label, value, condition):
            color = "green" if condition else "red"
            return f"<strong>{label}:</strong> <span style='color:{color}; font-weight:bold'>{value}</span>"

        st.markdown("---")
        st.subheader("📊 Ingresos y Utilidades")

        st.write(f"**Ingreso Total:** ${ingreso_total:,.2f}")
        st.write(f"**Costo Total:** ${costo_total:,.2f}")
        st.markdown(colored_bold("Utilidad Bruta", f"${utilidad_bruta:,.2f}", utilidad_bruta >= 0), unsafe_allow_html=True)
        st.markdown(colored_bold("% Utilidad Bruta", f"{porcentaje_bruta:.2f}%", porcentaje_bruta >= 50), unsafe_allow_html=True)
        st.write(f"**Costos Indirectos (35%):** ${costos_indirectos:,.2f}")
        st.markdown(colored_bold("Utilidad Neta", f"${utilidad_neta:,.2f}", utilidad_neta >= 0), unsafe_allow_html=True)
        st.markdown(colored_bold("% Utilidad Neta", f"{porcentaje_neta:.2f}%", porcentaje_neta >= 15), unsafe_allow_html=True)

if st.session_state.revisar_ruta and st.button("💾 Guardar Ruta"):
    d = st.session_state.datos_captura

    tipo_cambio_flete = valores["Tipo de cambio USD"] if d["moneda_ingreso"] == "USD" else valores["Tipo de cambio MXP"]
    tipo_cambio_cruce = valores["Tipo de cambio USD"] if d["moneda_cruce"] == "USD" else valores["Tipo de cambio MXP"]
    tipo_cambio_costo_cruce = valores["Tipo de cambio USD"] if d["moneda_costo_cruce"] == "USD" else valores["Tipo de cambio MXP"]

    ingreso_flete_convertido = d["ingreso_flete"] * tipo_cambio_flete
    ingreso_cruce_convertido = d["ingreso_cruce"] * tipo_cambio_cruce
    costo_cruce_convertido = d["costo_cruce"] * tipo_cambio_costo_cruce
    ingreso_total = ingreso_flete_convertido + ingreso_cruce_convertido

    costo_diesel_camion = (d["km"] / valores["Rendimiento Camion"]) * valores["Costo Diesel"]

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

    # Bono Team (solo si no es Tramo)
    if ruta_tipo != "Tramo" and Modo_de_Viaje == "Team":
        bono_team = valores.get("Bono Modo Team", 650)
        sueldo += bono_team

    extras = sum([
        safe_number(d["movimiento_local"]), safe_number(puntualidad),
        safe_number(d["pension"]), safe_number(d["estancia"]),
        safe_number(d["fianza"]),
        safe_number(d["pistas_extra"]), safe_number(d["stop"]), safe_number(d["falso"]),
        safe_number(d["gatas"]), safe_number(d["accesorios"]), safe_number(d["guias"])
    ])

    costo_total = costo_diesel_camion + sueldo + bono + d["casetas"] + extras + costo_cruce_convertido

    nueva_ruta = {
        "ID_Ruta": generar_nuevo_id(),
        "Fecha": str(d["fecha"]), "Tipo": d["tipo"], "Ruta_Tipo": d["ruta_tipo"], "Cliente": d["cliente"], "Origen": d["origen"], "Destino": d["destino"], "Modo de Viaje": d["Modo de Viaje"], "KM": d["km"],
        "Moneda": d["moneda_ingreso"], "Ingreso_Original": d["ingreso_flete"], "Tipo de cambio": tipo_cambio_flete,
        "Ingreso Flete": ingreso_flete_convertido, "Moneda_Cruce": d["moneda_cruce"], "Cruce_Original": d["ingreso_cruce"],
        "Tipo cambio Cruce": tipo_cambio_cruce, "Ingreso Cruce": ingreso_cruce_convertido,
        "Moneda Costo Cruce": d["moneda_costo_cruce"], "Costo Cruce": d["costo_cruce"],
        "Costo Cruce Convertido": costo_cruce_convertido,
        "Ingreso Total": ingreso_total,
        "Pago por KM": pago_km, "Sueldo_Operador": sueldo, "Bono": bono,
        "Casetas": d["casetas"],
        "Movimiento_Local": d["movimiento_local"], "Puntualidad": puntualidad, "Pension": d["pension"],
        "Estancia": d["estancia"], "Fianza": d["fianza"],
        "Pistas_Extra": d["pistas_extra"], "Stop": d["stop"], "Falso": d["falso"],
        "Gatas": d["gatas"], "Accesorios": d["accesorios"], "Guias": d["guias"],
        "Costo_Diesel_Camion": costo_diesel_camion,
        "Costo_Extras": extras, "Costo_Total_Ruta": costo_total, "Costo Diesel": valores["Costo Diesel"], "Rendimiento Camion": valores["Rendimiento Camion"],
    }

    # Generar nuevo ID y verificar duplicado
    nuevo_id = generar_nuevo_id()
    existe = supabase.table("Rutas").select("ID_Ruta").eq("ID_Ruta", nuevo_id).execute()

    if existe.data:
        st.error("⚠️ Conflicto al generar ID. Intenta de nuevo.")
    else:
        nueva_ruta["ID_Ruta"] = nuevo_id
        try:
            supabase.table("Rutas").insert(nueva_ruta).execute()
            st.success("✅ Ruta guardada exitosamente.")
            st.session_state.revisar_ruta = False
            del st.session_state["datos_captura"]
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error al guardar ruta: {e}")
            st.json(nueva_ruta) 
