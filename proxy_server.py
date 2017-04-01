
"""
From: https://gist.github.com/barrachri/32f865c4705f27e75d3b8530180589fb#file-proxy_server-py
"""

import logging
import sys
from urllib.parse import urljoin

import asyncio
import aiohttp
from aiohttp import web


TARGET_SERVER_BASE_URL = 'http://127.0.0.1:8888'


logger = logging.getLogger("runproxy")

async def proxy(request):

    target_url = urljoin(TARGET_SERVER_BASE_URL, request.match_info['path'])

    data = await request.read()
    get_data = request.rel_url.query

    logger.info("------------------------------------------------------------")
    logger.info("REQUEST C2P")
    logger.info("------------------------------------------------------------")
    logger.info("URL | HEADER | METHOD | DATA | GET DATA")
    logger.info("------------------------------------------------------------")
    logger.info("{} | {} | {} |{} | {}".format(target_url, request.headers, request.method, data, get_data))


    async with aiohttp.ClientSession() as session:

        # check if the client is asking to upgrade the connection
        if "Upgrade" in request.headers:
            ws_c2p = web.WebSocketResponse()
            await ws_c2p.prepare(request)

            async with session.ws_connect(target_url) as ws_p2s:
                async for msg in ws_c2p:
                    logger.info("------------------------------------------------------------")
                    logger.info("WEBSOCKET C2P: %s", msg.data)
                    logger.info("------------------------------------------------------------")
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        if msg.data == 'close':
                            await ws_c2p.close()
                        else:
                            ws_p2s.send_str(msg.data)
                            data_p2s = await ws_p2s.receive_str()
                            logger.info("------------------------------------------------------------")
                            logger.info("WEBSOCKET P2S: %s", data_p2s)
                            logger.info("------------------------------------------------------------")
                            ws_c2p.send_str(data_p2s)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.info("------------------------------------------------------------")
                        logger.info('ws connection closed with exception %s' % ws.exception())
                        logger.info("------------------------------------------------------------")

            logger.info("------------------------------------------------------------")
            logger.info("websocket connection closed")
            logger.info("------------------------------------------------------------")

            return ws_c2p
        else:
            async with session.request(request.method, target_url, headers=request.headers, params=get_data, data=data) as resp:
                res = resp
                raw = await res.read()

    logger.info("------------------------------------------------------------")
    logger.info("RESPONSE P2C")
    logger.info("------------------------------------------------------------")
    logger.info("Header {} | Status {}".format(res.headers, res.status))
    logger.info("------------------------------------------------------------")

    return web.Response(body=raw, status=res.status, headers=res.headers)


if __name__ == "__main__":

    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(logging.StreamHandler(sys.stdout))

    app = web.Application()
    app.router.add_route('*', '/{path:.*?}', proxy)

    loop = asyncio.get_event_loop()
    f = loop.create_server(app.make_handler(), '0.0.0.0', 8080)
    srv = loop.run_until_complete(f)
    print('serving on', srv.sockets[0].getsockname())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass