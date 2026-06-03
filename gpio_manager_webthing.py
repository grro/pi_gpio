from webthing import (Property, Thing, Value)
import tornado.ioloop
from gpio_manager import OutGpio, InGpio


class OutThing(Thing):

    # regarding capabilities refer https://iot.mozilla.org/schemas
    # there is also another schema registry http://iotschema.org/docs/full.html not used by webthing

    def __init__(self, out: OutGpio):
        Thing.__init__(
            self,
            'urn:dev:ops:gpio_out-1',
            'Out ' + out.name,
            ['GpioOut'],
            ""
        )

        self.ioloop = tornado.ioloop.IOLoop.current()
        self.out = out

        self.is_on = Value(out.is_on, out.switch)
        self.add_property(
            Property(self,
                     'is-on',
                     self.is_on,
                     metadata={
                         'title': 'is on',
                         "type": "boolean",
                         'description': 'True if is on',
                         'readOnly': False,
                     }))

    def on_value_changed(self):
        self.ioloop.add_callback(self._on_value_changed)

    def _on_value_changed(self):
        pass



class InThing(Thing):

    # regarding capabilities refer https://iot.mozilla.org/schemas
    # there is also another schema registry http://iotschema.org/docs/full.html not used by webthing

    def __init__(self, in_gpio: InGpio):
        Thing.__init__(
            self,
            'urn:dev:ops:gpio_in-1',
            'In ' + in_gpio.name,
            ['GpioIn'],
            ""
        )

        self.ioloop = tornado.ioloop.IOLoop.current()
        self.in_gpio = in_gpio

        self.is_on = Value(in_gpio.on)
        self.add_property(
            Property(self,
                     'on',
                     self.is_on,
                     metadata={
                         'title': 'is on',
                         "type": "boolean",
                         'description': 'True if is on',
                         'readOnly': True,
                     }))

        self.last_on = Value(in_gpio.last_on.strftime("%Y-%m-%dT%H:%M:%S"))
        self.add_property(
            Property(self,
                     'last_on',
                     self.last_on,
                     metadata={
                         'title': 'last on',
                         "type": "string",
                         'description': 'datetime of last on (ISO8601)',
                         'readOnly': True,
                     }))

        self.last_off = Value(in_gpio.last_off.strftime("%Y-%m-%dT%H:%M:%S"))
        self.add_property(
            Property(self,
                     'last_off',
                     self.last_off,
                     metadata={
                         'title': 'last off',
                         "type": "string",
                         'description': 'datetime of last off (ISO8601)',
                         'readOnly': True,
                     }))

        self.last_change = Value(in_gpio.last_change.strftime("%Y-%m-%dT%H:%M:%S"))
        self.add_property(
            Property(self,
                     'last_change',
                     self.last_change,
                     metadata={
                         'title': 'last change',
                         "type": "string",
                         'description': 'datetime of last change (ISO8601)',
                         'readOnly': True,
                     }))

        self.in_gpio.add_listener(self.on_value_changed)

    def on_value_changed(self, name: str):
        self.ioloop.add_callback(self._on_value_changed)

    def _on_value_changed(self):
        self.is_on.notify_of_external_update(self.in_gpio.on)
        self.last_on.notify_of_external_update(self.in_gpio.last_on.strftime("%Y-%m-%dT%H:%M:%S"))
        self.last_off.notify_of_external_update(self.in_gpio.last_off.strftime("%Y-%m-%dT%H:%M:%S"))
        self.last_change.notify_of_external_update(self.in_gpio.last_change.strftime("%Y-%m-%dT%H:%M:%S"))


