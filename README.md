# SecretariatPro · beta

SecretariatPro reúne la aplicación de realización, el Manager, el overlay para emisión y el worker OCR. La beta genera instaladores para Windows x64 y macOS Apple Silicon/Intel.

## Emisión y operativa

- **Directo → Comprobación previa** distingue bloqueos reales de avisos. OBS, el monitor de Programa y la tablet son opcionales; el panel puede cerrarse y recuperarse.
- **Directo → Copiar enlace para emisión** copia `http://127.0.0.1:8765/overlay.html` mediante el portapapeles nativo. Debe añadirse como fuente de navegador de 1920 × 1080 en OBS u otro programa de emisión.
- **Realización → Cola de gráficos** permite preparar, previsualizar y lanzar gráficos en orden sin modificar la salida durante la preparación.
- **Configuración → Acceso remoto** crea un QR de un solo uso para una sesión de tablet revocable.

## Cuentas e identidad visual

- El Manager puede invitar por correo a realizadores o gestores aunque todavía no tengan cuenta. El enlace abre [Mi cuenta](https://secretariatproapp.com/cuenta) en la web oficial para crear la contraseña y completar los datos.
- El Manager publica tamaños y tipografías independientes por elemento. El ámbito puede ser general o de competición cuando el plan lo permite.
- Los realizadores reciben la identidad publicada y no pueden editarla.
- En la primera apertura se utiliza el idioma del sistema si está disponible (`es`, `en`, `sv`, `cs`, `fi`, `de`); inglés es el idioma de respaldo.

## Desarrollo

Requiere Python 3.12. Instalar `requirements.txt` y `requirements-test.txt`; en macOS aplicar también `constraints-macos.txt`.

```bash
python -m unittest discover -s tests
node --check script.js
node --check webapp/app.js
node --check manager_app/app.js
```

La web oficial vive en `website/`. Es un proyecto Astro estático bilingüe con el portal de cuenta integrado:

```bash
cd website
npm ci
npm audit --audit-level=high
npm run build
```

`public_config.json` contiene solamente la URL, la clave publicable de Supabase y la URL pública del portal. Los secretos, sesiones, ajustes OBS, datos locales, modelos binarios y resultados de compilación están excluidos del repositorio.

## Modelos OCR e instaladores

La aplicación usa SP-OCR v0.7 y SP-SCORE v0.2. Los binarios verificados viven en el release privado `ocr-models-v0.7-v0.2`; GitHub Actions los descarga, comprueba sus SHA-256 contra `models/MANIFEST_SP_OCR.json` y después compila.

El workflow **Beta installers** produce `.exe` para Windows y `.dmg` para ambas arquitecturas de macOS, además de SHA-256 y dependencias resueltas. **Website** compila la web Astro y publica una copia estática verificable. Los instaladores de beta todavía no tienen firma de editor ni notarización. Consultar [la auditoría](docs/BETA_AUDIT.md) y el [protocolo de aceptación](docs/BETA_VALIDATION.md) antes de distribuirlos.
