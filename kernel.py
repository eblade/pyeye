import asyncio
import json
import aiohttp
import sys
import io
import contextlib
from aiohttp import web
import base64
import traceback

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

def plot_function():
    f = io.BytesIO()
    plt.savefig(f, format='png')
    return Image(f)

class Image:
    def __init__(self, f):
        self.data = f.getvalue()

    def _repr_html_(self):
        return '<img src="data:image/png;base64, ' + base64.b64encode(self.data).decode() + '" />'

_globals = {
    'np': np,
    'pd': pd,
    'plt': plt,
    'matplotlib': matplotlib,
    'plot': plot_function
}
_locals = {}

_requests = []
_requests_lock = asyncio.Lock()
_websockets = []
_websockets_lock = asyncio.Lock()


async def post_request_handler(request):
    data = await request.json()
    code = data['code']
    print(code)
    r = Request(code)

    with await _requests_lock:
        r.id = len(_requests)
        _requests.append(r)

    asyncio.ensure_future(push_to_all(r.to_json()))
    asyncio.ensure_future(run_request(r))

    return web.json_response(r.to_dict())


async def run_request(request):
    chunks = request.code.rsplit('\n', 1)
    if len(chunks) == 1:
        body = None
        last_line = chunks[0]
    else:
        body = chunks[0]
        last_line = chunks[1]

    if last_line.startswith(' ') or last_line.startswith('\t'):
        last_line = '\n'.join([body, last_line])
        body = None

    try:
        with catch_output() as (stdout, stderr):
            if body is not None:
                exec(body, _globals, _locals)

            if is_statement(last_line):
                result = exec(last_line, _globals, _locals)
            else:
                result = eval(last_line, _globals, _locals)
                request.is_eval = True
        request.result = result
        request.status = 'done'

        request.stdout = stdout.getvalue()
        request.stderr = stderr.getvalue()

    except Exception as e:
        request.stderr = traceback.format_exc()
        request.status = 'failed'

    print(request.to_json())
    asyncio.ensure_future(push_to_all(request.to_json()))


async def get_request_handler(request):
    request_id = int(request.match_info.get('request_id'))
    with await _requests_lock:
        r = _requests[request_id]
    return web.json_response(r.to_dict())


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print('websocket connection established')

    with await _websockets_lock:
        _websockets.append(ws)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                with await _websockets_lock:
                    _websockets.remove(ws)
                await ws.close()
            else:
                request_id = int(msg.data)
                with await _requests_lock:
                    if len(_requests) >= request_id - 1:
                        response = "{}"
                    else:
                        response = _requests[request_id].to_json()
                    await ws.send_str(response)
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())

    print('websocket connection closed')

    return ws


async def get_webpage_handler(request):
    html = open('index.html', 'r').read()
    resp = web.Response(body=html.encode('utf-8'))
    resp.headers['content-type'] = 'text/html'
    return resp


async def push_to_all(message):
    with await _websockets_lock:
        for ws in _websockets:
            await ws.send_str(message)

def is_statement(s):
    try:
        compile(s, '<user>', 'eval')
        return False
    except SyntaxError:
        return True


class Request:
    def __init__(self, code):
        self.id = None
        self.code = code
        self.result = None
        self.is_eval = False
        self.status = 'running'
        self.stdout = None
        self.stderr = None

    def to_dict(self):
        if self.result is None:
            result = 'None'
        elif hasattr(self.result, '_repr_html_'):
            result = self.result._repr_html_()
        else:
            result = str(self.result)
        return {
            "id": self.id,
            "status": self.status,
            "code": self.code,
            "result": html_escape(result),
            "is_eval": self.is_eval,
            "stdout": html_escape(self.stdout),
            "stderr": html_escape(self.stderr),
        }

    def to_json(self, *args, **kwargs):
        import json
        return json.dumps(self.to_dict(*args, **kwargs))


def html_escape(s):
    if s is None:
        return ''
    return (s
        .replace(' ', '&nbsp;')
        .replace('\t', 4*'&nbsp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('\n', '<br/>\n')
    )


@contextlib.contextmanager
def catch_output(stdout=None, stderr=None):
    oldout = sys.stdout
    olderr = sys.stderr
    try:
        if stdout is None:
            stdout = io.StringIO()
        if stderr is None:
            stderr = io.StringIO()
        sys.stdout = stdout
        sys.stderr = stderr
        yield stdout, stderr
    finally:
        sys.stdout = oldout
        sys.stderr = olderr


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.post('/', post_request_handler),
        web.get('/', get_webpage_handler),
        web.get(r'/{request_id:\d+}', get_request_handler),
        web.get('/websocket', websocket_handler),
    ])

    web.run_app(app)
