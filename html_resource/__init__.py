#
# import os
# from aiohttp import web
#
# ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
#
# async def index(request):
#     content = open(os.path.join(ROOT, "static/web/index.html"), "r").read()
#     return web.Response(content_type="text/html", text=content)
#
#
# async def javascript(request):
#     content = open(os.path.join(ROOT, "static/web/client.js"), "r").read()
#     return web.Response(content_type="application/javascript", text=content)
#
#
# async def css(request):
#     content = open(os.path.join(ROOT, "static/web/styles.css"), "r").read()
#     return web.Response(content_type="text/css", text=content)
