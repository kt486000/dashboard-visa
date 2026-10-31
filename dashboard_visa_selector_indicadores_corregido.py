# Dashboard académico de Visa Inc. — Big Data Analytics
# Requisitos: Python 3.10+ recomendado
# Instalar dependencias en CMD/Terminal:
#   py -m pip install streamlit pandas plotly numpy
# Ejecutar desde la carpeta donde está este archivo:
#   py -m streamlit run dashboard_visa.py

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Visa Inc. | Big Data Analytics",
    page_icon="📊",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Datos anuales de muestra. Verifica las cifras contra los informes anuales
# citados al final antes de entregar el trabajo.
# No se generan datos semanales/mensuales ficticios.
# -----------------------------------------------------------------------------
ANNUAL = pd.DataFrame(
    {
        "Año": [2021, 2022, 2023, 2024, 2025],
        "Ingresos netos (USD miles de millones)": [24.105, 29.310, 32.653, 35.926, 40.000],
        "Gastos operativos GAAP (USD miles de millones)": [8.301, 10.497, 11.653, 12.331, 16.006],
        "Utilidad neta (USD miles de millones)": [12.311, 14.957, 17.273, 19.743, 20.058],
        "Volumen de pagos (USD billones)": [10.4, 11.6, 12.3, 13.2, 14.2],
        "Transacciones procesadas (miles de millones)": [164.7, 192.5, 212.6, 233.8, 257.5],
    }
)

# Indicadores derivados: se calculan a partir de las series anuales disponibles.
# El primer año queda vacío en las tasas de crecimiento porque no hay año previo.
ANNUAL["Margen neto (%)"] = (
    ANNUAL["Utilidad neta (USD miles de millones)"]
    / ANNUAL["Ingresos netos (USD miles de millones)"] * 100
)
ANNUAL["Gastos operativos / ingresos (%)"] = (
    ANNUAL["Gastos operativos GAAP (USD miles de millones)"]
    / ANNUAL["Ingresos netos (USD miles de millones)"] * 100
)
ANNUAL["Crecimiento de ingresos (%)"] = (
    ANNUAL["Ingresos netos (USD miles de millones)"].pct_change() * 100
)
ANNUAL["Crecimiento de gastos operativos (%)"] = (
    ANNUAL["Gastos operativos GAAP (USD miles de millones)"].pct_change() * 100
)
ANNUAL["Crecimiento de utilidad neta (%)"] = (
    ANNUAL["Utilidad neta (USD miles de millones)"].pct_change() * 100
)

GEO = pd.DataFrame(
    {
        "Año": [2022, 2023, 2024, 2025] * 2,
        "Geografía": ["Estados Unidos"] * 4 + ["Internacional"] * 4,
        "Ingresos (USD miles de millones)": [
            12.851, 14.138, 14.780, 15.633,
            16.459, 18.515, 21.146, 24.367,
        ],
    }
)

DATE_NAMES = {"fecha", "date", "periodo", "period", "fecha_periodo", "period_date"}
FREQUENCIES = ["Anual", "Semestral", "Trimestral", "Bimestral", "Mensual", "Semanal"]


def money_or_number(value: float) -> str:
    """Formato compacto para tarjetas KPI."""
    return f"{value:,.3f}"


def prepare_uploaded_data(uploaded_file: object) -> tuple[pd.DataFrame | None, str | None]:
    """Lee y valida un CSV que incluya fecha y al menos una columna numérica."""
    try:
        raw = pd.read_csv(uploaded_file)
    except Exception as exc:  # muestra errores de lectura en la interfaz
        return None, f"No se pudo leer el CSV: {exc}"

    raw.columns = [str(column).strip() for column in raw.columns]
    date_column = next(
        (column for column in raw.columns if column.strip().lower() in DATE_NAMES),
        None,
    )
    if date_column is None:
        return None, "El CSV necesita una columna de fecha: fecha, date, periodo o period."

    raw[date_column] = pd.to_datetime(raw[date_column], errors="coerce")
    raw = raw.dropna(subset=[date_column]).sort_values(date_column)
    numeric_columns = raw.select_dtypes(include="number").columns.tolist()
    if not numeric_columns:
        return None, "El CSV necesita al menos una columna numérica además de la fecha."
    if raw.empty:
        return None, "No se encontraron fechas válidas en el CSV."

    return raw, None


