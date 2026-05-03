import sys
import ctypes


def main():
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
        ctypes.windll.ole32.OleInitialize(None)
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
        window.start_validation()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
