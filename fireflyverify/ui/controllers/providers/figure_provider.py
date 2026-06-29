"""FigureProvider — serves the controller's rendered matplotlib figures to QML.

QML requests ``image://figure/<kind>/<token>``; the token only forces a reload
when the figure changes. The actual QImage comes from a getter callback.
"""
from __future__ import annotations

from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


class FigureProvider(QQuickImageProvider):
    def __init__(self, getter):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._getter = getter            # callable(kind) -> QImage | None

    def requestImage(self, image_id, size, requested):
        kind = str(image_id).split("/")[0]
        img = None
        try:
            img = self._getter(kind)
        except Exception:
            img = None
        if img is None or img.isNull():
            img = QImage(8, 8, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(0)
        size.setWidth(img.width())
        size.setHeight(img.height())
        return img
