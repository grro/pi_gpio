# AGENTS.md

> Read before changing files or running commands.

## Project

GPIO via `libgpiod`, WebThing on `port` (default `8316`), MCP SSE on `port + 2` (`/sse`).
No separate HTTP control server.

Primary target: Docker on a **Raspberry Pi Zero 2 W** (64-bit, 512 MB RAM, SD card).
Minimize CPU, RAM, image size, startup work, and disk writes. Runtime must work without internet;
mDNS is optional. Containers need access to the GPIO devices.

## Files

- `run_server.py` – entry point: `<name> <port> <gpio-config>`
- `gpio_manager.py` – GPIO I/O, chip selection, listeners
- `gpio_manager_webthing.py` – WebThing properties
- `gpio_manager_mcp.py` – MCP resources/tools and mDNS
- `Dockerfile` – Python 3.11; env `name`, `port`, `gpio`, `PI_GPIO_VERSION`
- `.github/workflows/publish_to_dockerhub.yml` – git tag → multi-arch `grro/pi_gpio`

GPIO config: `type:name:description:chip#line[:reverted]`, entries joined by `&`.
Bare line numbers use automatic chip selection or `GPIO_CHIP`; underscores become spaces.

## Rules

- State intended behavior and failures first; agree on interface changes before implementing.
- Make small changes; update `README.md` for user-visible changes.
- Use `logging`, not `print`. Keep dependency versions pinned.
- GPIO uses daemon threads, WebThing uses Tornado, MCP uses its own asyncio loop.
  Cross-thread calls must use thread-safe APIs.
- Preserve shutdown behavior; avoid unnecessary workers, polling, network access, and SD-card writes.
- Never commit secrets.

## Verification

No checked-in test suite:

```sh
docker build --platform linux/arm64/v8 --tag pi_gpio:dev .
docker run --rm --entrypoint python pi_gpio:dev -c "import run_server, gpio_manager, gpio_manager_webthing, gpio_manager_mcp"
```

Exercise changed behavior; use fake GPIOs for interface checks. Verify GPIO access, offline startup,
shutdown, and resource usage on the Zero 2 W. Preserve GPIO and WebThing/MCP behavior.
