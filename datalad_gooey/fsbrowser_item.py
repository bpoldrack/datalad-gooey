from pathlib import Path
from typing import Dict

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QIcon,
)
from PySide6.QtWidgets import (
    QTreeWidgetItem,
)

from .fsbrowser_utils import _parse_dir

# package path
package_path = Path(__file__).resolve().parent


class FSBrowserItem(QTreeWidgetItem):
    PathObjRole = Qt.UserRole + 765

    def __init__(self, parent=None):
        # DO NOT USE DIRECTLY, GO THROUGH from_lsdir_result()
        super().__init__(
            parent,
            type=QTreeWidgetItem.UserType + 145,
        )
        self._child_lookup = None

    def __str__(self):
        return f'FSBrowserItem<{self.pathobj}>'

    @property
    def pathobj(self):
        p = self.data(0, FSBrowserItem.PathObjRole)
        if p is None:
            raise RuntimeError('TreeWidgetItem has no path set')
        return p

    @property
    def datalad_type(self):
        return self.data(1, Qt.EditRole)

    def data(self, column: int, role: int):
        if column == 0 and role in (Qt.DisplayRole, Qt.EditRole):
            # for now, we do not distinguish the two, maybe never will
            # but the default implementation also does this, so we match
            # behavior explicitly until we know better
            return self.pathobj.name
        # fall back on default implementation
        return super().data(column, role)

    def __getitem__(self, name: str):
        if self._child_lookup is None:
            self._child_lookup = {
                child.data(0, Qt.EditRole): child
                for child in self.children_()
            }
        return self._child_lookup.get(name)

    def _register_child(self, name, item):
        if self._child_lookup is None:
            self._child_lookup = {}
        self._child_lookup[name] = item

    def removeChild(self, item):
        super().removeChild(item)
        del self._child_lookup[item.pathobj.name]

    def children_(self):
        # get all pointers to children at once, other wise removing
        # one from the parent while the generator is running invalidates
        # the indices
        for c in [self.child(ci) for ci in range(self.childCount())]:
            yield c

    def update_data_from(self, other):
        # only meant to be called for items representing the same path
        assert self.pathobj == other.pathobj

        changed = False
        # take whatever the item has
        for col in range(1, other.columnCount()):
            # should they be different?
            #for role in (Qt.DisplayRole, Qt.EditRole):
            for role in (Qt.EditRole,):
                have = self.data(col, role)
                got = other.data(col, role)
                if have != got:
                    changed = True
                    self.setData(col, role, got)
        if changed:
            self.emitDataChanged()

    @classmethod
    def from_path(cls,
                  path: Path,
                  root: bool = True,
                  children: bool = True,
                  include_files: bool = False,
                  parent=None):
        gen = _parse_dir(
            path,
            depth=1 if children else 0,
            include_files=include_files
        )
        if root:
            root = cls.from_lsdir_result(next(gen), parent=parent)
        else:
            next(gen)
            root = parent
        children = [
            cls.from_lsdir_result(r, parent=root) for r in gen
        ]
        if children:
            root.addChildren(children)

        return root

    @classmethod
    def from_lsdir_result(cls, res: Dict, parent=None):
        item = FSBrowserItem(parent=parent)
        path = Path(res['path'])
        if hasattr(parent, '_register_child'):
            parent._register_child(path.name, item)
        item.setData(0, FSBrowserItem.PathObjRole, path)
        path_type = res['type']
        item.setData(1, Qt.EditRole, path_type)
        item._setItemIcons(res)
        if path_type in ('directory', 'dataset'):
            # show an expansion indiciator, even when we do not have
            # children in the item yet
            item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        return item

    def _setItemIcons(self, res):
        # Set 'type' icon
        item_type = res['type']
        if item_type != 'file':
            self.setIcon(0, self._getIcon(item_type))
        # Set other icon types: TODO

    def _getIcon(self, item_type):
        """Gets icon associated with item type"""
        icon_mapping = {
            'dataset': 'dataset-closed',
            'directory': 'directory-closed',
            'file': 'file',
            'file-annex': 'file-annex',
            'file-git': 'file-git',
            # opportunistic guess?
            'symlink': 'file-annex',
            'untracked': 'untracked',
            'clean': 'clean',
            'modified': 'modified',
            'deleted': 'untracked',
            'unknown': 'untracked',
            'added': 'modified',
        }
        icon_name = icon_mapping.get(item_type, None)
        if icon_name:
            return QIcon(str(
                package_path / 'resources' / 'icons' / f'{icon_name}.svg'))
        else:
            raise NotImplementedError(f"Unknown item type {item_type}")
