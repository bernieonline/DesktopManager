import sys
import time
import ctypes


def main():
    # --delay N: sleep N seconds before doing anything else.
    # Used by the startup Run key entry so the shop window launches
    # 30 s after logon, by which time Explorer's OLE drag-and-drop
    # infrastructure is fully stable.  Must be processed BEFORE any
    # Qt/COM initialisation so we don't hold resources while sleeping.
    if "--delay" in sys.argv:
        try:
            idx = sys.argv.index("--delay")
            seconds = int(sys.argv[idx + 1])
            time.sleep(seconds)
        except (IndexError, ValueError):
            pass  # malformed --delay flag, ignore

    if "--startup" in sys.argv:
        from src.core.startup_executor import StartupExecutor
        StartupExecutor().run()
    elif "--control-panel" in sys.argv:
        from PySide6.QtWidgets import QApplication
        from src.ui.control_panel import ControlPanel
        app = QApplication(sys.argv)
        app.setApplicationName("Desktop Workspaces")
        window = ControlPanel()
        window.show()
        sys.exit(app.exec())
    else:
        # OleInitialize must be called before QApplication on Windows.
        # PySide6 6.11.0 does not reliably call it before RegisterDragDrop,
        # which silently breaks OLE drag-and-drop (IDropTarget never fires).
        _ole_hr = ctypes.windll.ole32.OleInitialize(None)
        # S_OK=0 (first init), S_FALSE=1 (already init'd) — both are fine.
        # RPC_E_CHANGED_MODE (0x80010106) means another thread init'd COM in
        # MTA mode, which would break drag-and-drop.
        from src.utils.logger import get_logger as _gl
        _gl("main").debug(f"OleInitialize → 0x{_ole_hr & 0xFFFFFFFF:08X}")
        from PySide6.QtWidgets import QApplication
        from src.ui.shop_window import ShopWindow
        app = QApplication(sys.argv)
        app.setApplicationName("Desktop Workspaces")
        app.setQuitOnLastWindowClosed(False)
        app.setStyleSheet(
            "QToolTip { background-color: #2A2A2A; color: #E8E8E8;"
            "border: 1px solid #4FC3F7; padding: 4px 8px;"
            "border-radius: 3px; font-family: Segoe UI; font-size: 12px; }"
        )
        window = ShopWindow()
        window.show()
        # Delay validation so the window is visually rendered before the
        # progress bar appears.  Without this, fast local-path validation
        # completes before the first repaint and the bar never shows.
        from PySide6.QtCore import QTimer as _QT
        _QT.singleShot(500, window.start_validation)
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
