"""Cliente de Google Sheets usando una service account.

Para que funcione: la service account (definida en GOOGLE_SHEETS_CREDENTIALS_JSON)
debe tener el sheet compartido como editor. El ID del sheet va en SHEET_ID.
"""

import json
import os
from typing import Iterable

import gspread
from google.oauth2.service_account import Credentials

from .modelo import Transaccion


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class SheetsClient:
    def __init__(self):
        creds_json = os.environ["GOOGLE_SHEETS_CREDENTIALS_JSON"]
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        self.cliente = gspread.authorize(creds)
        self.spreadsheet = self.cliente.open_by_key(os.environ["SHEET_ID"])
        self._hoja = None

    @property
    def hoja(self):
        if self._hoja is None:
            try:
                self._hoja = self.spreadsheet.worksheet("transacciones")
            except gspread.WorksheetNotFound:
                self._hoja = self.spreadsheet.add_worksheet("transacciones", rows=1000, cols=20)
                self._hoja.append_row(Transaccion.encabezados())
        return self._hoja

    def ids_existentes(self) -> set:
        """Devuelve el conjunto de id_correo ya escritos al sheet, para evitar duplicados."""
        ids = self.hoja.col_values(1)
        return set(ids[1:])  # excluimos el encabezado

    def insertar(self, transacciones: Iterable[Transaccion]) -> int:
        filas = [t.to_row() for t in transacciones]
        if not filas:
            return 0
        self.hoja.append_rows(filas, value_input_option="USER_ENTERED")
        return len(filas)
