import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import io

st.set_page_config(layout="wide")
st.title("TEXA csv LOGVIEWER by MG")

uploaded_file = st.file_uploader("Wähle eine TEXA-CSV-Datei", type=["csv"])

if uploaded_file is not None:
    try:
        # Datei lesen (TEXA = UTF-16)
        text_io = io.TextIOWrapper(uploaded_file, encoding='utf-16')
        raw_lines = text_io.readlines()

        # Zeilen aufteilen per Tab + Spalten auffüllen
        split_data = [line.rstrip('\n').split('\t') for line in raw_lines if line.strip()]
        max_columns = max(len(row) for row in split_data)
        split_data = [row + [''] * (max_columns - len(row)) for row in split_data]

        # Header reparieren: Zeit aus Zeile 12, Kanäle aus Zeile 10
        zeit_header = split_data[11][0:2]
        mess_header = split_data[9][2:]
        header = zeit_header + mess_header
        units = split_data[10][2:]
        data_rows = [row[0:2] + row[2:] for row in split_data[12:] if len(row) == len(split_data[11])]
        df = pd.DataFrame(data_rows, columns=header)

        # Konvertieren
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
        df = df.dropna(axis=1, how='all')
        df = df.applymap(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
        df = df.apply(pd.to_numeric, errors='ignore')
        df = df.reset_index(drop=True)

        st.success("Datei erfolgreich geladen.")

        # Zeitspalte
        zeitspalte = next((col for col in df.columns if "relative" in col.lower() and "zeit" in col.lower()), None)
        if zeitspalte:
            x_axis = pd.to_numeric(df[zeitspalte], errors='coerce')
            x_label = zeitspalte
        else:
            st.warning("❗ Keine gültige Zeitachse gefunden – verwende Messpunktindex.")
            x_axis = df.index
            x_label = "Messpunktindex"

        # Uhrzeit (optional)
        uhrzeit_col = next((col for col in df.columns if "uhrzeit" in col.lower()), None)
        uhrzeit_tooltip = df[uhrzeit_col] if uhrzeit_col else None

        # Optionen (Sidebar)
        with st.sidebar:
            st.markdown("### Tooltip-Anzeige")
            zeige_zeit = st.checkbox("RELATIVE ZEIT anzeigen", value=True)
            zeige_uhrzeit = st.checkbox("Uhrzeit anzeigen", value=False)
            zeige_label = st.checkbox("Messgrößenname anzeigen", value=True)

            st.markdown("### Darstellung")
            normieren = st.checkbox("Kurven optisch normieren (0–1)", value=True)

            st.markdown("### Bereich markieren")
            bereich_start = st.number_input("Startzeit (s)", min_value=0.0, value=0.0)
            bereich_ende = st.number_input("Endzeit (s)", min_value=0.0, value=10.0)

        # Messgrößen-Auswahl
        exclude = [x_label]
        if uhrzeit_col:
            exclude.append(uhrzeit_col)
        y_options = [col for col in df.columns if col not in exclude]
        y_cols = st.multiselect("Messgrößen auswählen", options=y_options, default=[])

        if y_cols:
            fig = go.Figure()
            for col in y_cols:
                werte = df[col]
                original = werte.copy()
                if normieren and werte.max() != werte.min():
                    werte = (werte - werte.min()) / (werte.max() - werte.min())

                einheit = f" [{units[mess_header.index(col)]}]" if col in mess_header and len(units) > mess_header.index(col) else ""

                hovertext = ""
                if zeige_label:
                    hovertext += col + ": "
                hovertext += original.astype(str)

                if zeige_zeit:
                    hovertext += "<br>" + x_label + ": " + x_axis.astype(str)
                if zeige_uhrzeit and uhrzeit_tooltip is not None:
                    hovertext += "<br>Uhrzeit: " + uhrzeit_tooltip.astype(str)

                fig.add_trace(go.Scatter(
                    x=x_axis,
                    y=werte,
                    mode='lines',
                    name=col + einheit,
                    hovertext=hovertext,
                    hoverinfo='text'
                ))

            # Zeitfenster hervorheben
            if zeitspalte and bereich_ende > bereich_start:
                fig.add_vrect(
                    x0=bereich_start,
                    x1=bereich_ende,
                    fillcolor="gray",
                    opacity=0.2,
                    line_width=0,
                    annotation_text="Markiert",
                    annotation_position="top left"
                )

            fig.update_layout(
                title="Mehrkanal-Diagramm (VC Scope Style)",
                xaxis_title=x_label,
                yaxis_title="Normiert (0–1)" if normieren else "Wert",
                height=650,
                hovermode="x unified"
            )
            fig.update_xaxes(rangeslider_visible=True)
            st.plotly_chart(fig, use_container_width=True)

            # PNG-Export
            png_data = fig.to_image(format="png")
            st.download_button(
                label="📷 Diagramm als PNG speichern",
                data=png_data,
                file_name="texa_scope_export.png"
            )
        else:
            st.info("Bitte mindestens eine Messgröße auswählen.")

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")
else:
    st.info("Bitte lade eine TEXA-CSV-Datei hoch.")
