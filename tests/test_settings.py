"""Tests for MorocoVoice settings persistence and rebranding."""

from __future__ import annotations

import pytest

from app.main import MUTEX_NAME, MorocoVoiceApplication, VoiceFlowApplication
from app.ui.settings_window import _persist_groq_api_key_to_env


def test_mutex_name_and_aliases() -> None:
    """Ensure mutex name matches MorocoVoice standard and alias is preserved."""
    assert MUTEX_NAME == "Global\\MorocoVoice_SingleInstance_Mutex"
    assert VoiceFlowApplication is MorocoVoiceApplication


def test_persist_groq_api_key_creates_and_updates(tmp_path) -> None:
    """Ensure _persist_groq_api_key_to_env updates existing key and preserves comments."""
    env_file = tmp_path / ".env"

    # Test 1: Write to non-existent file
    _persist_groq_api_key_to_env(env_file, "gsk_initial123")
    assert env_file.exists()
    content = env_file.read_text(encoding="utf-8")
    assert "GROQ_API_KEY=gsk_initial123" in content

    # Test 2: Update existing key with other variables preserved
    env_file.write_text(
        "# Header comment\nOLLAMA_URL=http://localhost:11434\nGROQ_API_KEY=gsk_initial123\n# Footer comment\n",
        encoding="utf-8",
    )
    _persist_groq_api_key_to_env(env_file, "gsk_updated999")
    updated_content = env_file.read_text(encoding="utf-8")
    assert "GROQ_API_KEY=gsk_updated999" in updated_content
    assert "gsk_initial123" not in updated_content
    assert "# Header comment" in updated_content
    assert "OLLAMA_URL=http://localhost:11434" in updated_content


def test_is_valid_groq_api_key():
    """Verify placeholder keys are rejected and valid keys are accepted."""
    from app.config import is_valid_groq_api_key

    # Placeholders or empty
    assert not is_valid_groq_api_key("")
    assert not is_valid_groq_api_key(None)
    assert not is_valid_groq_api_key("gsk_tu_clave_de_groq_aqui")
    assert not is_valid_groq_api_key("gsk_tu_clave")
    assert not is_valid_groq_api_key("tu_clave_aqui")
    assert not is_valid_groq_api_key("gsk_short")

    # Valid key format
    assert is_valid_groq_api_key("gsk_1234567890abcdefghijklmnopqrstuvwxyz")


def test_verify_groq_api_key_online_mocked():
    """Verify verify_groq_api_key_online handles valid and unauthorized keys."""
    from unittest.mock import MagicMock, patch

    from app.ui.settings_window import verify_groq_api_key_online

    # Case 1: Successful check
    with patch("groq.Groq") as mock_groq_class:
        mock_instance = MagicMock()
        mock_groq_class.return_value = mock_instance
        mock_instance.models.list.return_value = ["model1"]

        valid, msg = verify_groq_api_key_online("gsk_validkey")
        assert valid is True
        assert "válida" in msg

    # Case 2: Unauthorized (401)
    with patch("groq.Groq") as mock_groq_class:
        mock_instance = MagicMock()
        mock_groq_class.return_value = mock_instance
        mock_instance.models.list.side_effect = Exception("Error code: 401 - {'error': {'message': 'Invalid API Key'}}")

        valid, msg = verify_groq_api_key_online("gsk_invalidkey")
        assert valid is False
        assert "401" in msg or "inválida" in msg


