# eficiencia_utils.py

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

def obtener_vehiculos(api_key):
    """Obtener los vehículos desde la API"""
    base_url = "http://localhost:3000/plannerstats/vehiculos"
    headers = {"x-api-key": api_key}

    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al obtener los vehículos: {e}")
        return []

def show_eficiencia_vehiculo(fecha_default, api_key):
    st.title("⚡ Análisis de Eficiencia del Vehículo")

    vehiculos = obtener_vehiculos(api_key)
    if not vehiculos:
        st.warning("No se encontraron vehículos.")
        return

    matriculas = [veh["matricula"] for veh in vehiculos]

    search_text = st.text_input("Buscar matrícula", "")
    matriculas_filtradas = [m for m in matriculas if search_text.lower() in m.lower()]

    if not matriculas_filtradas:
        st.warning("No se encontraron vehículos con ese texto.")
        return

    matricula = st.selectbox("Selecciona la matrícula", matriculas_filtradas)

    fecha = st.date_input("Fecha", fecha_default)

    if st.button("Consultar eficiencia"):
        st.info(f"Consultando datos para {matricula} el {fecha.strftime('%Y-%m-%d')}...")

        base_url = "http://localhost:3000/plannerstats/BI/vehiculoiot-eficiencia"
        params = {
            "fecha": fecha.strftime("%Y-%m-%d"),
            "matricula": matricula
        }
        headers = {"x-api-key": api_key}
        
        try:
            response = requests.get(base_url, params=params, headers=headers)
            response.raise_for_status()
            datos = response.json()
            if not datos:
                st.warning("No se encontraron datos para ese día.")
                return
        except requests.exceptions.RequestException as e:
            st.error(f"Error al consultar la API: {e}")
            return

        # Conversión a DataFrame
        df = pd.DataFrame(datos)
        df["evTime"] = pd.to_datetime(df["evTime"], errors='coerce')
        df["energyConsumption_ave"] = pd.to_numeric(df["energyConsumption"].apply(lambda x: x.get("ave", None)), errors='coerce')
        df["energyConsumption_rt"] = pd.to_numeric(df["energyConsumption"].apply(lambda x: x.get("rt", None)), errors='coerce')
        df["outsideTemp"] = pd.to_numeric(df["outsideTemp"], errors='coerce')
        df["insideTemp"] = pd.to_numeric(df["insideTemp"], errors='coerce')

        # Validación de que las columnas necesarias no estén vacías
        if df.empty:
            st.warning("No hay datos válidos para graficar.")
            return

        # Métricas generales
        distancia_total = df["mileage"].max() - df["mileage"].min()
        consumo_medio = df["energyConsumption_ave"].mean()
        eficiencia_kwh_100km = (consumo_medio / distancia_total * 100) if distancia_total > 0 else None

        st.subheader("📈 Métricas generales")
        col1, col2, col3 = st.columns(3)
        col1.metric("Distancia recorrida (km)", f"{distancia_total:.2f}")
        col2.metric("Consumo medio (kWh/100km)", f"{eficiencia_kwh_100km:.2f}" if eficiencia_kwh_100km else "N/A")
        col3.metric("SOC inicial", f"{df['soc'].iloc[0]}%")

        col21, col22 = st.columns(2)
        # Gráficos
        col21.subheader("🔋 Eficiencia energética (media)")
        if not df["energyConsumption_ave"].isnull().all():
            col21.line_chart(df.set_index("evTime")[["energyConsumption_ave"]])
        else:
            col21.warning("No hay datos para la eficiencia energética (media).")

        col22.subheader("🔋 Eficiencia energética (tiempo real)")
        if not df["energyConsumption_rt"].isnull().all():
            col22.line_chart(df.set_index("evTime")[["energyConsumption_rt"]])
        else:
            col22.warning("No hay datos para la eficiencia energética (tiempo real).")

        col31, col32 = st.columns(2)
        col31.subheader("🚗 Velocidad del vehículo")
        if not df["speed"].isnull().all():
            col31.line_chart(df.set_index("evTime")[["speed"]])
        else:
            col31.warning("No hay datos de velocidad.")

        col32.subheader("🔌 Nivel de batería (SOC)")
        if not df["soc"].isnull().all():
            col32.line_chart(df.set_index("evTime")[["soc"]])
        else:
            col32.warning("No hay datos de nivel de batería.")

        col41, col42 = st.columns(2)
        col41.subheader("🌡️ Temperatura exterior")
        if not df["outsideTemp"].isnull().all():
            col41.line_chart(df.set_index("evTime")[["outsideTemp"]])
        else:
            col41.warning("No hay datos de temperatura exterior.")

        col42.subheader("🌡️ Temperatura interior")
        if not df["insideTemp"].isnull().all():
            col42.line_chart(df.set_index("evTime")[["insideTemp"]])
        else:
            col42.warning("No hay datos de temperatura interior.")
