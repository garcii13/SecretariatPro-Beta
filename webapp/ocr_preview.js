/* A preview has one source and one request. Stale responses never replace it. */
window.OCRPreviewController = class OCRPreviewController {
  constructor({ image, empty, status, onReady, onReset, onError }) {
    Object.assign(this, { image, empty, status, onReady, onReset, onError });
    this.generation = 0;
    this.objectURL = null;
    this.request = null;
  }

  reset(message = "Selecciona una fuente OCR") {
    this.generation += 1;
    this.request?.abort();
    this.request = null;
    this.image.classList.remove("is-visible");
    this.image.removeAttribute("src");
    if (this.objectURL) URL.revokeObjectURL(this.objectURL);
    this.objectURL = null;
    this.empty.hidden = false;
    this.status.textContent = message;
    this.onReset?.();
  }

  async load(url, label) {
    this.reset("Capturando preview…");
    const generation = this.generation;
    const request = new AbortController();
    this.request = request;
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; request.abort(); }, 45000);
    try {
      const response = await fetch(url, { signal: request.signal, cache: "no-store" });
      if (!response.ok) {
        let detail = `No se pudo obtener el preview OCR (HTTP ${response.status}).`;
        try {
          const error = await response.json();
          if (typeof error.detail === "string") detail = error.detail;
        } catch (_) { /* Keep the HTTP status if the response is not JSON. */ }
        throw new Error(detail);
      }
      const blob = await response.blob();
      if (generation !== this.generation) return false;
      if (!blob.type.startsWith("image/")) throw new Error("La fuente no ha devuelto una imagen válida.");
      this.objectURL = URL.createObjectURL(blob);
      this.image.src = this.objectURL;
      await this.image.decode();
      if (generation !== this.generation) return false;
      this.empty.hidden = true;
      this.image.classList.add("is-visible");
      this.status.textContent = label || "Fuente OCR";
      this.onReady?.();
      return true;
    } catch (error) {
      if (generation !== this.generation) return false;
      const message = timedOut ? "La fuente no respondió a tiempo. Comprueba sus permisos y conexión e inténtalo de nuevo." : error.message;
      this.reset(message);
      this.onError?.(message);
      return false;
    } finally {
      clearTimeout(timer);
      if (this.request === request) this.request = null;
    }
  }
};
