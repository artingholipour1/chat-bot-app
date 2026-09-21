import sys
import asyncio
import qasync
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QFontDatabase, QFont
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # بارگذاری فونت فارسی (اگر وجود دارد)
    try:
        font_id = QFontDatabase.addApplicationFont("resources/fonts/Vazirmatn-Regular.ttf")
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                app.setFont(QFont(families[0], 11))
    except:
        pass

    # آیکون برنامه
    icon_path = MainWindow.resource_path("resources/icon.ico")
    if icon_path and not icon_path.startswith(":"):
        app.setWindowIcon(QIcon(icon_path))

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow(app)
    window.show()

    with loop:
        loop.run_forever()