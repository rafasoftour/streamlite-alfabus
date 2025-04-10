# eficiencia_utils.py

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

def obtener_maximos_dia(api_key, fecha):
    """Llama a la API para obtener máximos globales de distancia y eficiencia en ese día."""
    base_url = "http://localhost:3000/plannerstats/BI/vehiculoiot-maxdia"
    params = {"fecha": fecha.strftime("%Y-%m-%d")}
    headers = {"x-api-key": api_key}

    response = requests.get(base_url, params=params, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener máximos del día: {response.status_code}")
        return {"maxDistance": None, "maxEnergyConsumptionAve": None}        

def show_kpi_gauge(title, value, min_value, max_value, color="lightblue"):
    """Crear gráfico gauge para mostrar un KPI"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        delta={'reference': (max_value + min_value) / 2},  # Mostrar delta respecto al valor medio
        gauge={
            'axis': {'range': [min_value, max_value]},
            'bar': {'color': color},
            'steps': [
                {'range': [min_value, (max_value + min_value) / 2], 'color': 'lightgreen'},
                {'range': [(max_value + min_value) / 2, max_value], 'color': 'tomato'}
            ],
        },
        title={'text': title}
    ))
    return fig        

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

        st.subheader("📈 Métricas generales (Valores comparados con los máximos para todos los vehículos ese dia)")
        # Cálculo de valores máximos dinámicos
        maximos = obtener_maximos_dia(api_key, fecha)
        max_dist = maximos.get("maxDistance")
        max_eff = maximos.get("maxEnergyConsumptionAve")
        soc_max = 100  # El máximo para el SOC es 100%

        # Mostrar KPI con gráfico gauge
        col1, col2, col3 = st.columns(3)
        # Gráficos con valores dinámicos
        fig_soc = show_kpi_gauge("SOC Inicial (%)", df['soc'].iloc[0], 0, soc_max)
        col1.plotly_chart(fig_soc)

        fig_eficiencia = show_kpi_gauge("Eficiencia energética (kWh/100km)", eficiencia_kwh_100km, 0, max_eff)
        col2.plotly_chart(fig_eficiencia)

        fig_distancia = show_kpi_gauge("Distancia recorrida (km)", distancia_total, 0, max_dist)
        col3.plotly_chart(fig_distancia)

        # Gráficos interactivos con Plotly
        col21, col22 = st.columns(2)
        col21.subheader("🔋 Eficiencia energética (media)")
        if not df["energyConsumption_ave"].isnull().all():
            fig1 = px.line(df, x="evTime", y="energyConsumption_ave", title="Eficiencia energética media")
            col21.plotly_chart(fig1)
        else:
            col21.warning("No hay datos para la eficiencia energética (media).")

        col22.subheader("🔋 Eficiencia energética (tiempo real)")
        if not df["energyConsumption_rt"].isnull().all():
            fig2 = px.line(df, x="evTime", y="energyConsumption_rt", title="Eficiencia energética tiempo real")
            col22.plotly_chart(fig2)
        else:
            col22.warning("No hay datos para la eficiencia energética (tiempo real).")

        col31, col32 = st.columns(2)
        col31.subheader("🚗 Velocidad del vehículo")
        if not df["speed"].isnull().all():
            fig3 = px.line(df, x="evTime", y="speed", title="Velocidad del vehículo")
            col31.plotly_chart(fig3)
        else:
            col31.warning("No hay datos de velocidad.")

        col32.subheader("🔌 Nivel de batería (SOC)")
        if not df["soc"].isnull().all():
            fig4 = px.line(df, x="evTime", y="soc", title="Nivel de batería (SOC)")
            col32.plotly_chart(fig4)
        else:
            col32.warning("No hay datos de nivel de batería.")

        col41, col42 = st.columns(2)
        col41.subheader("🌡️ Temperatura exterior")
        if not df["outsideTemp"].isnull().all():
            fig5 = px.line(df, x="evTime", y="outsideTemp", title="Temperatura exterior")
            col41.plotly_chart(fig5)
        else:
            col41.warning("No hay datos de temperatura exterior.")

        col42.subheader("🌡️ Temperatura interior")
        if not df["insideTemp"].isnull().all():
            fig6 = px.line(df, x="evTime", y="insideTemp", title="Temperatura interior")
            col42.plotly_chart(fig6)
        else:
            col42.warning("No hay datos de temperatura interior.")
