# Modelos OCR aprobados de SecretariatPro

- `spocr_v0.7_hybrid.joblib`: especialista del reloj, entrenado con LEDs
  reales y sintéticos derivados de ellos.
- `spscore_v0.2_digits.joblib`: especialista independiente de los marcadores;
  reconoce uno o dos dígitos y cubre las cifras `0–9`.

SP-OCR v0.7 conserva la anchura mostrada por el reloj: `02:23` permanece como
`02:23`. Los dos modelos se cargan de forma diferida después del OCR estable
`en_PP-OCRv4_mobile_rec`. Una compuerta conservadora decide si acepta la
corrección o conserva PaddleOCR. Si falta un artefacto o no puede cargarse, la
aplicación continúa automáticamente con PaddleOCR.

Los usuarios finales no entrenan ni instalan modelos. El entrenamiento,
benchmark y aprobación se realizan exclusivamente en **SecretariatPro OCR
Lab**.

## Instalador Windows

El ZIP del release contiene los dos especialistas `.joblib`. El reconocedor
base de PaddleOCR se prepara aparte con `python packaging/prepare_windows_ocr.py`
antes de compilar. Sus archivos se incluyen en
`models/en_PP-OCRv4_mobile_rec/`, y el worker instalado los usa directamente,
sin descargar modelos en el ordenador del realizador.

La especificación Windows incluye los metadatos de todas las dependencias de
`ocr-core` que PaddleX exige al crear el reconocedor, incluidos `python-bidi`,
`pypdfium2` y `opencv-contrib-python`. `python packaging/check_worker.py` comprueba
también una lectura real del ejecutable, no solo la importación de librerías
y la carga de los especialistas.
