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
    line: int
    reverted: bool
    chip: str = None

    @staticmethod
    def __parse_port(field: str):
        """Parses a port field of the form 'chip#line' (e.g. 'gpiochip1#11')
        or a bare line number (e.g. '11'). Returns (chip, line)."""
        if "#" in field:
            chip, line = field.split("#", 1)
            return chip, int(line)
        return None, int(field)

    @staticmethod
    def parse(conf: str):
        # e.g. in:MotionLivingroom:gpiochip1#11&in:MotionCorridor:gpiochip1#13
        logging.info("parsing " + conf)
        parts = conf.split(":")
        try:
            if len(parts) > 4:
                chip, line = Config.__parse_port(parts[3])
                # FIX: String sicher in Boolean umwandeln
                is_reverted = parts[4].strip().lower() in ('true', '1', 'yes')
                return Config(type=parts[0], name=parts[1], description=parts[2], line=line, reverted=is_reverted, chip=chip)
            elif len(parts) > 3:
                chip, line = Config.__parse_port(parts[3])
                return Config(type=parts[0], name=parts[1], description=parts[2], line=line, reverted=False, chip=chip)
            else:
                chip, line = Config.__parse_port(parts[2])
                # Hinweis: Hier wird parts[1] (name) aktuell auch als Description genutzt.
                return Config(type=parts[0], name=parts[1], description=parts[1], line=line, reverted=False, chip=chip)
        except Exception as e:
            logging.error("error parsing '" + conf + "':   " + str(e))
            raise e


def run_server(name: str, port: int, confs: List[Config]):
    out_gpios = [OutGpio(conf.line, conf.name, conf.description, conf.reverted, conf.chip) for conf in confs if conf.type.lower() == 'out']
    in_gpios = [InGpio(conf.line, conf.name, conf.description, conf.reverted, conf.chip) for conf in confs if conf.type.lower() == 'in']
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
        logging.getLogger("mcp.server.lowlevel").setLevel(logging.WARNING)
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



# npx @modelcontextprotocol/inspector
# http://localhost:6274/