"""Entry point del servidor — para build.py y ejecución directa."""
import asyncio
from frameworks.ws_runner import main

if __name__ == "__main__":
    asyncio.run(main())
