import sys
import logging
from PyQt5 import QtWidgets
from refactored_pump_control.main_window import MainWindow

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    app = QtWidgets.QApplication(sys.argv)
    
    # Optional: Set a clean visual style
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