def resample_rule(frequency: str) -> str:
    """Frecuencias de pandas para agrupar por periodos calendario."""
    return {
        "Semanal": "W-SUN",
        "Bimestral": "2ME",
        "Mensual": "ME",
        "Trimestral": "QE",
        "Semestral": "2QE",
        "Anual": "YE",
    }[frequency]


st.title("Visa Inc. — Dashboard de Big Data Analytics")
st.caption(
    "Panel académico de indicadores, evolución temporal, comparación geográfica "
    "y tendencia exploratoria. Periodo histórico: 2021–2025."
)

with st.sidebar:
    st.header("Filtros del dashboard")
    frequency = st.selectbox("Periodicidad", FREQUENCIES, index=0)
    geography = st.selectbox(
        "Geografía",
        ["Global", "Estados Unidos", "Internacional"],
        index=0,
    )
    annual_indicators = [
        "Ingresos netos (USD miles de millones)",
        "Utilidad neta (USD miles de millones)",
        "Volumen de pagos (USD billones)",
        "Transacciones procesadas (miles de millones)",
        "Margen neto (%)",
    ]
    periodic_indicators = [
        "Visa Spending Momentum Index (SMI)",
        "Ventas minoristas de EE. UU.",
        "Índice de precios al consumidor (CPI)",
        "Tasa de desempleo de EE. UU.",
        "Weekly Economic Index (WEI)",
    ]
    indicator_options = annual_indicators if frequency == "Anual" else periodic_indicators
    kpi = st.selectbox("Indicador", indicator_options)
    st.divider()
    uploaded_file = st.file_uploader(
        "Cargar datos detallados (CSV)",
        type=["csv"],
        help="Debe incluir una columna de fecha y una o más columnas numéricas.",
    )

# -----------------------------------------------------------------------------
# Si se carga un CSV, mostrar datos agrupados según la periodicidad seleccionada.
# -----------------------------------------------------------------------------
if uploaded_file is not None:
    raw, error = prepare_uploaded_data(uploaded_file)
    if error:
        st.error(error)
        st.stop()

    assert raw is not None
    date_column = next(
        column for column in raw.columns if column.strip().lower() in DATE_NAMES
    )
    numeric_columns = raw.select_dtypes(include="number").columns.tolist()

    left, right = st.columns([2, 1])
    with left:
        uploaded_metric = st.selectbox("Indicador del CSV", numeric_columns)
    with right:
        aggregation = st.selectbox(
            "Cómo agrupar los datos",
            ["Suma", "Promedio", "Último valor"],
            help=(
                "Elige según el significado del indicador. Por ejemplo, las transacciones "
                "de un periodo suelen sumarse; una tasa puede requerir promedio."
            ),
        )

    series = raw[[date_column, uploaded_metric]].copy()
    series = series.set_index(date_column)[uploaded_metric].sort_index()
    rule = resample_rule(frequency)
    resampler = series.resample(rule)
    if aggregation == "Suma":
        grouped = resampler.sum(min_count=1)
    elif aggregation == "Promedio":
        grouped = resampler.mean()
    else:
        grouped = resampler.last()
    grouped = grouped.dropna().rename(uploaded_metric).reset_index()
    grouped = grouped.rename(columns={date_column: "Fecha"})

    st.info(
        "La visualización utiliza el CSV que cargaste. Comprueba que la frecuencia "
        "original y el método de agregación sean adecuados para tu indicador."
    )
    if grouped.empty:
        st.warning("No hay valores que mostrar después de agrupar el CSV.")
    else:
        latest = grouped[uploaded_metric].iloc[-1]
        previous = grouped[uploaded_metric].iloc[-2] if len(grouped) > 1 else np.nan
        col1, col2, col3 = st.columns(3)
        col1.metric("Último valor del periodo", f"{latest:,.3f}")
        if pd.notna(previous) and previous != 0:
            col2.metric("Cambio respecto al periodo anterior", f"{(latest / previous - 1) * 100:+.1f}%")
        else:
            col2.metric("Cambio respecto al periodo anterior", "N/D")
        col3.metric("Periodos disponibles", f"{len(grouped):,}")

        st.plotly_chart(
            px.line(
                grouped,
                x="Fecha",
                y=uploaded_metric,
                markers=True,
                title=f"{uploaded_metric} — agrupación {frequency.lower()}",
            ),
            use_container_width=True,
        )
        st.dataframe(grouped, use_container_width=True, hide_index=True)
        st.download_button(
            "Descargar datos agrupados en CSV",
            data=grouped.to_csv(index=False).encode("utf-8-sig"),
            file_name="visa_datos_agrupados.csv",
            mime="text/csv",
        )
    st.stop()

