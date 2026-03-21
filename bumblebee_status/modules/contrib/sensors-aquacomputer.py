# -*- coding: UTF-8 -*-

"""Unified Aquacomputer HID sensor module for bumblebee-status.

Displays coolant loop telemetry from Aquacomputer High Flow NEXT,
D5 NEXT pump, and Leakshield devices. Device names are resolved
dynamically from sysfs using stable USB product IDs, eliminating
the need to update module configs after USB bus resets or reboots.

Widgets (in order):
    - Coolant temp in  (D5 NEXT temp1)        type: water-in
    - Coolant temp out (High Flow NEXT temp1)  type: water-out
    - Flow rate        (High Flow NEXT fan1)   type: water-in
    - Pump speed       (D5 NEXT fan1)          type: fan
    - Water quality    (High Flow NEXT fan2)   type: fan
    - Conductivity     (High Flow NEXT fan3)   type: fan
    - Loop pressure    (Leakshield fan1)       type: fan
"""

import os
import glob

import core.module
import core.widget
import util.cli
import util.format

# Stable USB product IDs for Aquacomputer devices
_AQUACOMPUTER_DEVICES = {
    "highflownext": "f012",
    "d5next":       "f00e",
    "leakshield":   "f014",
}


def _resolve_chip_name(chip_prefix, usb_product_id):
    """Resolve the volatile hwmon chip name using stable USB product ID.

    Walks /sys/class/hwmon looking for a hwmon device whose name starts
    with chip_prefix and whose USB ancestor exposes the given product ID.
    Returns the full chip name (e.g. 'highflownext-hid-3-80') or None.
    """
    for hwmon_path in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            name_file = os.path.join(hwmon_path, "name")
            name = open(name_file).read().strip()
            if not name.startswith(chip_prefix):
                continue
            # Walk up the sysfs device tree looking for idProduct
            device_path = os.path.realpath(hwmon_path)
            while device_path and device_path != "/":
                id_path = os.path.join(device_path, "idProduct")
                if os.path.exists(id_path):
                    found_pid = open(id_path).read().strip().lower()
                    if found_pid == usb_product_id.lower():
                        return name
                    break  # found idProduct but wrong device, stop walking
                device_path = os.path.dirname(device_path)
        except Exception:
            continue
    return None


def _read_sensor(chip_name, field):
    """Read a single sensor field value from sysfs hwmon directly.

    More efficient than shelling out to 'sensors -u' for every widget.
    Returns float or None on error.
    """
    for hwmon_path in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            name = open(os.path.join(hwmon_path, "name")).read().strip()
            if name != chip_name:
                continue
            value_path = os.path.join(hwmon_path, field)
            if os.path.exists(value_path):
                return float(open(value_path).read().strip())
        except Exception:
            continue
    return None


class Module(core.module.Module):
    def __init__(self, config, theme):
        super().__init__(config, theme, [])
        self._chips = {}
        self._resolve_chips()
        self._create_widgets()

    def _resolve_chips(self):
        """Resolve all three Aquacomputer device names from sysfs."""
        for chip_prefix, usb_pid in _AQUACOMPUTER_DEVICES.items():
            name = _resolve_chip_name(chip_prefix, usb_pid)
            self._chips[chip_prefix] = name

    def update(self):
        # Re-resolve in case of USB bus reset between updates
        self._resolve_chips()
        for widget in self.widgets():
            self._update_widget(widget)

    def state(self, widget):
        return [widget.get("type", "")]

    def _create_widgets(self):
        # Pump speed — D5 NEXT fan1 (RPM)
        w = self.add_widget(full_text=self._text_pump)
        w.set("type", "pump-rpm")
        w.set("chip", "d5next")
        w.set("field", "fan1_input")

        # Coolant temp in — D5 NEXT temp1
        w = self.add_widget(full_text=self._text_temp_in)
        w.set("type", "water-in")
        w.set("chip", "d5next")
        w.set("field", "temp1_input")

        # Coolant temp out — High Flow NEXT temp1
        w = self.add_widget(full_text=self._text_temp_out)
        w.set("type", "water-out")
        w.set("chip", "highflownext")
        w.set("field", "temp1_input")

        # Loop pressure — Leakshield fan1 (μbar/1000 = mbar)
        w = self.add_widget(full_text=self._text_pressure)
        w.set("type", "loop-pressure")
        w.set("chip", "leakshield")
        w.set("field", "fan1_input")

        # Flow rate — High Flow NEXT fan1 (dL/h, display as l/h)
        w = self.add_widget(full_text=self._text_flow)
        w.set("type", "flow-rate")
        w.set("chip", "highflownext")
        w.set("field", "fan1_input")

        # Water quality — High Flow NEXT fan2 (raw/100 = %)
        w = self.add_widget(full_text=self._text_quality)
        w.set("type", "coolant-quality")
        w.set("chip", "highflownext")
        w.set("field", "fan2_input")

        # Conductivity — High Flow NEXT fan3 (raw/10 = μS/cm)
        w = self.add_widget(full_text=self._text_conductivity)
        w.set("type", "conductivity")
        w.set("chip", "highflownext")
        w.set("field", "fan3_input")

    def _read(self, widget):
        chip_name = self._chips.get(widget.get("chip"))
        if not chip_name:
            return None
        return _read_sensor(chip_name, widget.get("field"))

    def _update_widget(self, widget):
        # full_text callables are re-evaluated on each render cycle,
        # so no explicit update needed here — just keep chips resolved.
        pass

    # --- full_text callables ---

    def _text_temp_in(self, widget):
        v = self._read(widget)
        return "{:0.1f}°C".format(v / 1000) if v is not None else "n/a"

    def _text_temp_out(self, widget):
        v = self._read(widget)
        return "{:0.1f}°C".format(v / 1000) if v is not None else "n/a"

    def _text_flow(self, widget):
        v = self._read(widget)
        return "{:0.0f}l/h".format(v / 10) if v is not None else "n/a"

    def _text_pump(self, widget):
        v = self._read(widget)
        return "{:0.0f}RPM".format(v) if v is not None else "n/a"

    def _text_quality(self, widget):
        v = self._read(widget)
        return "{:0.0f}%".format(v / 100) if v is not None else "n/a"

    def _text_conductivity(self, widget):
        v = self._read(widget)
        return "{:0.0f}μS/cm".format(v / 10) if v is not None else "n/a"

    def _text_pressure(self, widget):
        v = self._read(widget)
        return "{:0.0f}mbar".format(v / 1000) if v is not None else "n/a"


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
