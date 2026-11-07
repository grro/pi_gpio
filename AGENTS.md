# AGENTS.md

> AI agents: read this file in full before changing files or running commands.

## Project

Controls and monitors Raspberry Pi GPIO pins using `libgpiod` and exposes them through a WebThing
API and an MCP SSE server. The configured base port defaults to `8316`; MCP uses `port + 2`
(`/sse`). No separate HTTP control server is started.

Primary target: Docker on a **Raspberry Pi Zero 2 W** (64-bit, 512 MB RAM, SD card). Keep CPU,
memory, disk writes, image size, and startup work low. GPIO access requires the container to be
given access to the host GPIO character devices. The service must start without internet access;
mDNS discovery is optional.

## Where things are

- `run_server.py` – entry point (`<name> <port> <gpio-config>`), parses GPIO configuration and starts all servers
- `gpio_manager.py` – GPIO input/output handling with `gpiod`, chip selection, and input listeners
- `gpio_manager_webthing.py` – WebThing properties for GPIO inputs and outputs
- `gpio_manager_mcp.py` – MCP resources/tools over SSE and mDNS discovery
- `Dockerfile` – Python 3.11 image; environment variables `name`, `port`, and `gpio`
- `.github/workflows/publish_to_dockerhub.yml` – tag-triggered multi-architecture image publish (`grro/pi_gpio`)

GPIO configuration entries are joined with `&` and have the form
`type:name:description:chip#line[:reverted]`, for example
`in:Motion:Room_motion:gpiochip0#11&out:Relay:Room_relay:gpiochip0#13:false`.
The chip may be omitted by using a bare line number; GPIO chip selection can also use `GPIO_CHIP`.
The command-line parser replaces underscores with spaces in the configuration argument.

## Workflow (spec first)

1. State intended behavior first: inputs, outputs, affected ports, and failure cases (no GPIO, shutdown).
2. Get agreement before changing externally visible interfaces (configuration syntax, resource/tool names, ports).
3. Make the smallest change, verify it, and update `README.md` for user-visible changes.

## Commands

There is no checked-in test suite. Build and verify imports in the container:

```sh
docker build --platform linux/arm64/v8 --tag pi_gpio:dev .
docker run --rm --entrypoint python pi_gpio:dev -c "import run_server, gpio_manager, gpio_manager_webthing, gpio_manager_mcp"
```

Exercise GPIO-dependent behavior on a Raspberry Pi Zero 2 W with the required `/dev/gpiochip*`
device access. Check startup and shutdown on the target device. The MCP and WebThing interfaces can
be checked independently of GPIO hardware by using test doubles for `InGpio` and `OutGpio`.

## Conventions

- Use `logging`, not `print`.
- GPIO input event polling runs in daemon threads; WebThing uses Tornado, and MCP runs its asyncio
  event loop in a dedicated thread. Cross-thread asyncio calls must use thread-safe APIs.
- Keep dependencies and Docker image changes minimal; `fastmcp`, `gpiod`, and `zeroconf` versions
  are pinned in `requirements.txt`.
- Avoid unnecessary background workers, polling, network requests, startup work, and persistent SD
  card writes. Do not make internet access required for startup or normal operation.
- Preserve the existing server shutdown behavior when changing lifecycle handling.

## Definition of done

- The ARM64 Docker build and import check pass; changed behavior is exercised.
- On the Zero 2 W, startup and normal operation do not require internet access and add no unnecessary
  CPU, memory, or SD-card overhead.
- No regression in GPIO input/output handling, the WebThing/MCP interfaces, or shutdown.
- `README.md` is updated when user-visible behavior changes; no secrets are committed.