# -----------------------------------------------------------------------------
# Vista con los datos anuales incorporados.
# -----------------------------------------------------------------------------
if frequency != "Anual":
    st.subheader(f"Indicadores por periodicidad — {frequency}")
    st.caption(
        "Las series no financieras son indicadores de contexto. Solo el SMI procede "
        "de Visa; las demás fuentes son externas y no representan resultados contables de Visa."
    )

    @st.cache_data(ttl=86400)
    def load_fred_series(series_id: str) -> pd.DataFrame:
        url = (
            "https://fred.stlouisfed.org/graph/fredgraph.csv"
            f"?id={series_id}&cosd=2021-01-01&coed=2025-12-31"
        )
        data = pd.read_csv(url)
        data.columns = ["Fecha", "Valor"]
        data["Fecha"] = pd.to_datetime(data["Fecha"], errors="coerce")
        data["Valor"] = pd.to_numeric(data["Valor"], errors="coerce")
        return data.dropna().sort_values("Fecha")

    # Cinco indicadores disponibles en las vistas no anuales.
    external_options = {
        "Visa Spending Momentum Index (SMI)": {
            "id": "VISASMIHSA",
            "source": "Visa vía FRED",
            "description": "Índice mensual de momentum del gasto basado en transacciones Visa en EE. UU.",
            "native": "Mensual",
        },
        "Ventas minoristas de EE. UU.": {
            "id": "RSXFS",
            "source": "U.S. Census Bureau vía FRED",
            "description": "Ventas minoristas y de servicios de alimentos en EE. UU., en millones de USD.",
            "native": "Mensual",
        },
        "Índice de precios al consumidor (CPI)": {
            "id": "CPIAUCSL",
            "source": "U.S. Bureau of Labor Statistics vía FRED",
            "description": "Índice de precios al consumidor de EE. UU., ajustado estacionalmente.",
            "native": "Mensual",
        },
        "Tasa de desempleo de EE. UU.": {
            "id": "UNRATE",
            "source": "U.S. Bureau of Labor Statistics vía FRED",
            "description": "Porcentaje de la fuerza laboral civil desempleada en EE. UU.",
            "native": "Mensual",
        },
        "Weekly Economic Index (WEI)": {
            "id": "WEI",
            "source": "Lewis, Mertens y Stock vía FRED",
            "description": "Índice semanal de actividad económica de EE. UU.; no es un indicador de Visa.",
            "native": "Semanal",
        },
    }

    # El selector de la barra lateral controla también las vistas no anuales.
    selected_external = kpi
    config = external_options[selected_external]

    try:
        external = load_fred_series(config["id"])
        if frequency == "Semanal":
            # Para series mensuales, se conserva el valor mensual y no se inventan semanas.
            if config["native"] == "Semanal":
                chart_data = external.copy()
            else:
                st.info(
                    "Esta serie se publica mensualmente. En periodicidad semanal se muestra "
                    "su último dato mensual disponible por semana, sin interpolar valores."
                )
                chart_data = external.copy()
        else:
            rule = {
                "Bimestral": "2ME",
                "Mensual": "ME",
                "Trimestral": "QE",
                "Semestral": "2QE",
            }[frequency]
            chart_data = (
                external.set_index("Fecha")["Valor"]
                .resample(rule)
                .mean()
                .dropna()
                .rename("Valor")
                .reset_index()
            )

        chart_data = chart_data[
            (chart_data["Fecha"] >= "2021-01-01")
            & (chart_data["Fecha"] <= "2025-12-31")
        ].copy()

        st.caption(f"Fuente: {config['source']}. {config['description']}")
        if chart_data.empty:
            st.warning("La fuente no devolvió observaciones para 2021–2025.")
        else:
            latest = float(chart_data["Valor"].iloc[-1])
            previous = float(chart_data["Valor"].iloc[-2]) if len(chart_data) > 1 else np.nan
            c1, c2, c3 = st.columns(3)
            c1.metric("Último valor", f"{latest:,.2f}")
            c2.metric(
                "Cambio vs. periodo anterior",
                f"{latest - previous:+,.2f}" if pd.notna(previous) else "N/D",
            )
            c3.metric("Observaciones", f"{len(chart_data):,}")

            st.plotly_chart(
                px.line(
                    chart_data,
                    x="Fecha",
                    y="Valor",
                    markers=True,
                    title=f"{selected_external} — {frequency.lower()} (2021–2025)",
                ),
                use_container_width=True,
            )
            st.dataframe(chart_data, use_container_width=True, hide_index=True)
            st.download_button(
                "Descargar esta serie en CSV",
                data=chart_data.to_csv(index=False).encode("utf-8-sig"),
                file_name="visa_indicador_periodico.csv",
                mime="text/csv",
            )
    except Exception as exc:
        st.error(
            "No se pudo descargar la serie desde FRED. Verifica tu conexión a internet "
            f"e inténtalo de nuevo. Detalle: {exc}"
        )
    st.stop()


