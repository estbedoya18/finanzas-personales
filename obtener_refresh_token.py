"""Obtiene un refresh token de Gmail.

Se corre UNA sola vez en tu computador local. Después copias el refresh token
a los secrets de GitHub y no lo vuelves a tocar (los refresh tokens de Google
no expiran si los usas regularmente).

Uso:
  1. Crea un OAuth Client ID tipo "Desktop app" en console.cloud.google.com
  2. Descarga el JSON y guárdalo como credentials.json en este directorio
  3. Habilita la Gmail API en el mismo proyecto
  4. Corre: python obtener_refresh_token.py
  5. Abre el link, autoriza, copia el refresh token que imprime
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def main():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    print("\n=== COPIA ESTOS VALORES A LOS SECRETS DE GITHUB ===\n")
    print(f"GMAIL_CLIENT_ID = {creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET = {creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN = {creds.refresh_token}")
    print()


if __name__ == "__main__":
    main()
