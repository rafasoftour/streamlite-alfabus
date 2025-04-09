import streamlit as st
from datetime import datetime, timedelta
from utils.soc_utils import show_soc_analysis
from utils.soc_low import show_low_soc_view

st.set_page_config("Análisis Vehículos Eléctricos", layout="wide")

def main():
    st.sidebar.title("🔧 Panel de control")
    page = st.sidebar.selectbox(
        "Selecciona un estudio",
        [
            "Inicio",
            "Vehículos con SOC bajo (<20%)",
            "SOC por fecha y vehículo",

            # "Consumo energético",
            # "Temperaturas",
            # "Eventos de carga",
            # etc.
        ]
    )

    # Definir la fecha de ayer como valor por defecto
    ayer = datetime.now() - timedelta(days=1)
    fecha_default = ayer.date()
    api_key = "cab94416ab19e7a249d6c1469c36b3c81ed3c33a7ed7fc67cab4df91e1ace823"

    if page == "Inicio":
        st.title("🚍 Análisis de Vehículos Eléctricos")
        st.write("Selecciona una opción en el menú lateral para comenzar.")
        st.info("Este visor permite analizar la eficiencia de carga y uso de los vehículos eléctricos.")

    elif page == "SOC por fecha y vehículo":
        show_soc_analysis(fecha_default, api_key)

    elif page == "Vehículos con SOC bajo (<20%)":
        show_low_soc_view(fecha_default, api_key)

if __name__ == "__main__":
    main()
