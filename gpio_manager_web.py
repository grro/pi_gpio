import json
import threading
import logging
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List
from gpio_manager import OutGpio, InGpio # Ensure these match your local file

class SimpleRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass # Keep console clean

    def do_GET(self):
        out_gpios: Dict[str, OutGpio] = self.server.out_gpios
        in_gpios: Dict[str, InGpio] = self.server.in_gpios

        parsed_url = urlparse(self.path)
        path = parsed_url.path.lstrip("/")
        query_params = parse_qs(parsed_url.query)

        # 1. Handle Output GPIOs (Control)
        if path in out_gpios:
            gpio = out_gpios[path]
            if 'set' in query_params:
                val = query_params['set'][0].lower()
                if val in ['true', '1', 'on']:
                    gpio.switch(True)
                else:
                    gpio.switch(False)

            self._send_json(200, {'name': path, 'value': gpio.is_on, 'reverted': gpio.reverted})
            return

        # 2. Handle Input GPIOs (Read-only)
        if path in in_gpios:
            gpio = in_gpios[path]
            self._send_json(200, {'name': path, 'value': gpio.on, 'reverted': gpio.reverted, 'last_change': gpio.last_change.isoformat()})
            return

        # 3. Handle Index/Home Page
        html = "<html><body><h1>GPIO Control Panel</h1><ul>"
        html += "<h3>Inputs</h3>"
        for name, gpio in in_gpios.items():
            status = "ON" if gpio.on else "OFF"
            html += f"<li><a href='/{name}'>{name}</a> (IN {gpio.gpio_number}) - Current: {status} (last change {gpio.last_change.strftime('%Y-%m-%dT%H:%M:%S')})</li>"

        html += "<h3>Outputs</h3>"
        for name, gpio in out_gpios.items():
            status = "ON" if gpio.on else "OFF"
            html += f"<li><a href='/{name}'>{name}</a> (OUT {gpio.gpio_number}) - Current: {status} "
            html += f"[<a href='/{name}?set=true'>ON</a> | <a href='/{name}?set=false'>OFF</a>]</li>"

        html += "</ul></body></html>"
        self._send_html(200, html)


    def _send_html(self, status, message):
        self.send_response(status)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def _send_json(self, status, data: Dict[str, Any]):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

class GpioManagerWebServer:
    def __init__(self, in_gpios: List[InGpio], out_gpios: List[OutGpio], host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.address = (self.host, self.port)
        self.server = HTTPServer(self.address, SimpleRequestHandler)
        # Store references in the server object for the RequestHandler to use
        self.server.out_gpios = {gpio.name: gpio for gpio in out_gpios}
        self.server.in_gpios = {gpio.name: gpio for gpio in in_gpios}
        self.server_thread = None

    def start(self):
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        logging.info(f"Web server started: http://{self.host}:{self.port}")

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        logging.info("Web server stopped")