# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_ID_RAIZ = "13nUnzgBGfy3H9Y3U0cFoYRob75IKp681"

@st.cache_resource
def obtener_servicio_drive():
    creds = None
    # Intenta leer credenciales en formato string/json o diccionario desde Secrets
    if "gcp_service_account" in st.secrets:
        try:
            secret_data = st.secrets["gcp_service_account"]
            if isinstance(secret_data, str):
                creds_dict = json.loads(secret_data)
            else:
                creds_dict = dict(secret_data)
                if "private_key" in creds_dict:
                    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            creds = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=SCOPES
            )
        except Exception as e:
            st.error(f"Error al procesar las credenciales en Secrets: {e}")
            return None
            
    elif os.path.exists("credenciales.json"):
        creds = service_account.Credentials.from_service_account_file(
            "credenciales.json", scopes=SCOPES
        )
    
    if creds:
        return build('drive', 'v3', credentials=creds)
    return None
