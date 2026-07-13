import sys
from accord.views.cli_click.commands import main
from accord.views.gui_kivy.main_view import MainView

def main_cli():
    """Punto de entrada para la CLI (accord)"""
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)

def main_gui():
    """Punto de entrada para la GUI (accord-gui)"""
    try:
        main_view = MainView()
        main_view.run()
    except SystemExit as e:
        sys.exit(e.code)
