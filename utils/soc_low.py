import streamlit as st
import requests
import pandas as pd

def show_low_soc_view(default_date, api_key: str):
    st.title("⚠️ Vehículos con SOC Bajo (<=20%)")

    # Selección de fechas
    start_date = st.date_input("Fecha de inicio", value=default_date)
    end_date = st.date_input("Fecha de fin", value=default_date)

    if start_date > end_date:
        st.error("La fecha de inicio no puede ser posterior a la de fin.")
        return

    if st.button("Buscar vehículos con SOC bajo"):
        with st.spinner("Consultando registros con SOC <= 20%..."):
            data = fetch_low_soc_data(start_date, end_date, api_key)

        if data:
            df = pd.DataFrame(data)
            if df.empty:
                st.success("✅ No hay registros de SOC bajo en el rango seleccionado.")
            else:
                st.warning(f"⚠️ Se encontraron {len(df)} registros con SOC bajo.")
                df = df.sort_values("fecha")
                st.dataframe(df[["fecha", "matricula", "minSoc"]])
        else:
            st.error("❌ Error al obtener los datos de la API o no se encontraron vehículos.")

def fetch_low_soc_data(start_date, end_date, api_key: str):
    """Consulta la API para obtener los registros donde SOC < 20%."""
    url = "http://localhost:3000/plannerstats/BI/vehiculoiot-low-soc"  # Asegúrate de que esta ruta exista
    headers = {
        "x-api-key": api_key
    }

    params = {
        "fechaInicio": start_date.strftime("%Y-%m-%d"),
        "fechaFin": end_date.strftime("%Y-%m-%d")
    }

    try:
        response = requests.get(url, headers=headers, params=params)

        # Verificamos si la respuesta es 404 (sin vehículos encontrados)
        if response.status_code == 404:
            return []  # No hay vehículos con SOC bajo en ese rango

        response.raise_for_status()  # Si hubo otro error, levantará una excepción
        return response.json()

    except requests.RequestException as e:
        if response.status_code == 404:
            st.info("✅ No se encontraron vehículos con SOC bajo en el rango de fechas especificado.")
        else:
            st.error(f"Error al llamar a la API: {e}")
        return []
