import asyncio
import json
import logging
import socket
import threading
from typing import Protocol, cast, Dict, List, Any
from fastmcp import FastMCP, Context
from pydantic import AnyUrl, TypeAdapter
from zeroconf import IPVersion, ServiceInfo, Zeroconf

#from gpio_manager import OutGpio, InGpio



logger = logging.getLogger(__name__)


class MDNS:
    def __init__(self) -> None:
        self.registered: dict[str, ServiceInfo] = {}
        self.zc = Zeroconf(ip_version=IPVersion.V4Only)
        self.service_type = "_mcp._tcp.local."
        self.hostname = socket.gethostname()
        self.local_ip = self._resolve_local_ip()

    @staticmethod
    def _resolve_local_ip() -> str:
        """Determine the primary outbound IP without sending any packets."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except OSError:
            logger.warning("mDNS: could not determine local IP, falling back to 127.0.0.1")
            return "127.0.0.1"
        finally:
            s.close()

    def register_mdns(self, name: str, port: int) -> None:
        service_name = f"{name}.{self.service_type}"
        try:
            service_info = ServiceInfo(
                type_=self.service_type,
                name=service_name,
                addresses=[socket.inet_aton(self.local_ip)],
                port=port,
                properties={
                    "version": "1.0",
                    "path": "/sse",
                    "server_type": "fastmcp",
                },
                server=f"{self.hostname}.local.",
            )

            logger.info("mDNS: registering %s at %s:%d", service_name, self.local_ip, port)
            self.zc.register_service(service_info)
            self.registered[name] = service_info
        except Exception as e:
            logger.error("mDNS registration failed for %s: %s", service_name, e)

    def unregister_mdns(self, name: str) -> None:
        service_info = self.registered.pop(name, None)
        if service_info is not None:
            logger.info("mDNS: unregistering %s", name)
            self.zc.unregister_service(service_info)

    def close(self) -> None:
        """Unregister everything and tear down the shared Zeroconf instance."""
        for name in list(self.registered):
            self.unregister_mdns(name)
        self.zc.close()


class ResourceUpdateSession(Protocol):
    async def send_resource_updated(self, uri: AnyUrl) -> None:
        ...


class GpioManagerMCPServer:
    _url_adapter = TypeAdapter(AnyUrl)

    def __init__(
            self,
            name: str,
            port: int,
            in_gpios: list,
            out_gpios: list,
           # in_gpios: list[InGpio],
           # out_gpios: list[OutGpio],
            host: str = "0.0.0.0",
    ) -> None:
        self.name = name
        self.host = host
        self.port = port

        self.mdns = MDNS()
        self.mcp = FastMCP(self.name)
        self.active_sessions: set[ResourceUpdateSession] = set()

        self.out_gpios = {gpio.name: gpio for gpio in out_gpios}
        self.in_gpios = {gpio.name: gpio for gpio in in_gpios}
        self.loop = asyncio.new_event_loop()
        self.last_state: dict[str, bool] = {}
        self._thread: threading.Thread | None = None

        for in_gpio in self.in_gpios.values():
            in_gpio.add_listener(self.__on_value_changed)

        self._register_handlers()

    def _register_handlers(self) -> None:

        @self.mcp.resource("sensor://gpio")
        def get_gpio_names() -> List[Dict[str, str]]:
            """Returns a JSON list of all GPIOs including their direction, id, and name."""
            gpio_data = [
                            {"id": name, "name": name, "direction": "in"} for name in self.in_gpios
                        ] + [
                            {"id": name, "name": name, "direction": "out"} for name in self.out_gpios
                        ]
            return gpio_data

        @self.mcp.resource("sensor://gpio/{name}")
        def get_gpio(name: str, ctx: Context) -> Dict[str, Any]:
            """
            Return the current state of a single GPIO (input or output) as JSON.
            Registers the client session to receive real-time push notifications.
            """
            try:
                req_ctx = ctx.request_context
                if req_ctx and req_ctx.session and req_ctx.session not in self.active_sessions:
                    self.active_sessions.add(cast(ResourceUpdateSession, req_ctx.session))
                    logger.info(f"[Server] Client session registered for updates (Resource: {name}).")
            except Exception as e:
                logger.debug(f"[Server] Could not register session: %s", e)

            if name in self.in_gpios:
                return {
                    "id": name,
                    "direction": "in",
                    "state": self.in_gpios[name].on
                }

            if name in self.out_gpios:
                return {
                    "id": name,
                    "direction": "out",
                    "state": self.out_gpios[name].on
                }

            return {"error": f"GPIO '{name}' not found."}


        @self.mcp.tool(name="gpios")
        def get_gpio_overview() -> str:
            """Return all inputs with their state plus all output names."""
            overview = {
                "inputs": {name: gpio.on for name, gpio in self.in_gpios.items()},
                "outputs": list(self.out_gpios.keys()),
            }
            return json.dumps(overview)

    def __on_value_changed(self, name: str) -> None:
        if not self.loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(self._trigger_client_notification(name), self.loop)

    async def _trigger_client_notification(self, name: str) -> None:
        if not self.active_sessions:
            return

        gpio = self.in_gpios.get(name)
        if gpio is None:
            logger.warning("Trigger called for unknown GPIO: %s", name)
            return

        current_state = gpio.on
        if current_state == self.last_state.get(name):
            return
        self.last_state[name] = current_state

        uri = self._url_adapter.validate_python(f"sensor://gpio/{name}")
        dead_sessions: set[ResourceUpdateSession] = set()

        for session in self.active_sessions:
            try:
                await session.send_resource_updated(uri)
            except Exception as e:
                logger.warning("Failed to send update to session: %s", e)
                dead_sessions.add(session)

        self.active_sessions -= dead_sessions

    async def __run(self) -> None:
        logger.info(
            "MCP server '%s' running on http://%s:%d/sse", self.name, self.host, self.port
        )
        await self.mcp.run_async(
            transport="sse",
            host=self.host,
            port=self.port,
            uvicorn_config={"access_log": False, "log_config": None},
        )

    def start(self) -> None:
        self.mdns.register_mdns(self.name, self.port)

        def _run_loop() -> None:
            asyncio.set_event_loop(self.loop)
            try:
                self.loop.run_until_complete(self.__run())
            finally:
                self.loop.close()

        self._thread = threading.Thread(target=_run_loop, daemon=True, name=f"mcp-{self.name}")
        self._thread.start()

    def stop(self) -> None:
        self.mdns.close()
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        logger.info("MCP server '%s' stopped", self.name)