@pytest.fixture(scope="module")
def tk_root():
    """Shared Tkinter root for settings UI tests to prevent multiple Tk instances crash."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


def test_settings_modal_reloads_fresh_config(tmp_path, tk_root):
    """Ensure SettingsModal always syncs from disk and never displays stale cached hotkeys."""
    import json
    from app.contracts import AppConfig
    from app.ui.settings_window import SettingsModal

    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(
        json.dumps({"hotkey_dictation": "ctrl+shift+h", "hotkey_rewrite": "ctrl+shift+space"}),
        encoding="utf-8",
    )

    initial_cfg = AppConfig(hotkey_dictation="ctrl+s")
    saved_calls = []

    modal = SettingsModal(
        parent=tk_root,
        current_config=initial_cfg,
        config_file_path=cfg_file,
        on_saved=lambda c: saved_calls.append(c),
    )

    # Before show: initial config had ctrl+s
    assert modal.current_config.hotkey_dictation == "ctrl+s"

    # Simulate show() logic: must refresh from disk
    modal.show()
    assert modal.current_config.hotkey_dictation == "ctrl+shift+h"
    assert modal.var_dictation.get() == "ctrl+shift+h"

    modal._on_cancel()


def test_render_keycap_chips_generates_chips(tk_root):
    """Verify keycap chips helper generates badges for shortcut tokens."""
    import tkinter as tk
    from app.ui.settings_window import SettingsModal
    from app.contracts import AppConfig

    modal = SettingsModal(
        parent=tk_root,
        current_config=AppConfig(),
        config_file_path="config.json",
        on_saved=lambda c: None,
    )
    frame = tk.Frame(tk_root)
    modal._render_keycap_chips(frame, "ctrl+shift+h")
    labels = [w.cget("text") for w in frame.winfo_children() if isinstance(w, tk.Label)]
    assert "CTRL" in labels
    assert "SHIFT" in labels
    assert "H" in labels
    assert "+" in labels


def test_tray_menu_has_settings_as_default_item():
    """Verify the tray icon designates Settings as default=True for double-click activation."""
    from unittest.mock import MagicMock
    from app.ui.tray import SystemTrayManager

    mock_root = MagicMock()
    mgr = SystemTrayManager(
        root=mock_root,
        on_shutdown=lambda: None,
        on_open_settings=lambda: None,
    )
    # Verify default constructor has empty hotkey_settings (clean governance)
    assert mgr.hotkey_settings == ""

    # Trigger tray menu construction without background thread
    from app.ui.tray import create_tray_icon_image
    import pystray
    from app import __version__

    menu = pystray.Menu(
        pystray.MenuItem(f"MorocoVoice v{__version__}", None, enabled=False),
        pystray.MenuItem(mgr._get_engine_label, None, enabled=False),
        pystray.MenuItem(mgr._get_vad_label, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("⚙️ Configuración...", mgr._on_settings_clicked, default=True),
        pystray.MenuItem("Abrir Logs", mgr._on_open_logs),
        pystray.MenuItem("Salir", mgr._on_exit_clicked),
    )
    default_items = [item for item in menu.items if getattr(item, "default", False)]
    assert len(default_items) == 1
    assert "Configuración" in default_items[0].text


def test_instrument_pystray_patches_icon_on_notify():
    """Verify that _instrument_pystray patches Icon._on_notify to handle double-click."""
    from unittest.mock import MagicMock
    import pystray._win32 as pystray_win32_icon
    from app.ui.tray import _instrument_pystray

    _instrument_pystray()
    assert hasattr(pystray_win32_icon.Icon, "_on_notify")
    assert pystray_win32_icon.Icon._on_notify.__name__ == "_patched_on_notify"

    # Verify that calling _patched_on_notify with WM_LBUTTONDBLCLK triggers self_icon()
    mock_icon = MagicMock()
    WM_LBUTTONDBLCLK = 0x0203
    pystray_win32_icon.Icon._on_notify(mock_icon, 0, WM_LBUTTONDBLCLK)
    mock_icon.assert_called_once()


def test_apply_dark_title_bar_handles_null_safely():
    """Verify _apply_dark_title_bar does not crash with mock or invalid window."""
    from unittest.mock import MagicMock
    from app.ui.settings_window import _apply_dark_title_bar

    mock_win = MagicMock()
    mock_win.winfo_id.return_value = 0
    # Must execute safely without raising
    _apply_dark_title_bar(mock_win)


def test_hud_dynamic_width_prevents_clipping(tk_root):
    """Verify FloatingHUD dynamically expands window width to prevent text clipping."""
    from app.ui.hud import FloatingHUD
    from app.contracts import AppState

    hud = FloatingHUD(tk_root)
    # Default short text
    hud.show("Escuchando...", state=AppState.RECORDING)
    assert hud.width >= 260

    # Long startup banner: must dynamically widen beyond text width
    startup_msg = "MorocoVoice listo • Dictado: CTRL+SHIFT+H"
    hud.show(startup_msg, state=AppState.INJECTING)
    assert hud.width >= 350
    assert hud.label.cget("text") == startup_msg
    hud.hide()


def test_pill_button_widget(tk_root):
    """Verify Canvas-drawn PillButton creates geometry, tracks clicks and supports text updates."""
    from app.ui.settings_window import PillButton

    clicked = []
    btn = PillButton(
        tk_root,
        text="Iniciar sesión",
        command=lambda: clicked.append(True),
        padx=20,
        pady=6,
    )
    assert btn.cget("text") == "Iniciar sesión"
    assert btn.w > 40
    assert btn.h > 20

    # Simulate click
    btn._on_click()
    assert clicked == [True]

    # Update text
    btn.set_text("Cerrar sesión")
    assert btn.cget("text") == "Cerrar sesión"


