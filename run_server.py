import sys
import logging

from typing import List
from dataclasses import dataclass
from webthing import (MultipleThings, WebThingServer)
from gpio_manager import OutGpio, InGpio
from gpio_manager_web import GpioManagerWebServer
from gpio_manager_mcp import GpioManagerMCPServer
from gpio_manager_webthing import OutThing, InThing



@dataclass
class Config:
    type: str
    name: str
    description: str
    port: int
    reverted: bool

    @staticmethod
    def parse(conf: str):
        logging.info("parsing " + conf)
        parts = conf.split(":")
        try:
            if len(parts) > 4:
                return Config(parts[0], parts[1], parts[2], int(parts[3]), bool(parts[4]))
            elif len(parts) > 3:
                return Config(parts[0], parts[1], parts[2], int(parts[3]), False)
            else:
                return Config(parts[0], parts[1], parts[1], int(parts[2]), False)
        except Exception as e:
            logging.error("error parsing '" + conf + "':   " + str(e))
            raise e





def run_server(name: str, port: int, confs: List[Config]):
    out_gpios = [OutGpio(conf.port, conf.name, conf.description, conf.reverted) for conf in confs if conf.type.lower() == 'out']
    in_gpios = [InGpio(conf.port, conf.name, conf.description, conf.reverted) for conf in confs if conf.type.lower() == 'in']
    server = WebThingServer(MultipleThings([InThing(gpio) for gpio in in_gpios] + [OutThing(gpio) for gpio in out_gpios], "outs"), port=port, disable_host_validation=True)
    web_server = GpioManagerWebServer(port=port+1, in_gpios=in_gpios, out_gpios=out_gpios)
    mcp_server = GpioManagerMCPServer(name, port=port+2, in_gpios=in_gpios, out_gpios=out_gpios)
    try:
        logging.info('starting the server on port ' + str(port))
        web_server.start()
        mcp_server.start()
        server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        web_server.stop()
        mcp_server.stop()
        server.stop()
        logging.info('done')


if __name__ == '__main__':
    try:
        logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
        logging.getLogger('tornado.access').setLevel(logging.ERROR)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
        name = sys.argv[1]
        port = int(sys.argv[2])
        gpio = sys.argv[3]
        logging.info("gpio: " + gpio)
        gpio = gpio.replace("_", " ")
        confs = [Config.parse(conf) for conf in gpio.split("&")]
        run_server(name, port, confs)
    except Exception as e:
        logging.error(str(e))
        raise e
