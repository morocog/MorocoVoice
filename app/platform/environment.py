"""Windows security-context detection for MorocoVoice.

WHY THIS MODULE EXISTS
----------------------
MorocoVoice depends on two capabilities that Windows grants only to processes
running at Medium integrity or above:

1. Publishing a notification-area (tray) icon  -> ``Shell_NotifyIcon(NIM_ADD)``
2. Receiving global keystrokes                 -> ``SetWindowsHookEx(WH_KEYBOARD_LL)``

When the process runs at **Low** integrity both are silently denied:

* ``Shell_NotifyIcon`` fails with ``ERROR_ACCESS_DENIED`` (WinError 5), so the
  tray icon never appears and the Settings/Exit menu becomes unreachable.
* ``SetWindowsHookEx`` *succeeds* and the listener thread stays alive, but UIPI
  stops any input destined for Medium-integrity processes from reaching it, so
  the hook observes **zero** events and every shortcut stays dead.

The process ends up at Low integrity when the executable it was launched from
carries a Low mandatory label. That happens in practice when a folder is
labelled by a sandboxing agent/EDE (workspace sandboxes commonly stamp
``Mandatory Label\\Low Mandatory Level:(OI)(CI)(NW)`` on their workspace root),
and the label is inherited by every file inside - including the virtual
environment's ``pythonw.exe``.

Result: the application looks perfectly healthy (threads alive, HUD painting)
while nothing works and nothing is logged. Detecting the context up front turns
that invisible failure into an actionable message.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

from app.logging_setup import get_logger

logger = get_logger("environment")

# --- Win32 constants -------------------------------------------------------
TOKEN_QUERY = 0x0008
TokenElevation = 20
TokenIntegrityLevel = 25
TokenIsAppContainer = 29

#: The mandatory-label SID's final sub-authority identifies the level.
_INTEGRITY_NAMES: dict[int, str] = {
    0x0000: "Untrusted",
    0x1000: "Low",
    0x2000: "Medium",
    0x2100: "Medium-Plus",
    0x3000: "High",
    0x4000: "System",
    0x5000: "Protected",
}

#: Integrity below this level cannot publish a tray icon or receive input.
_MINIMUM_USABLE_RID = 0x2000


@dataclass(frozen=True)
class SecurityContext:
    """Snapshot of the security context the process is running under."""

    integrity_rid: int
    integrity_name: str
    is_app_container: bool
    is_elevated: bool
    query_failed: bool = False

    @property
    def is_low_integrity(self) -> bool:
        return self.integrity_rid < _MINIMUM_USABLE_RID

    @property
    def supports_tray_and_hooks(self) -> bool:
        """Whether the shell tray and global input hooks can work at all."""
        return not self.query_failed and not self.is_app_container and not self.is_low_integrity


def _win32_apis() -> tuple[ctypes.CDLL, ctypes.CDLL] | None:
    """Bind the two DLLs with explicit signatures (SID pointers need them)."""
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        advapi32.OpenProcessToken.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        advapi32.OpenProcessToken.restype = wintypes.BOOL
        advapi32.GetTokenInformation.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        advapi32.GetTokenInformation.restype = wintypes.BOOL
        advapi32.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
        advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
        advapi32.GetSidSubAuthority.argtypes = [ctypes.c_void_p, wintypes.DWORD]
        advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
        return kernel32, advapi32
    except Exception as exc:  # pragma: no cover - non-Windows or exotic host
        logger.debug("Win32 token APIs unavailable: %s", exc)
        return None


class _SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class _TOKEN_MANDATORY_LABEL(ctypes.Structure):
    _fields_ = [("Label", _SID_AND_ATTRIBUTES)]


def _read_token(token_handle: wintypes.HANDLE, advapi32: ctypes.CDLL, info_class: int) -> int | None:
    """Read a DWORD-valued token information class, or None on failure."""
    value = wintypes.DWORD()
    returned = wintypes.DWORD()
    ok = advapi32.GetTokenInformation(
        token_handle, info_class, ctypes.byref(value), ctypes.sizeof(value), ctypes.byref(returned)
    )
    return value.value if ok else None


def _read_integrity_rid(token_handle: wintypes.HANDLE, advapi32: ctypes.CDLL) -> int | None:
    """Read the mandatory-label RID (0x1000 Low, 0x2000 Medium, ...)."""
    needed = wintypes.DWORD()
    advapi32.GetTokenInformation(
        token_handle, TokenIntegrityLevel, None, 0, ctypes.byref(needed)
    )
    if not needed.value:
        return None
    buffer = ctypes.create_string_buffer(needed.value)
    if not advapi32.GetTokenInformation(
        token_handle, TokenIntegrityLevel, buffer, needed.value, ctypes.byref(needed)
    ):
        return None
    label = ctypes.cast(buffer, ctypes.POINTER(_TOKEN_MANDATORY_LABEL)).contents
    sid = label.Label.Sid
    count = advapi32.GetSidSubAuthorityCount(sid)
    if not count:
        return None
    sub_authority = advapi32.GetSidSubAuthority(sid, count.contents.value - 1)
    return sub_authority.contents.value if sub_authority else None


def get_security_context() -> SecurityContext:
    """Inspect the current process token. Never raises."""
    unknown = SecurityContext(
        integrity_rid=_MINIMUM_USABLE_RID,
        integrity_name="desconocido",
        is_app_container=False,
        is_elevated=False,
        query_failed=True,
    )

    apis = _win32_apis()
    if apis is None:
        return unknown
    kernel32, advapi32 = apis

    token = wintypes.HANDLE()
    try:
        if not advapi32.OpenProcessToken(
            kernel32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(token)
        ):
            logger.debug("OpenProcessToken failed: %s", ctypes.get_last_error())
            return unknown

        rid = _read_integrity_rid(token, advapi32)
        if rid is None:
            return unknown

        return SecurityContext(
            integrity_rid=rid,
            integrity_name=_INTEGRITY_NAMES.get(rid, f"desconocido (0x{rid:04X})"),
            is_app_container=_read_token(token, advapi32, TokenIsAppContainer) == 1,
            is_elevated=_read_token(token, advapi32, TokenElevation) == 1,
        )
    except Exception as exc:  # pragma: no cover - defensive, must never break startup
        logger.debug("Could not determine security context: %s", exc)
        return unknown
    finally:
        if token:
            try:
                kernel32.CloseHandle(token)
            except Exception:
                pass


def remediation_command(target: Path | str) -> str:
    """The exact command that lifts a Low label back to Medium.

    The application folder is the usual culprit, but a labelled *parent* folder
    propagates down, so the command targets the folder the app lives in.
    """
    folder = Path(target).resolve()
    return f'icacls "{folder}" /setintegritylevel Medium /T /C'


def describe_restriction(context: SecurityContext, app_folder: Path | str) -> str:
    """Build the multi-line, actionable explanation logged at startup."""
    folder = Path(app_folder).resolve()
    reasons: list[str] = []
    if context.is_low_integrity:
        reasons.append(
            f"el proceso corre en integridad '{context.integrity_name}' "
            f"(0x{context.integrity_rid:04X}) en lugar de Medium"
        )
    if context.is_app_container:
        reasons.append("el proceso corre dentro de un AppContainer")

    lines = [
        "ENTORNO RESTRINGIDO DETECTADO: " + "; ".join(reasons) + ".",
        "Consecuencias: Windows denegara el icono de bandeja (Shell_NotifyIcon ->",
        "Acceso denegado) y el hook de teclado no recibira ninguna pulsacion, por",
        "lo que NINGUN atajo global funcionara aunque la aplicacion parezca sana.",
        "Causa habitual: la carpeta de la aplicacion (o una carpeta padre) tiene una",
        "etiqueta de integridad Low, habitualmente puesta por el sandbox de un agente",
        "de IA o por una herramienta de seguridad. Los ejecutables dentro de una",
        "carpeta Low se lanzan ELLOS MISMOS en Low, aunque los abras desde el Explorador.",
        f"Carpeta afectada: {folder}",
        "Solucion (PowerShell o CMD normal, y luego reiniciar MorocoVoice):",
        f"    {remediation_command(folder)}",
        "Si el problema reaparece tras usar un sandbox de agente, mueve MorocoVoice",
        "fuera de la carpeta que ese sandbox etiqueta. Ver docs/TROUBLESHOOTING.md.",
    ]
    return "\n".join(lines)
