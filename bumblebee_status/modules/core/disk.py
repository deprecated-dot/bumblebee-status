# pylint: disable=C0111,R0903

"""Shows free diskspace, total diskspace and the percentage of free disk space.

Parameters:
    * disk.warning: Warning threshold in % of disk space (defaults to 80%)
    * disk.critical: Critical threshold in % of disk space (defaults to 90%)
    * disk.path: Comma separated list of paths (defaults to /)
    * disk.open: Which application / file manager to use for opening the selected directory (defaults to xdg-open) 
    * disk.format: Format string, tags {path}, {used}, {left}, {size} and {percent} (defaults to '({path}) {used}/{size} ({percent:05.02f}%)')
    * disk.system: Unit system to use - SI (KB, MB, ...) or IEC (KiB, MiB, ...) (defaults to 'IEC')
"""

import os

import core.module
import core.widget
import core.input

import util.format


class Module(core.module.Module):

    def __init__(self, config, theme):
        super().__init__(config, theme, core.widget.Widget(self.diskspace))

        self._indexPath = 0
        self._path = tuple(
                filter( len, util.format.aslist(self.parameter("path", "/")) )
        )

        self._format = self.parameter("format", "({path}) {used}/{size} ({percent:05.02f}%)")
        p = self.parameter('format', '{path}')

        self._system = self.parameter("system", "IEC")

        self._used = 0
        self._left = 0
        self._size = 0
        self._percent = 0

        core.input.register(
            self,
            button=core.input.LEFT_MOUSE,
            cmd="openDir",
        )

        core.input.register(
            self,
            button=core.input.WHEEL_UP,
            cmd="nextPath",
        )

        core.input.register(
            self,
            button=core.input.WHEEL_DOWN,
            cmd="prevPath",
        )

    def diskspace(self, widget):
        used_str = util.format.byte(self._used, sys=self._system)
        size_str = util.format.byte(self._size, sys=self._system)
        left_str = util.format.byte(self._left, sys=self._system)
        percent_str = self._percent

        return self._format.format(
            path=self._path[self._indexPath],
            used=used_str,
            left=left_str,
            size=size_str,
            percent=percent_str,
        )

    def update(self):
        st = os.statvfs(self._path[self._indexPath])
        self._size = st.f_blocks * st.f_frsize
        self._left = st.f_bavail * st.f_frsize
        self._used = self._size - self._left
        self._percent = 100.0 * self._used / self._size

    def state(self, widget):
        return self.threshold_state(self._percent, 80, 90)

    def openDir(self, event):
        util.cli.execute(
                "{} {}".format( self.parameter("open", "xdg-open"),
                                self._path[self._indexPath] )
        )

    def nextPath(self, event):
        self._indexPath += 1

        if self._indexPath >= len(self._path):
            self._indexPath = 0

    def prevPath(self, event):
        self._indexPath -= 1

        if self._indexPath < 0:
            self._indexPath = len(self._path) - 1

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
