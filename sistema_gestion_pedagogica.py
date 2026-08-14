# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN Y CONEXIÓN CON GOOGLE DRIVE API
# -----------------------------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/drive']

# ID de la carpeta compartida en tu Google Drive (sacado de la URL de Drive)
FOLDER_ID_RAIZ = "13nUnzgBGfy3H9Y3U0cFoYRob75IKp681"

@st.cache_resource
def obtener_servicio_drive():
    """Autentica contra la API de Google Drive usando Secrets de Streamlit o un archivo local."""
    creds = None
    
    # 1. Intentar cargar desde Secrets de Streamlit Cloud
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
    # 2. Intentar cargar desde archivo local 'credenciales.json'
    elif os.path.exists("credenciales.json"):
        creds = service_account.Credentials.from_service_account_file(
            "credenciales.json", scopes=SCOPES
        )
    
    if creds:
        return build('drive', 'v3', credentials=creds)
    return None

try:
    drive_service = obtener_servicio_drive()
except Exception as e:
    drive_service = None

# -----------------------------------------------------------------------------
# 2. CONFIGURACIÓN DE LA INTERFAZ Y SIDEBAR
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Sistema Pedagógico I.E.", page_icon="📚", layout="wide")

st.markdown("""
    <style>
    .main-title { color: #1E3A8A; font-size: 28px; font-weight: bold; }
    .stButton>button { background-color: #2563EB; color: white; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True)

st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=70)
st.sidebar.title("🏛️ I.E. Control Pedagógico")
rol = st.sidebar.selectbox("Seleccionar Rol de Usuario:", ["Docente", "Coordinador", "Director"])
st.sidebar.divider()
st.sidebar.caption("Sincronizado vía API con Google Drive 24/7")

# Advertencia de conexión
if not drive_service:
    st.error("⚠️ No se pudo conectar a Google Drive. Asegúrate de configurar las credenciales en 'Secrets' de Streamlit Cloud o tener el archivo 'credenciales.json'.")

# -----------------------------------------------------------------------------
# 3. VISTA DOCENTE (SUBIDA DE ARCHIVOS)
# -----------------------------------------------------------------------------
if rol == "Docente":
    st.markdown("<p class='main-title'>📤 Módulo de Carga - Docente</p>", unsafe_allow_html=True)
    st.caption("Los archivos se subirán directamente a la carpeta de Google Drive.")

    with st.form("form_docente"):
        st.subheader("Subir Documento Técnico-Pedagógico")

        docente_nombre = st.text_input("Nombre del Docente:", value="Prof. Juan Pérez")
        coordinacion = st.selectbox("Coordinación:", ["Matemática y Ciencias", "Letras y Comunicación", "Innovación y EPT", "Desarrollo Personal"])
        area_grado = st.text_input("Área / Grado:", value="Matemática 2° Sec")

        tipo_doc = st.selectbox("Tipo de Documento:", ["PROGRAMACION_ANUAL", "UNIDAD_DE_APRENDIZAJE", "SESION_DE_APRENDIZAJE", "INSTRUMENTO_EVALUACION"])
        periodo = st.selectbox("Periodo / Bimestre:", ["Bimestre I", "Bimestre II", "Bimestre III", "Bimestre IV"])

        archivo = st.file_uploader("Seleccionar Archivo (PDF, DOCX, XLSX):", type=["pdf", "docx", "xlsx"])
        notas = st.text_area("Comentarios para la coordinación:")

        subir = st.form_submit_button("🚀 Guardar y Subir a Google Drive")

        if subir:
            if archivo is not None:
                if drive_service:
                    with st.spinner("Subiendo archivo a Google Drive..."):
                        try:
                            # 1. Guardar archivo temporal en el servidor
                            ruta_temp = os.path.join(".", archivo.name)
                            with open(ruta_temp, "wb") as f:
                                f.write(archivo.getbuffer())

                            # 2. Renombrar el archivo de forma estandarizada
                            nombre_final = f"{periodo.replace(' ','_')}_{tipo_doc}_{docente_nombre.replace(' ','_')}_{archivo.name}"

                            # 3. Metadatos del archivo para la API de Drive
                            file_metadata = {
                                'name': nombre_final,
                                'parents': [FOLDER_ID_RAIZ]
                            }
                            media = MediaFileUpload(ruta_temp, resumable=True)

                            # 4. Ejecutar la carga vía API
                            file_uploaded = drive_service.files().create(
                                body=file_metadata, media_body=media, fields='id'
                            ).execute()

                            # 5. Limpiar archivo temporal local
                            if os.path.exists(ruta_temp):
                                os.remove(ruta_temp)

                            st.success(f"✅ ¡El archivo **{nombre_final}** fue subido exitosamente a Google Drive!")
                            st.info(f"🆔 ID del documento en Drive: `{file_uploaded.get('id')}`")

                        except Exception as e:
                            st.error(f"❌ Ocurrió un error al subir el archivo: {e}")
                else:
                    st.error("❌ No hay conexión activa con la API de Google Drive.")
            else:
                st.error("⚠️ Por favor selecciona un archivo antes de enviar.")

# -----------------------------------------------------------------------------
# 4. VISTA COORDINADOR (REVISIÓN DE ARCHIVOS)
# -----------------------------------------------------------------------------
elif rol == "Coordinador":
    st.markdown("<p class='main-title'>🔍 Revisión Pedagógica - Coordinación</p>", unsafe_allow_html=True)

    if drive_service:
        st.subheader("📂 Documentos Registrados en Google Drive")
        try:
            # Consultar archivos alojados en la carpeta raíz
            results = drive_service.files().list(
                q=f"'{FOLDER_ID_RAIZ}' in parents and trashed = false",
                fields="files(id, name, createdTime, mimeType)"
            ).execute()

            items = results.get('files', [])

            if not items:
                st.info("Aún no hay archivos subidos en la carpeta de Google Drive.")
            else:
                df_archivos = pd.DataFrame(items)
                st.dataframe(df_archivos[['name', 'createdTime', 'id']], use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error al consultar la carpeta de Google Drive: {e}")

    st.divider()
    st.subheader("✍️ Registrar Revisión u Observación")
    with st.form("form_revision"):
        doc_evaluar = st.text_input("Nombre o ID del documento a revisar:")
        accion = st.radio("Acción de Revisión:", ["APROBAR Y FIRMAR", "OBSERVAR Y SOLICITAR CORRECCIÓN"])
        comentario = st.text_area("Observación o Criterio a mejorar:")
        btn_revisar = st.form_submit_button("Guardar Revisión")

        if btn_revisar:
            st.success(f"Revisión registrada con éxito. Estado: {accion}")

# -----------------------------------------------------------------------------
# 5. VISTA DIRECTOR (DASHBOARD INSTITUCIONAL)
# -----------------------------------------------------------------------------
elif rol == "Director":
    st.markdown("<p class='main-title'>📊 Dashboard Institucional - Dirección</p>", unsafe_allow_html=True)
    st.caption("Visión general del estado del cumplimiento de la plana docente.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cumplimiento General", "87.5%", "🟢 Meta OK")
    col2.metric("Documentos Entregados", "342 / 390", "🟢 87.6%")
    col3.metric("Pendientes", "36", "-4 esta semana")
    col4.metric("Observados", "12", "🔴 Corregir", delta_color="inverse")

    st.divider()
    st.subheader("📋 Resumen por Coordinaciones")

    data_coordinaciones = {
        "Coordinación": ["Matemática y Ciencias", "Letras y Comunicación", "Innovación y EPT", "Desarrollo Personal"],
        "Docentes Asignados": [12, 15, 8, 7],
        "Entregados": [110, 125, 60, 47],
        "Pendientes": [4, 6, 2, 8],
        "Cumplimiento (%)": [96.4, 95.4, 96.7, 85.4]
    }
    st.dataframe(pd.DataFrame(data_coordinaciones), use_container_width=True)
