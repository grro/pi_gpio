import os
import glob
import logging
import threading
from datetime import datetime, UTC, timedelta

import gpiod
from gpiod.line import Direction, Value, Bias, Edge


_CONSUMER = "pi_gpio"


def _resolve_chip_path(value: str) -> str:
    """Accepts a full path (/dev/gpiochip0), a device name (gpiochip0)
    or a bare number (0) and returns the full device path."""
    value = value.strip()
    if value.startswith("/"):
        return value
    if value.isdigit():
        return "/dev/gpiochip" + value
    return "/dev/" + value


def _find_gpiochip(chip: str = None) -> str:
    """Return the GPIO chip device. Priority: explicit per-device chip
    argument, then the GPIO_CHIP env var, then auto-detection of the SoC
    GPIO chip (Pi <=4: gpiochip0, Pi 5: gpiochip4).
    Accepts 'gpiochip0', '/dev/gpiochip0' or '0'."""
    configured = chip or os.environ.get("GPIO_CHIP") or os.environ.get("gpiochip")
    if configured:
        return _resolve_chip_path(configured)
    for path in sorted(glob.glob("/dev/gpiochip*")):
        try:
            if not gpiod.is_gpiochip_device(path):
                continue
            with gpiod.Chip(path) as chip:
                if chip.get_info().label.startswith("pinctrl"):
                    return path
        except Exception:
            continue
    return "/dev/gpiochip0"


class OutGpio:

    def __init__(self, line: int, name: str, description: str, reverted: bool, chip: str = None):
        self.name = name
        self.description = description
        self.addr = str(chip) + "#" +  str(line)
        self.reverted = reverted
        self.__offset = line
        self.__datetime_last_on = datetime.now()
        self.__datetime_last_off = datetime.now()
        self.__datetime_last_change = datetime.now(UTC)
        self.__request = gpiod.request_lines(
            _find_gpiochip(chip),
            consumer=_CONSUMER,
            config={
                self.__offset: gpiod.LineSettings(
                    direction=Direction.OUTPUT,
                    output_value=Value.INACTIVE,
                )
            },
        )
        logging.info("GPIO OUT " + name + " registered on " + self.addr + (" (reverted=true)" if self.reverted else ""))
        self.switch(False)

    @property
    def last_on(self) -> datetime:
        return self.__datetime_last_on

    @property
    def last_off(self) -> datetime:
        return self.__datetime_last_off

    @property
    def last_change(self) -> datetime:
        return self.__datetime_last_change

    def switch(self, on:bool):
        logging.info("setting OUT " + str(self.line) + " " + ("on" if on else "off"))
        if self.reverted:
            on = not on
        if on:
            self.__request.set_value(self.__offset, Value.ACTIVE)
            self.__datetime_last_on = datetime.now(UTC)
            self.__datetime_last_change = datetime.now(UTC)
        else:
            self.__request.set_value(self.__offset, Value.INACTIVE)
            self.__datetime_last_off = datetime.now(UTC)
            self.__datetime_last_change = datetime.now(UTC)

    def is_on(self) -> bool:
        return self.__request.get_value(self.__offset) == Value.ACTIVE

    @property
    def on(self) -> bool:
        return self.is_on() if not self.reverted else not self.is_on()




class InGpio:

    def __init__(self, line: int, name: str, description: str, reverted: bool, chip: str = None):
        self.name = name
        self.description = description
        self.addr = str(chip) + "#" +  str(line)
        self.reverted = reverted
        self.__offset = line
        self.__on = None
        self.__datetime_last_on = datetime.now(UTC)
        self.__datetime_last_off = datetime.now(UTC)
        self.__datetime_last_change = datetime.now(UTC)
        self.listeners = set()

        self.__request = gpiod.request_lines(
            _find_gpiochip(chip),
            consumer=_CONSUMER,
            config={
                self.__offset: gpiod.LineSettings(
                    direction=Direction.INPUT,
                    bias=Bias.PULL_UP,
                    edge_detection=Edge.BOTH,
                    debounce_period=timedelta(milliseconds=200),
                )
            },
        )

        logging.info(f"GPIO IN {name} registered on {self.addr} " + (" (reverted=true)" if self.reverted else ""))

        self.__on = self.__read()
        self.__running = True
        self.__thread = threading.Thread(target=self.__event_loop, name=f"gpio-in-{name}", daemon=True)
        self.__thread.start()

    def __read(self) -> bool:
        return self.__request.get_value(self.__offset) == Value.ACTIVE

    @property
    def on(self) -> bool:
        return not self.__on if self.reverted else self.__on

    @property
    def last_on(self) -> datetime:
        return self.__datetime_last_on

    @property
    def last_off(self) -> datetime:
        return self.__datetime_last_off

    @property
    def last_change(self) -> datetime:
        return self.__datetime_last_change

    def add_listener(self, listener):
        self.listeners.add(listener)

    def notify_listeners(self):
        for listener in self.listeners:
            listener(self.name)

    def __event_loop(self):
        while self.__running:
            try:
                if self.__request.wait_edge_events(timedelta(seconds=1)):
                    self.__request.read_edge_events()
                    self.__check()
            except Exception as e:
                logging.error("Error in GPIO IN " + self.name + " event loop: " + str(e))

    def __check(self, channel=None):
        try:
            new_on = self.__read()
            if new_on != self.__on:
                self.__on = new_on
                self.__datetime_last_change = datetime.now(UTC)
                if new_on:
                    self.__datetime_last_on = datetime.now(UTC)
                else:
                    self.__datetime_last_off = datetime.now(UTC)

                msg = "GPIO IN " + self.name + " new effective state: " + str(self.on) + " last_change: " + self.__datetime_last_change.strftime("%Y-%m-%dT%H:%M:%S")
                config = "GPIO " + str(self.addr) + ": " + str(int(new_on)) + ("; reverted" if self.reverted else "")
                logging.info(msg + " (" + config + ")")

                self.notify_listeners()
        except Exception as e:
            logging.error("Error in GPIO IN " + self.name + " listener: " + str(e))