# -----------------------------------------------------------------------------
# Vista anual: resultados financieros y operativos de Visa.
# -----------------------------------------------------------------------------
annual_data = ANNUAL.copy()

if geography != "Global":
    # La desagregación geográfica disponible corresponde a ingresos 2022–2025.
    st.info(
        "La selección geográfica solo aplica al desglose de ingresos. "
        "Los demás indicadores se muestran a nivel global."
    )

if kpi not in annual_data.columns:
    st.error("El indicador seleccionado no está disponible en la base anual.")
    st.stop()

st.subheader(f"{kpi} — evolución anual")

metric_values = annual_data[kpi].dropna()
if metric_values.empty:
    st.warning("No hay datos disponibles para este indicador.")
else:
    last_value = float(metric_values.iloc[-1])
    first_value = float(metric_values.iloc[0])
    change = last_value - float(metric_values.iloc[-2]) if len(metric_values) > 1 else np.nan

    c1, c2, c3 = st.columns(3)
    c1.metric("Último dato (2025)", money_or_number(last_value))
    c2.metric(
        "Cambio frente al año anterior",
        f"{change:+,.3f}" if pd.notna(change) else "N/D",
    )
    c3.metric("Cambio 2021–2025", f"{last_value - first_value:+,.3f}")

    annual_chart = annual_data[["Año", kpi]].dropna()
    st.plotly_chart(
        px.line(
            annual_chart,
            x="Año",
            y=kpi,
            markers=True,
            title=f"{kpi} (2021–2025)",
        ),
        use_container_width=True,
    )
    st.dataframe(annual_chart, use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar indicador anual en CSV",
        data=annual_chart.to_csv(index=False).encode("utf-8-sig"),
        file_name="visa_indicador_anual.csv",
        mime="text/csv",
    )

if kpi == "Ingresos netos (USD miles de millones)" and geography != "Global":
    geo_selected = GEO[GEO["Geografía"] == geography]
    st.subheader(f"Ingresos por geografía — {geography}")
    st.plotly_chart(
        px.bar(
            geo_selected,
            x="Año",
            y="Ingresos (USD miles de millones)",
            title=f"Ingresos de Visa: {geography}",
        ),
        use_container_width=True,
    )
    st.dataframe(geo_selected, use_container_width=True, hide_index=True)
