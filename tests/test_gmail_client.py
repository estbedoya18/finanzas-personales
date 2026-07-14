"""Pruebas del recorrido de etiquetas de Gmail sin acceso a la API real."""

import base64

from src.gmail_client import GmailClient


def _payload(texto: str, remitente: str, asunto: str, labels=None) -> dict:
    data = base64.urlsafe_b64encode(texto.encode("utf-8")).decode("ascii")
    return {
        "labelIds": labels or [],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": remitente},
                {"name": "Subject", "value": asunto},
            ],
            "body": {"data": data},
        },
    }


class _Request:
    def __init__(self, respuesta):
        self.respuesta = respuesta

    def execute(self):
        return self.respuesta


class _Labels:
    def list(self, userId):
        return _Request(
            {
                "labels": [
                    {"name": "Transacciones/Bancolombia", "id": "bancolombia"},
                    {"name": "Transacciones/Lulo", "id": "lulo"},
                    {"name": "Procesado/Finanzas", "id": "procesado"},
                ]
            }
        )


class _Messages:
    def __init__(self):
        self.listados = []

    def list(self, userId, labelIds, maxResults, pageToken=None):
        etiqueta = labelIds[0]
        self.listados.append(etiqueta)

        respuestas = {
            "bancolombia": {"messages": [{"id": "correo-1"}, {"id": "duplicado"}]},
            "lulo": {
                "messages": [
                    {"id": "duplicado"},
                    {"id": "procesado-1"},
                    {"id": "correo-2"},
                ]
            },
        }
        return _Request(respuestas[etiqueta])

    def get(self, userId, id, format):
        correos = {
            "correo-1": _payload(
                "Compra Bancolombia",
                "alertasynotificaciones@an.notificacionesbancolombia.com",
                "Alertas y Notificaciones",
            ),
            "duplicado": _payload(
                "Correo presente en dos etiquetas",
                "alertasynotificaciones@an.notificacionesbancolombia.com",
                "Alertas y Notificaciones",
            ),
            "procesado-1": _payload(
                "Ya procesado",
                "notificaciones@lulobank.com",
                "Pago PSE exitoso",
                labels=["procesado"],
            ),
            "correo-2": _payload(
                "Transferencia Lulo",
                "notificaciones@lulobank.com",
                "¡Envío con Bre-B exitoso!",
            ),
        }
        return _Request(correos[id])


class _Users:
    def __init__(self):
        self._labels = _Labels()
        self._messages = _Messages()

    def labels(self):
        return self._labels

    def messages(self):
        return self._messages


class _Service:
    def __init__(self):
        self._users = _Users()

    def users(self):
        return self._users


def test_listar_pendientes_recorre_etiquetas_hijas_y_deduplica():
    cliente = object.__new__(GmailClient)
    cliente.service = _Service()
    cliente._etiquetas_cache = None

    correos = list(cliente.listar_pendientes())

    assert [correo.id for correo in correos] == [
        "correo-1",
        "duplicado",
        "correo-2",
    ]
    assert cliente.service._users._messages.listados == [
        "bancolombia",
        "lulo",
    ]
