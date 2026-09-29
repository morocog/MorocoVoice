"""Unit tests for the Windows security-context probe.

These guard the regression that motivated the module: an application launched
from a Low-integrity folder starts normally, paints its HUD, reports healthy
threads and yet can neither publish a tray icon nor observe a single keystroke.
The classification must therefore be treated as a first-class failure that is
reported loudly, and the remediation hint must stay actionable.
"""

from pathlib import Path

from app.contracts import AppConfig
from app.platform.environment import (
    SecurityContext,
    describe_restriction,
    get_security_context,
    remediation_command,
)


def test_low_integrity_context_is_rejected():
    """A Low-integrity process cannot own a tray icon or receive input."""
    low = SecurityContext(
        integrity_rid=0x1000,
        integrity_name="Low",
        is_app_container=False,
        is_elevated=False,
    )
    assert low.is_low_integrity is True
    assert low.supports_tray_and_hooks is False


def test_medium_integrity_context_is_accepted():
    """Medium integrity is the normal, working case."""
    medium = SecurityContext(
        integrity_rid=0x2000,
        integrity_name="Medium",
        is_app_container=False,
        is_elevated=False,
    )
    assert medium.is_low_integrity is False
    assert medium.supports_tray_and_hooks is True


def test_app_container_is_rejected_even_at_medium():
    """An AppContainer is restricted regardless of its integrity level."""
    container = SecurityContext(
        integrity_rid=0x2000,
        integrity_name="Medium",
        is_app_container=True,
        is_elevated=False,
    )
    assert container.supports_tray_and_hooks is False


def test_failed_query_never_claims_a_working_environment():
    """If the token cannot be read we must not promise working tray/hotkeys."""
    unknown = SecurityContext(
        integrity_rid=0x2000,
        integrity_name="desconocido",
        is_app_container=False,
        is_elevated=False,
        query_failed=True,
    )
    assert unknown.supports_tray_and_hooks is False


def test_get_security_context_never_raises():
    """The startup probe must never be able to break application startup."""
    context = get_security_context()
    assert isinstance(context, SecurityContext)
    assert context.integrity_rid > 0
    assert isinstance(context.integrity_name, str)
    assert context.integrity_name


def test_remediation_command_is_runnable_and_quoted():
    """The hint must be a copy-pasteable icacls invocation."""
    command = remediation_command(r"C:\ruta con espacios\MorocoVoice")
    assert command.startswith("icacls ")
    # The path must be quoted so it survives spaces, and the whole tree relabelled.
    assert '"C:\\ruta con espacios\\MorocoVoice"' in command
    assert "/setintegritylevel Medium" in command
    assert "/T" in command


def test_describe_restriction_mentions_cause_and_fix():
    """The logged explanation must name the consequence and the exact fix."""
    low = SecurityContext(
        integrity_rid=0x1000,
        integrity_name="Low",
        is_app_container=False,
        is_elevated=False,
    )
    folder = Path("C:/Users/ejemplo/MorocoVoice")
    message = describe_restriction(low, folder)

    assert "ENTORNO RESTRINGIDO" in message
    assert "Low" in message
    assert "Shell_NotifyIcon" in message
    assert "icacls" in message
    assert "TROUBLESHOOTING" in message


def test_settings_hotkey_has_a_non_empty_default():
    """Regression: an empty Settings hotkey is exactly what locks users out.

    The tray icon used to be the only route into the Settings window. When a
    restricted environment rejects that icon, a keyboard route must exist.
    """
    assert AppConfig().hotkey_settings
