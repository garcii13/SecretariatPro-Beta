"""Opt-in native regression: capture only our own overlapping test windows."""
import sys
import threading
import time


def diagnose():
    if sys.platform != "darwin":
        raise RuntimeError("La prueba visual nativa requiere macOS.")
    import AppKit
    import Foundation
    from window_capture import capture_window, WindowCaptureError

    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    app.finishLaunching()
    windows = []
    results = {}

    def pump():
        Foundation.NSRunLoop.currentRunLoop().runUntilDate_(
            Foundation.NSDate.dateWithTimeIntervalSinceNow_(0.05))

    def capture(window_id):
        outcome = []

        def run():
            try:
                outcome.append(capture_window(window_id)[0])
            except Exception as exc:
                outcome.append(exc)

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        deadline = time.monotonic() + 15
        while worker.is_alive() and time.monotonic() < deadline:
            pump()
        if not outcome:
            raise RuntimeError("La captura nativa de prueba no respondió.")
        if isinstance(outcome[0], Exception):
            raise outcome[0]
        return outcome[0]

    def check(name, index):
        frame = capture(int(windows[index].windowNumber()))
        if frame is None:
            raise AssertionError(f"{name}: captura vacía")
        height, width = frame.shape[:2]
        center = frame[height // 4:3 * height // 4, width // 4:3 * width // 4]
        mean = center.mean(axis=(0, 1))
        channel = 2 if index == 0 else 0
        if mean[channel] < 220 or sum(mean) - mean[channel] > 40:
            raise AssertionError(f"{name}: contiene píxeles ajenos a la ventana: {mean.tolist()}")
        results[name] = {"shape": list(frame.shape), "bgr": mean.tolist()}
        return width, height

    try:
        for color in ((1, 0, 0), (0, 0, 1)):
            window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                ((80, 100), (320, 180)), 0, 2, False)
            window.setReleasedWhenClosed_(False)
            window.setTitle_("SecretariatPro capture regression")
            window.setBackgroundColor_(AppKit.NSColor.colorWithRed_green_blue_alpha_(*color, 1))
            window.orderFrontRegardless()
            windows.append(window)
        # Allow WindowServer to register both windows before enumerating them.
        for _ in range(10):
            pump()
        original = check("covered", 0)
        check("covering_same_title", 1)
        windows[0].setFrameOrigin_((160, 160))
        pump()
        check("moved", 0)
        windows[0].setContentSize_((240, 120))
        pump()
        resized = check("resized", 0)
        if resized != (round(original[0] * 0.75), round(original[1] * 2 / 3)):
            raise AssertionError(f"Dimensiones obsoletas tras redimensionar: {original} -> {resized}")
        closed_id = int(windows[0].windowNumber())
        windows[0].close()
        for _ in range(10):
            pump()
        try:
            capture(closed_id)
        except WindowCaptureError:
            results["closed_rejected"] = True
        else:
            raise AssertionError("Una ventana cerrada no debe devolver otra imagen.")
        try:
            capture(2147483646)
        except WindowCaptureError:
            results["missing_rejected"] = True
        else:
            raise AssertionError("Una ventana inexistente no debe devolver otra imagen.")
        return {"type": "window_capture_ok", "checks": results}
    finally:
        for window in windows:
            window.close()
