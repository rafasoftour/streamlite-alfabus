import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

def obtener_vehiculos(api_key):
    """Obtener los vehículos desde la API"""
    base_url = "http://localhost:3000/plannerstats/vehiculos"
    headers = {
        "x-api-key": api_key
    }

    response = requests.get(base_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener los vehículos: {response.status_code}")
        return []

def show_soc_analysis(fecha_default, api_key):
    st.title("🔋 Evolución del SOC por Vehículo")

    # Obtener vehículos desde la API
    vehiculos = obtener_vehiculos(api_key)
    
    if not vehiculos:
        st.warning("No se encontraron vehículos.")
        return
    
    # Extraer matrículas y permitir al usuario buscar
    matriculas = [vehiculo["matricula"] for vehiculo in vehiculos]
    
    # Añadir campo de texto para búsqueda
    search_text = st.text_input("Buscar matrícula", "")
    
    # Filtrar las matrículas basadas en la entrada del usuario
    matriculas_filtradas = [matricula for matricula in matriculas if search_text.lower() in matricula.lower()]
    
    if not matriculas_filtradas:
        st.warning("No se encontraron vehículos con ese texto.")
        return
    
    # Mostrar un selectbox con las matrículas filtradas
    matricula = st.selectbox("Selecciona la matrícula del vehículo", matriculas_filtradas)

    # Obtener los datos para la matrícula seleccionada
    vehiculo = next(veh for veh in vehiculos if veh["matricula"] == matricula)
    fecha = st.date_input("Fecha", fecha_default)
    bin_size = st.number_input("Tamaño del bin (min)", min_value=1, max_value=60, value=5)

    if st.button("Consultar SOC"):
        base_url = "http://localhost:3000/plannerstats/BI/vehiculoiot-socbin"
        params = {
            "fecha": fecha.strftime("%Y-%m-%d"),
            "matricula": matricula,
            "bin": str(bin_size)
        }

        headers = {
            "x-api-key": api_key
        }

        with st.spinner("Obteniendo datos..."):
            response = requests.get(base_url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()

            if data:
                df = pd.DataFrame(data)
                df["timestamp"] = pd.to_datetime(df["_id"].apply(lambda x: x["interval"]))
                df = df.sort_values("timestamp")

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df["avgSOC"], mode="lines", name="SOC promedio", line=dict(color="blue")))
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df["maxSOC"], mode="lines", name="SOC máximo", line=dict(width=0), showlegend=False))
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df["minSOC"], mode="lines", name="SOC mínimo", fill='tonexty', fillcolor='rgba(0,100,80,0.2)', line=dict(width=0), showlegend=False))

                fig.update_layout(
                    title="SOC durante el día",
                    xaxis_title="Hora",
                    yaxis_title="SOC (%)",
                    height=500,
                    hovermode="x unified"
                )

                st.plotly_chart(fig, use_container_width=True)
                st.subheader("📋 Tabla de datos")
                st.dataframe(df[["timestamp", "minSOC", "avgSOC", "maxSOC", "count"]])
            else:
                st.warning("No se encontraron datos.")
        else:
            st.error(f"Error al consultar la API: {response.status_code}")
