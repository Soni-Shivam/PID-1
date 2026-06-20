"""List model + filter/sort proxy for the application menu.

AppListModel exposes the enumerated apps with custom roles; AppFilterProxy does
case-insensitive search over Name+Comment, category filtering, and order-by
(name / most used / recently used). Icons resolve lazily and are cached so the
grid paints cheaply.
"""
from __future__ import annotations

from core.qt_compat import Qt, QtCore, QtGui
from apps import usage
from apps.desktop_entries import AppEntry, list_apps

APP_ID = Qt.UserRole + 1
NAME = Qt.UserRole + 2
COMMENT = Qt.UserRole + 3
CATEGORIES = Qt.UserRole + 4
COUNT = Qt.UserRole + 5
LAST_TS = Qt.UserRole + 6
ENTRY = Qt.UserRole + 7

_GENERIC_ICON = "application-x-executable"


def fuzzy_match(query: str, text: str) -> bool:
    """True if every query char appears in *text* in order (subsequence match).

    Typo/gap tolerant: 'gimp' matches 'GNU Image Manipulation Program' via
    initials, 'clc' matches 'Calculator'. Substring is the strongest case and
    is naturally included. Empty query matches everything.
    """
    if not query:
        return True
    it = iter(text)
    return all(ch in it for ch in query)


class AppListModel(QtCore.QAbstractListModel):
    """Flat model over the installed-app catalogue."""

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._apps: list[AppEntry] = []
        self._usage: dict = {}
        self._icon_cache: dict[str, QtGui.QIcon] = {}
        self.reload()

    def reload(self) -> None:
        """Re-read the catalogue and usage stats (used for live updates)."""
        self.beginResetModel()
        self._apps = list_apps()
        self._usage = usage.stats()
        self._icon_cache.clear()
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._apps)

    def _icon(self, app: AppEntry) -> QtGui.QIcon:
        cached = self._icon_cache.get(app.app_id)
        if cached is not None:
            return cached
        icon = QtGui.QIcon.fromTheme(app.icon) if app.icon else QtGui.QIcon()
        if icon.isNull():
            icon = QtGui.QIcon.fromTheme(_GENERIC_ICON)
        self._icon_cache[app.app_id] = icon
        return icon

    def data(self, index: QtCore.QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        app = self._apps[index.row()]
        if role in (Qt.DisplayRole, NAME):
            return app.name
        if role == Qt.DecorationRole:
            return self._icon(app)
        if role in (Qt.ToolTipRole, COMMENT):
            return app.comment
        if role == APP_ID:
            return app.app_id
        if role == CATEGORIES:
            return list(app.categories)
        if role == ENTRY:
            return app
        rec = self._usage.get(app.app_id) or {}
        if role == COUNT:
            return int(rec.get("count", 0))
        if role == LAST_TS:
            return float(rec.get("last_ts", 0.0))
        return None


class AppFilterProxy(QtCore.QSortFilterProxyModel):
    """Search + category filter with switchable order-by."""

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._query = ""
        self._category = ""
        self.setDynamicSortFilter(True)
        self.set_order("name")

    def set_query(self, text: str) -> None:
        self._query = (text or "").strip().lower()
        self.invalidateFilter()

    def set_category(self, category: str) -> None:
        self._category = "" if category in ("", "All") else category
        self.invalidateFilter()

    def set_order(self, mode: str) -> None:
        if mode == "most_used":
            self.setSortRole(COUNT)
            self.sort(0, Qt.DescendingOrder)
        elif mode == "recent":
            self.setSortRole(LAST_TS)
            self.sort(0, Qt.DescendingOrder)
        else:
            self.setSortRole(NAME)
            self.sort(0, Qt.AscendingOrder)

    def filterAcceptsRow(self, row, parent):  # noqa: N802
        src = self.sourceModel()
        idx = src.index(row, 0, parent)
        if self._query:
            name = (src.data(idx, NAME) or "").lower()
            comment = (src.data(idx, COMMENT) or "").lower()
            # Substring on either field, or a fuzzy subsequence match on the
            # name (so partial/initials/typos still find the app).
            if (self._query not in name and self._query not in comment
                    and not fuzzy_match(self._query, name)):
                return False
        if self._category:
            if self._category not in (src.data(idx, CATEGORIES) or []):
                return False
        return True

    def lessThan(self, left, right):  # noqa: N802
        role = self.sortRole()
        lv = self.sourceModel().data(left, role)
        rv = self.sourceModel().data(right, role)
        if isinstance(lv, str) and isinstance(rv, str):
            return lv.lower() < rv.lower()
        return (lv or 0) < (rv or 0)
