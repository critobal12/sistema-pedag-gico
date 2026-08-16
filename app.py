# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN Y CONEXIÓN
# -----------------------------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_ID_RAIZ = "13nUnzgBGfy3H9Y3U0cFoYRob75IKp681"

@st.cache_resource
def obtener_servicio_drive():
    creds = None
    if "gcp_service_account" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=SCOPES
            )
        except Exception as e:
            st.error(f"Error en Secrets: {e}")
            return None
    elif os.path.exists("credenciales.json"):
        creds = service_account.Credentials.from_service_account_file("credenciales.json", scopes=SCOPES)
    
    if creds:
        return build('drive', 'v3', credentials=creds)
    return None

drive_service = obtener_servicio_drive()

if "revisiones" not in st.session_state:
    st.session_state["revisiones"] = {}

# -----------------------------------------------------------------------------
# 2. INTERFAZ PRINCIPAL
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Sistema Pedagógico I.E.", page_icon="📚", layout="wide")

st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=70)
st.sidebar.title("🏛️ I.E. Control Pedagógico")
rol = st.sidebar.selectbox("Seleccionar Rol de Usuario:", ["Docente", "Coordinador", "Director"])
st.sidebar.divider()

if drive_service:
    st.sidebar.success("🟢 Conectado a Google Drive")
else:
    st.sidebar.warning("🔴 Sin conexión a Google Drive")

# -----------------------------------------------------------------------------
# 3. VISTA DOCENTE
# -----------------------------------------------------------------------------
if rol == "Docente":
    st.title("📤 Módulo de Carga - Docente")

    with st.form("form_docente", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            docente_nombre = st.text_input("Nombre del Docente:", value="Prof. Juan Pérez")
            coordinacion = st.selectbox("Coordinación:", ["Matemática y Ciencias", "Letras y Comunicación", "Innovación y EPT", "Desarrollo Personal"])
        with col2:
            area_grado = st.text_input("Área / Grado:", value="Matemática 2° Sec")
            periodo = st.selectbox("Periodo / Bimestre:", ["Bimestre I", "Bimestre II", "Bimestre III", "Bimestre IV"])

        tipo_doc = st.selectbox("Tipo de Documento:", ["PROGRAMACION_ANUAL", "UNIDAD_DE_APRENDIZAJE", "SESION_DE_APRENDIZAJE", "INSTRUMENTO_EVALUACION"])
        archivo = st.file_uploader("Seleccionar Archivo (PDF, DOCX, XLSX):", type=["pdf", "docx", "xlsx"])

        subir = st.form_submit_button("🚀 Subir Documento a Drive")

        if subir and archivo is not None:
            if drive_service:
                with st.spinner("Subiendo archivo a Google Drive..."):
                    try:
                        ruta_temp = os.path.join(".", archivo.name)
                        with open(ruta_temp, "wb") as f:
                            f.write(archivo.getbuffer())

                        nombre_final = f"{periodo.replace(' ','_')}_{tipo_doc}_{docente_nombre.replace(' ','_')}_{archivo.name}"
                        file_metadata = {'name': nombre_final, 'parents': [FOLDER_ID_RAIZ]}
                        media = MediaFileUpload(ruta_temp, resumable=True)

                        file_uploaded = drive_service.files().create(
                            body=file_metadata, media_body=media, fields='id, webViewLink'
                        ).execute()

                        if os.path.exists(ruta_temp):
                            os.remove(ruta_temp)

                        link_url = file_uploaded.get('webViewLink')
                        st.success(f"✅ ¡El archivo **{nombre_final}** se subió correctamente!")
                        st.link_button("🔗 Abrir documento en Google Drive", link_url)

                    except Exception as e:
                        st.error(f"❌ Error al subir: {e}")

# -----------------------------------------------------------------------------
# 4. VISTA COORDINADOR
# -----------------------------------------------------------------------------
elif rol == "Coordinador":
    st.title("🔍 Revisión Pedagógica - Coordinación")

    if drive_service:
        try:
            results = drive_service.files().list(
                q=f"'{FOLDER_ID_RAIZ}' in parents and trashed = false",
                fields="files(id, name, createdTime, webViewLink)"
            ).execute()
            
            items = results.get('files', [])

            if items:
                st.subheader("📂 Documentos Registrados y Enlaces Directos")
                df = pd.DataFrame(items)

                st.dataframe(
                    df[['name', 'createdTime', 'webViewLink']],
                    column_config={
                        "name": "Nombre del Archivo",
                        "createdTime": "Fecha de Carga",
                        "webViewLink": st.column_config.LinkColumn(
                            "Enlace Directo URL",
                            display_text="👁️ Ver en Google Drive"
                        )
                    },
                    use_container_width=True
                )

                st.divider()
                st.subheader("✍️ Evaluar Documento")
                doc_seleccionado = st.selectbox("Selecciona un documento:", [i["name"] for i in items])
                
                url_doc = next((i["webViewLink"] for i in items if i["name"] == doc_seleccionado), "#")
                st.link_button(f"📄 Abrir '{doc_seleccionado}' para revisar", url_doc)

                with st.form("form_eval"):
                    accion = st.radio("Dictamen:", ["🟢 APROBADO", "🔴 OBSERVADO"])
                    comentario = st.text_area("Observaciones:")
                    if st.form_submit_button("Guardar Dictamen"):
                        st.session_state["revisiones"][doc_seleccionado] = {
                            "Estado": accion,
                            "Comentario": comentario,
                            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        st.success("Evaluación guardada.")
                        st.rerun()
            else:
                st.info("No hay documentos en la carpeta de Drive.")

        except Exception as e:
            st.error(f"Error al listar documentos: {e}")

# -----------------------------------------------------------------------------
# 5. VISTA DIRECTOR
# -----------------------------------------------------------------------------
elif rol == "Director":
    st.title("📊 Dashboard Institucional - Dirección")
    st.dataframe(pd.DataFrame(list(st.session_state["revisiones"].items())), use_container_width=True)
