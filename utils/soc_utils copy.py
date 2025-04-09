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

                # Resaltar los valores donde el SOC esté por debajo del 20%
                low_soc_mask = df['avgSOC'] < 20
                low_soc_points = df[low_soc_mask]

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df["avgSOC"], mode="lines", name="SOC promedio", line=dict(color="blue")))
                fig.add_trace(go.Scatter(x=low_soc_points["timestamp"], y=low_soc_points["avgSOC"], mode="markers", name="SOC bajo (bajo 20%)", marker=dict(color="red", size=10, symbol="x")))

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

                # Alerta de bajo SOC
                if not low_soc_points.empty:
                    st.warning("🚨 ¡Alerta! El vehículo está por debajo del 20% de SOC y debe regresar a la cochera.")
                
                st.subheader("📋 Tabla de datos")
                st.dataframe(df[["timestamp", "minSOC", "avgSOC", "maxSOC", "count"]])
            else:
                st.warning("No se encontraron datos.")
        else:
            st.error(f"Error al consultar la API: {response.status_code}")
        # Mostrar el estado del vehículo
        show_vehicle_status(matricula, fecha, api_key)

def show_vehicle_status(matricula, fecha, api_key):
    """Mostrar los registros del estado de un vehículo (carga, estatus de batería y estatus de vehículo)"""
    st.subheader("📋 Estado del vehículo")

    base_url = f"http://localhost:3000/plannerstats/BI/vehiculoiot-status"
    params = {
        "fecha": fecha.strftime("%Y-%m-%d"),
        "matricula": matricula
    }

    headers = {
        "x-api-key": api_key
    }

    with st.spinner("Obteniendo estado del vehículo..."):
        response = requests.get(base_url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()

        if data:
            df_status = pd.DataFrame(data)
            df_status["evTime"] = pd.to_datetime(df_status["evTime"])

            # Mostrar tabla de datos
            st.dataframe(df_status[["evTime", "gbCharge", "gbStatus", "evStatus"]])

            # Convertir los estados a valores numéricos para graficarlos
            gbStatus_map = {"Start": 1, "Stop": 2, "Idle": 3}  # Asignar valores numéricos
            gbCharge_map = {"Charging": 1, "Not in Charging": 0}  # 1: Charging, 0: Not in Charging
            evStatus_map = {"Active": 1, "Inactive": 2, "Error": 3}  # Mapear los posibles estados de evStatus

            df_status["gbStatus_num"] = df_status["gbStatus"].map(gbStatus_map)
            df_status["gbCharge_num"] = df_status["gbCharge"].map(gbCharge_map)
            df_status["evStatus_num"] = df_status["evStatus"].map(evStatus_map)

            # Gráfica para gbStatus
            fig_status = go.Figure()
            fig_status.add_trace(go.Scatter(
                x=df_status["evTime"],
                y=df_status["gbStatus_num"],
                mode="markers+lines",
                name="gbStatus",
                marker=dict(color="blue", size=8)
            ))

            fig_status.update_layout(
                title="Estado del vehículo (gbStatus) a lo largo del día",
                xaxis_title="Hora",
                yaxis_title="Estado (gbStatus)",
                yaxis=dict(tickvals=[1, 2, 3], ticktext=["Start", "Stop", "Idle"]),
                height=400,
                showlegend=True,
                hovermode="x unified"
            )

            st.plotly_chart(fig_status, use_container_width=True)

            # Gráfica para gbCharge
            fig_charge = go.Figure()
            fig_charge.add_trace(go.Scatter(
                x=df_status["evTime"],
                y=df_status["gbCharge_num"],
                mode="markers+lines",
                name="gbCharge",
                marker=dict(color="green", size=8)
            ))

            fig_charge.update_layout(
                title="Estado de carga del vehículo (gbCharge) a lo largo del día",
                xaxis_title="Hora",
                yaxis_title="Estado de carga (gbCharge)",
                yaxis=dict(tickvals=[0, 1], ticktext=["No en carga", "En carga"]),
                height=400,
                showlegend=True,
                hovermode="x unified"
            )

            st.plotly_chart(fig_charge, use_container_width=True)

            # Gráfica para evStatus
            fig_evstatus = go.Figure()
            fig_evstatus.add_trace(go.Scatter(
                x=df_status["evTime"],
                y=df_status["evStatus_num"],
                mode="markers+lines",
                name="evStatus",
                marker=dict(color="orange", size=8)
            ))

            fig_evstatus.update_layout(
                title="Estado del vehículo (evStatus) a lo largo del día",
                xaxis_title="Hora",
                yaxis_title="Estado (evStatus)",
                yaxis=dict(tickvals=[1, 2, 3], ticktext=["Activo", "Inactivo", "Error"]),
                height=400,
                showlegend=True,
                hovermode="x unified"
            )

            st.plotly_chart(fig_evstatus, use_container_width=True)

        else:
            st.warning("No se encontraron registros de estado para este vehículo.")
    else:
        st.error(f"Error al consultar el estado del vehículo: {response.status_code}")

    """Mostrar los registros del estado de un vehículo (carga y estatus)"""
    st.subheader("📋 Estado del vehículo")

    base_url = f"http://localhost:3000/plannerstats/BI/vehiculoiot-status"
    params = {
        "fecha": fecha.strftime("%Y-%m-%d"),
        "matricula": matricula
    }

    headers = {
        "x-api-key": api_key
    }

    with st.spinner("Obteniendo estado del vehículo..."):
        response = requests.get(base_url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()

        if data:
            df_status = pd.DataFrame(data)
            df_status["evTime"] = pd.to_datetime(df_status["evTime"])

            # Mostrar tabla de datos
            # st.dataframe(df_status[["evTime", "gbCharge", "gbStatus"]])

            # Convertir los estados a valores numéricos para graficarlos
            gbStatus_map = {"Start": 1, "Stop": 2, "Idle": 3}  # Asignar valores numéricos
            gbCharge_map = {"Charging": 1, "Not in Charging": 0}  # 1: Charging, 0: Not in Charging

            df_status["gbStatus_num"] = df_status["gbStatus"].map(gbStatus_map)
            df_status["gbCharge_num"] = df_status["gbCharge"].map(gbCharge_map)

            # Gráfica para gbStatus
            fig_status = go.Figure()

            fig_status.add_trace(go.Scatter(
                x=df_status["evTime"],
                y=df_status["gbStatus_num"],
                mode="markers+lines",
                name="gbStatus",
                marker=dict(color="blue", size=8)
            ))

            fig_status.update_layout(
                title="Estado del vehículo (gbStatus) a lo largo del día",
                xaxis_title="Hora",
                yaxis_title="Estado (gbStatus)",
                yaxis=dict(tickvals=[1, 2, 3], ticktext=["Start", "Stop", "Idle"]),
                height=400,
                showlegend=True,
                hovermode="x unified"
            )

            st.plotly_chart(fig_status, use_container_width=True)

            # Gráfica para gbCharge
            fig_charge = go.Figure()

            fig_charge.add_trace(go.Scatter(
                x=df_status["evTime"],
                y=df_status["gbCharge_num"],
                mode="markers+lines",
                name="gbCharge",
                marker=dict(color="green", size=8)
            ))

            fig_charge.update_layout(
                title="Estado de carga del vehículo (gbCharge) a lo largo del día",
                xaxis_title="Hora",
                yaxis_title="Estado de carga (gbCharge)",
                yaxis=dict(tickvals=[0, 1], ticktext=["No en carga", "En carga"]),
                height=400,
                showlegend=True,
                hovermode="x unified"
            )

            st.plotly_chart(fig_charge, use_container_width=True)

        else:
            st.warning("No se encontraron registros de estado para este vehículo.")
    else:
        st.error(f"Error al consultar el estado del vehículo: {response.status_code}")

    """Mostrar los registros del estado de un vehículo (carga y estatus)"""
    st.subheader("📋 Estado del vehículo")

    base_url = f"http://localhost:3000/plannerstats/BI/vehiculoiot-status"
    params = {
        "fecha": fecha.strftime("%Y-%m-%d"),
        "matricula": matricula
    }

    headers = {
        "x-api-key": api_key
    }

    with st.spinner("Obteniendo estado del vehículo..."):
        response = requests.get(base_url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()

        if data:
            df_status = pd.DataFrame(data)
            df_status["evTime"] = pd.to_datetime(df_status["evTime"])

            st.dataframe(df_status[["evTime", "gbCharge", "gbStatus"]])
        else:
            st.warning("No se encontraron registros de estado para este vehículo.")
    else:
        st.error(f"Error al consultar el estado del vehículo: {response.status_code}")