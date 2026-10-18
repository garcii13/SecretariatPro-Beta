"""Fail closed before publication unless acceptance evidence matches the binaries."""
import re


CHECKS = ("installed", "visual", "camera_ocr", "obs_multicam", "powerplays", "export_and_finish")
CLOUD_CHECKS = ("tenant_isolation", "roles", "invitations", "concurrent_theme_publication", "account_recovery", "backup_restore")


def validate_acceptance(evidence, version, builds, artifacts):
    if not isinstance(evidence, dict) or evidence.get("version") != version:
        raise ValueError("Falta aceptación para la versión que se va a publicar")
    if not evidence.get("reviewer") or not evidence.get("checked_at"):
        raise ValueError("La aceptación necesita responsable y fecha")
    cloud = evidence.get("cloud") or {}
    if any(cloud.get(key) is not True for key in CLOUD_CHECKS):
        raise ValueError("Faltan comprobaciones cloud reales")
    for platform, commit in builds.items():
        proof = (evidence.get("platforms") or {}).get(platform) or {}
        if proof.get("commit") != commit or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError(f"La aceptación de {platform} no corresponde al build")
        if any(proof.get(key) is not True for key in CHECKS):
            raise ValueError(f"Faltan recorridos instalados/OBS de {platform}")
        expected = artifacts.get(platform) or {}
        if not expected or proof.get("artifacts") != expected:
            raise ValueError(f"Los hashes aceptados no coinciden con {platform}")
    return True
