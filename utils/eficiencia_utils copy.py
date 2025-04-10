# eficiencia_utils.py

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

def obtener_vehiculos(api_key):
    """Obtener los vehículos desde la API"""
    base_url = "http://localhost:3000/plannerstats/vehiculos"
    headers = {"x-api-key": api_key}

    response = requests.get(base_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener los vehículos: {response.status_code}")
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
        response = requests.get(base_url, params=params, headers=headers)

        if response.status_code == 200:
            datos = response.json()
            if not datos:
                st.warning("No se encontraron datos para ese día.")
                return
        else:
            st.error(f"Error al consultar la API: {response.status_code}")
            return

        # Conversión a DataFrame
        df = pd.DataFrame(datos)
        df["evTime"] = pd.to_datetime(df["evTime"])
        df["energyConsumption_ave"] = pd.to_numeric(df["energyConsumption"].apply(lambda x: x.get("ave", None)), errors='coerce')
        df["energyConsumption_rt"] = pd.to_numeric(df["energyConsumption"].apply(lambda x: x.get("rt", None)), errors='coerce')
        df["outsideTemp"] = pd.to_numeric(df["outsideTemp"], errors='coerce')
        df["insideTemp"] = pd.to_numeric(df["insideTemp"], errors='coerce')

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
        col21.line_chart(df.set_index("evTime")[["energyConsumption_ave"]])
        col22.subheader("🔋 Eficiencia energética (tiempo real)")
        col22.line_chart(df.set_index("evTime")[["energyConsumption_rt"]])

        col31, col32 = st.columns(2)
        col31.subheader("🚗 Velocidad del vehículo")
        col31.line_chart(df.set_index("evTime")[["speed"]])

        col32.subheader("🔌 Nivel de batería (SOC)")
        col32.line_chart(df.set_index("evTime")[["soc"]])

        col41, col42 = st.columns(2)
        col41.subheader("🌡️ Temperatura exterior")
        col41.line_chart(df.set_index("evTime")[["outsideTemp"]])
        col42.subheader("🌡️ Temperatura interior")
        col42.line_chart(df.set_index("evTime")[["insideTemp"]])
