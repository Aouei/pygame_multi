import server

import json
import pygame
import pygame_gui
import websockets
import asyncio
import threading


class Connection:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._server_obj: server.Server | None = None
        self.client = None
        self.clients = 0
        self._stopping = False

    @property
    def is_connected(self):
        return self._thread is not None and self._thread.is_alive()

    async def start(self):
        old_thread = self._thread if self.is_connected else None
        if old_thread:
            await self.stop()
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, old_thread.join, 2.0)

        self._server_obj = server.Server()
        srv = self._server_obj
        self._thread = threading.Thread(
            target=lambda: asyncio.run(server.run(srv)),
            daemon=True
        )
        self._thread.start()
        asyncio.create_task(self.connect())

    async def stop(self):
        self._stopping = True
        try:
            if self._server_obj:
                self._server_obj.running = False
            if self.client is not None:
                await self.client.close()
        except (websockets.exceptions.ConnectionClosed, OSError) as e:
            print(f"Stop error: {e}")
        finally:
            self._server_obj = None
            self._thread = None
            self.client = None
            self.clients = 0
            self._stopping = False

    async def receive_from_server(self, websocket) -> None:
        async for raw in websocket:
            data = json.loads(raw)
            self.clients = data.get('clients', 0)

    async def connect(self):
        for _ in range(20):
            if self._stopping:
                break
            try:
                async with websockets.connect("ws://localhost:25565") as websocket:
                    self.client = websocket
                    await self.receive_from_server(websocket)
                return
            except OSError:
                await asyncio.sleep(0.1)
            except websockets.exceptions.ConnectionClosed as e:
                print(f"Connection closed: {e}")
                return
        print("Could not connect to server")
        self.client = None
        self.clients = 0


async def main():
    global CONNECTED
    global PROCESS

    pygame.init()

    connection = Connection()

    window = pygame.display.set_mode((700, 700))
    manager = pygame_gui.UIManager(window.get_size())
    clock = pygame.time.Clock()

    host = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((0, 0), (100, 50)),
                                                text='Host',
                                                manager=manager,
                                                anchors={'center': 'center'})

    disconnect = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((100, 0), (100, 50)),
                                                text='Disconnect',
                                                manager=manager,
                                                anchors={'center': 'center'})

    clients = pygame_gui.elements.UITextBox(str(connection.clients), 
                                               relative_rect=pygame.Rect((100, 50), (100, 50)),
                                               manager=manager,
                                               anchors={'center': 'center'})
    disconnect.disable()

    playing = True
    while playing:
        time_delta = clock.tick(60)/1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                playing = False

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == host:
                    await connection.start()
                    await asyncio.sleep(2)
                    asyncio.create_task(connection.connect())

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == disconnect:
                    await connection.stop()
            
            manager.process_events(event)

        if playing:
            if connection.is_connected:
                disconnect.enable()
            else:
                disconnect.disable()

            clients.set_text(str(connection.clients))

            window.fill((0, 0, 0))
            manager.update(time_delta)
            manager.draw_ui(window)
            pygame.display.update()

    pygame.quit()


if __name__ == '__main__':
    asyncio.run(main())
    # try:
    # except websockets.exceptions.ConnectionClosed:
    #     pass
    # except Exception:
    #     pass
    # finally:
    #     print('Fin')