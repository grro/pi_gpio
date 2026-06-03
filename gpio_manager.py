import logging
import RPi.GPIO as GPIO
from threading import Thread
from datetime import datetime, UTC
from time import sleep



class OutGpio:

    def __init__(self, gpio_number: int, name: str, description: str, reverted: bool):
        self.name = name
        self.description = description
        self.gpio_number = gpio_number
        self.reverted = reverted
        self.__datetime_last_on = datetime.now()
        self.__datetime_last_off = datetime.now()
        self.__datetime_last_change = datetime.now(UTC)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_number, GPIO.OUT)
        logging.info("GPIO OUT " + name + " registered on " + str(self.gpio_number) + (" (reverted=true)" if self.reverted else ""))
        self.switch(False)


    @property
    def last_on(self) -> datetime:
        return self.__datetime_last_on

    @property
    def last_off(self) -> datetime:
        return self.__datetime_last_off

    def switch(self, on:bool):
        logging.info("setting OUT " + str(self.gpio_number) + " " + ("on" if on else "off"))
        if self.reverted:
            on = not on
        if on:
            GPIO.output(self.gpio_number,GPIO.HIGH)
            self.__datetime_last_on = datetime.now(UTC)
            self.__datetime_last_change = datetime.now(UTC)
        else:
            GPIO.output(self.gpio_number,GPIO.LOW)
            self.__datetime_last_off = datetime.now(UTC)
            self.__datetime_last_change = datetime.now(UTC)

    def is_on(self) -> bool:
        return GPIO.input(self.gpio_number)

    @property
    def on(self) -> bool:
        return self.is_on() if not self.reverted else not self.is_on()




class InGpio:

    def __init__(self, gpio_number: int, name: str, description: str, reverted: bool):
        self.name = name
        self.description = description
        self.gpio_number = gpio_number
        self.reverted = reverted
        self.__on = None
        self.__datetime_last_on = datetime.now(UTC)
        self.__datetime_last_off = datetime.now(UTC)
        self.__datetime_last_change = datetime.now(UTC)
        self.listeners = set()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_number, GPIO.IN)
        logging.info("GPIO IN " + name + " registered on " + str(self.gpio_number) + (" (reverted=true)" if self.reverted else ""))
        GPIO.add_event_detect(self.gpio_number, GPIO.BOTH, callback=self.__check())
        Thread(target=self.__loop, daemon=True).start()

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

    def motify_listeners(self):
        [listener(self.name) for listener in self.listeners]

    def __check(self):
        new_on = GPIO.input(self.gpio_number) == 1
        if new_on != self.__on:
            self.__on = new_on
            self.__datetime_last_change = datetime.now(UTC)
            if new_on:
                self.__datetime_last_on = datetime.now(UTC)
            else:
                self.__datetime_last_off = datetime.now(UTC)

            msg = "GPIO IN " + self.name + " new effective state: " + str(self.on) + " last_change: " + self.__datetime_last_change.strftime("%Y-%m-%dT%H:%M:%S")
            config = "GPIO " + str(self.gpio_number) + ": " + str(GPIO.input(self.gpio_number)) + ("; reverted" if self.reverted else "")
            logging.info(msg + " (" + config + ")")

            self.motify_listeners()

    def __loop(self):
        while True:
            try:
                self.__check()
            except Exception as e:
                logging.error("Error in GPIO IN " + self.name + " listener: " + str(e))
            finally:
                sleep(2)