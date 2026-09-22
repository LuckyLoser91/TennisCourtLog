# local_server.py
import os
import importlib.util
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

# 从 api/ 目录自动加载所有 handler
api_handlers = {}
API_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api')

for fname in sorted(os.listdir(API_DIR)):
    if not fname.endswith('.py') or fname.startswith('_'):
        continue
    route = '/api/' + fname[:-3]
    path = os.path.join(API_DIR, fname)
    try:
        spec = importlib.util.spec_from_file_location('api_' + fname[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, 'handler'):
            api_handlers[route] = mod.handler
            print(f'  ✓ loaded {route}')
        else:
            print(f'  ! {fname} has no handler class')
    except Exception as e:
        print(f'  ✗ failed to load {fname}: {e}')


class DevHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path in api_handlers:
            try:
                api_handlers[path].do_GET(self)
            except BrokenPipeError:
                pass
            except Exception as e:
                import traceback
                traceback.print_exc()
                try:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(('{"error": "%s"}' % str(e)).encode())
                except Exception:
                    pass
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        # 只打印 API 请求和错误，静态文件不打
        if '/api/' in (args[0] if args else ''):
            super().log_message(fmt, *args)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), DevHandler)
    print(f'\n🌐 Local dev server running:')
    print(f'   http://localhost:{port}/')
    print(f'   API routes ready: {sorted(api_handlers.keys())}')
    print(f'\n   Press Ctrl+C to stop.\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nBye.')