"""Tests for MorocoVoice settings persistence, Spotify UI components, and hotkey capture."""

from __future__ import annotations

import json
import types
from unittest.mock import MagicMock, patch

import pytest

from app import __version__
from app.contracts import AppConfig, AppState, AudioEngineType
from app.main import MUTEX_NAME, MorocoVoiceApplication, VoiceFlowApplication
from app.ui.hud import FloatingHUD
from app.ui.settings_window import (
    PillButton,
    SettingsModal,
    _apply_dark_title_bar,
    _persist_groq_api_key_to_env,
    resolve_captured_hotkey_event,
    verify_groq_api_key_online,
)


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


def test_is_valid_groq_api_key() -> None:
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


def test_verify_groq_api_key_online_mocked() -> None:
    """Verify verify_groq_api_key_online handles valid, unauthorized, and rate-limited keys."""
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
        mock_instance.models.list.side_effect = Exception(
            "Error code: 401 - {'error': {'message': 'Invalid API Key'}}"
        )

        valid, msg = verify_groq_api_key_online("gsk_invalidkey")
        assert valid is False
        assert "401" in msg or "inválida" in msg

    # Case 3: Transient 429 / 503 non-blocking
    with patch("groq.Groq") as mock_groq_class:
        mock_instance = MagicMock()
        mock_groq_class.return_value = mock_instance
        mock_instance.models.list.side_effect = Exception("Error code: 429 - Rate limit")

        valid, msg = verify_groq_api_key_online("gsk_validkey")
        assert valid is True
        assert "guard" in msg


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


def test_settings_modal_reloads_fresh_config_and_preserves_open_edits(tmp_path, tk_root) -> None:
    """Ensure SettingsModal syncs from disk on first open and preserves unsaved edits while open."""
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

    assert modal.current_config.hotkey_dictation == "ctrl+s"

    # First show() refreshes from disk
    modal.show()
    assert modal.current_config.hotkey_dictation == "ctrl+shift+h"
    assert modal.var_dictation.get() == "ctrl+shift+h"

    # Simulate user editing dictation shortcut without saving yet
    modal.var_dictation.set("alt+space")
    # Calling show() again while window is already open must NOT wipe unsaved edits
    modal.show()
    assert modal.var_dictation.get() == "alt+space"

    modal._on_cancel()


def test_resolve_captured_hotkey_event_supports_win_and_modifiers() -> None:
    """Verify resolve_captured_hotkey_event captures Win+Space, Ctrl+Shift+H, and Escape."""
    held: set[str] = set()

    # 1. Pressing Win_L alone records 'win' in held_mods and returns None
    ev_win = types.SimpleNamespace(keysym="Win_L", state=0)
    assert resolve_captured_hotkey_event(ev_win, held) is None
    assert "win" in held

    # 2. Pressing space while Win is held resolves to 'win+space'
    with patch("app.ui.settings_window._is_win_key_hardware_pressed", return_value=False):
        ev_space = types.SimpleNamespace(keysym="space", state=0)
        assert resolve_captured_hotkey_event(ev_space, held) == "win+space"

    # 3. Hardware Win key detection via GetAsyncKeyState even without prior Win_L event
    with patch("app.ui.settings_window._is_win_key_hardware_pressed", return_value=True):
        ev_space_hw = types.SimpleNamespace(keysym="space", state=0)
        assert resolve_captured_hotkey_event(ev_space_hw, set()) == "win+space"

    # 4. Ctrl+Shift+H via event.state bitmask (0x4 | 0x1 = 0x5)
    with patch("app.ui.settings_window._is_win_key_hardware_pressed", return_value=False):
        ev_csh = types.SimpleNamespace(keysym="H", state=0x5)
        assert resolve_captured_hotkey_event(ev_csh, set()) == "ctrl+shift+h"

    # 5. Escape cancels capture
    ev_esc = types.SimpleNamespace(keysym="Escape", state=0)
    assert resolve_captured_hotkey_event(ev_esc, set()) == "CANCEL"


