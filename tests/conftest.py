from __future__ import annotations

import os

from qt_compat import configure_qt_environment


os.environ.setdefault("QT_API", "pyside6")
configure_qt_environment(offscreen=True)