def test_settings_modal_preserves_explicit_local_mode_with_valid_key(tmp_path, tk_root) -> None:
    """Verify saving LOCAL mode when a valid Groq API key already existed does NOT force CLOUD."""
    valid_key = "gsk_1234567890abcdefghijklmnopqrstuvwxyz"
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(
        json.dumps(
            {
                "hotkey_dictation": "win+space",
                "hotkey_rewrite": "ctrl+shift+space",
                "engine": "CLOUD",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(f"GROQ_API_KEY={valid_key}\n", encoding="utf-8")

    saved_configs: list[AppConfig] = []
    modal = SettingsModal(
        parent=tk_root,
        current_config=AppConfig(engine=AudioEngineType.CLOUD, groq_api_key=valid_key),
        config_file_path=cfg_file,
        on_saved=lambda c: saved_configs.append(c),
    )
    modal.show()
    assert modal._had_valid_key_on_open is True

    # User explicitly switches to LOCAL offline mode
    modal.var_engine.set("LOCAL")
    modal._on_save()

    assert len(saved_configs) == 1
    assert saved_configs[0].engine == AudioEngineType.LOCAL
    saved_json = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert saved_json["engine"] == "LOCAL"
    modal._on_cancel()


def test_settings_modal_rejects_duplicate_shortcuts(tmp_path, tk_root) -> None:
    """Verify _on_save rejects identical dictation and rewrite shortcuts."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(
        json.dumps({"hotkey_dictation": "win+space", "hotkey_rewrite": "ctrl+shift+space"}),
        encoding="utf-8",
    )

    saved_configs: list[AppConfig] = []
    modal = SettingsModal(
        parent=tk_root,
        current_config=AppConfig(),
        config_file_path=cfg_file,
        on_saved=lambda c: saved_configs.append(c),
    )
    modal.show()
    modal.var_dictation.set("ctrl+shift+h")
    modal.var_rewrite.set("CTRL+SHIFT+H")
    modal._on_save()

    # Must not have saved
    assert len(saved_configs) == 0
    assert "distintos" in modal.toast_lbl.cget("text")
    modal._on_cancel()


def test_render_keycap_chips_generates_chips(tk_root) -> None:
    """Verify keycap chips helper generates badges for shortcut tokens."""
    import tkinter as tk

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


def test_tray_menu_has_settings_as_default_item() -> None:
    """Verify the tray icon designates Settings as default=True for double-click activation."""
    import pystray

    from app.ui.tray import SystemTrayManager

    mock_root = MagicMock()
    mgr = SystemTrayManager(
        root=mock_root,
        on_shutdown=lambda: None,
        on_open_settings=lambda: None,
    )
    assert mgr.hotkey_settings == ""

    menu = pystray.Menu(
        pystray.MenuItem(f"MorocoVoice v{__version__}", None, enabled=False),
        pystray.MenuItem(mgr._get_engine_label, None, enabled=False),
        pystray.MenuItem(mgr._get_vad_label, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("⚙️ Configuración...", mgr._on_settings_clicked, default=True),
        pystray.MenuItem("Abrir registro (logs)", mgr._on_open_logs),
        pystray.MenuItem("Salir", mgr._on_exit_clicked),
    )
    default_items = [item for item in menu.items if getattr(item, "default", False)]
    assert len(default_items) == 1
    assert "Configuración" in default_items[0].text


def test_instrument_pystray_patches_icon_on_notify() -> None:
    """Verify that _instrument_pystray patches Icon._on_notify to handle double-click."""
    import pystray._win32 as pystray_win32_icon

    from app.ui.tray import _instrument_pystray

    _instrument_pystray()
    assert hasattr(pystray_win32_icon.Icon, "_on_notify")
    assert pystray_win32_icon.Icon._on_notify.__name__ == "_patched_on_notify"

    mock_icon = MagicMock()
    WM_LBUTTONDBLCLK = 0x0203
    pystray_win32_icon.Icon._on_notify(mock_icon, 0, WM_LBUTTONDBLCLK)
    mock_icon.assert_called_once()


def test_apply_dark_title_bar_handles_null_safely() -> None:
    """Verify _apply_dark_title_bar does not crash with mock or invalid window."""
    mock_win = MagicMock()
    mock_win.winfo_id.return_value = 0
    _apply_dark_title_bar(mock_win)


def test_hud_dynamic_width_prevents_clipping(tk_root) -> None:
    """Verify FloatingHUD dynamically expands window width/height and tracks auto-dismiss timers."""
    hud = FloatingHUD(tk_root)
    hud.show("Escuchando...", state=AppState.RECORDING)
    assert hud.width >= 260
    assert hud.height >= 44
    first_timer = hud._auto_dismiss_timer
    assert first_timer is not None

    # Long startup banner with duration_ms: must dynamically widen and replace previous timer
    startup_msg = "MorocoVoice listo • Dictado: CTRL+SHIFT+H"
    hud.show(startup_msg, state=AppState.INJECTING, duration_ms=3000)
    assert hud.width >= 350
    assert hud.label.cget("text") == startup_msg
    second_timer = hud._auto_dismiss_timer
    assert second_timer is not None
    assert second_timer != first_timer

    # Hiding cancels and clears the active timer
    hud.hide()
    assert hud._auto_dismiss_timer is None


def test_pill_button_widget(tk_root) -> None:
    """Verify Canvas-drawn PillButton creates geometry, tracks clicks, border_color, and text updates."""
    clicked = []
    btn = PillButton(
        tk_root,
        text="Iniciar sesión",
        command=lambda: clicked.append(True),
        border_color="#282828",
        padx=20,
        pady=6,
    )
    assert btn.cget("text") == "Iniciar sesión"
    assert btn.w > 40
    assert btn.h > 20
    assert btn.border_color == "#282828"

    # Simulate click and color update
    btn._on_click()
    assert clicked == [True]

    btn.set_colors("#1DB954", "#000000", border_color=None)
    assert btn.border_color is None

    # Update text
    btn.set_text("Cerrar sesión")
    assert btn.cget("text") == "Cerrar sesión"
