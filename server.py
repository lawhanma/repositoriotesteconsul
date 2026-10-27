#!/usr/bin/env python3
"""
Servidor simples de consulta CPF - Athenas Buscas
API Key fica apenas no backend (variável de ambiente ou arquivo .env)
"""

import http.server
import socketserver
import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Carrega .env manualmente (sem dependência)
def load_env():
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())

load_env()

API_KEY = os.environ.get('ATHENAS_API_KEY', '')
PORT = int(os.environ.get('PORT', 3000))
PUBLIC_DIR = Path(__file__).parent / 'public'

if not API_KEY:
    print('ERRO: ATHENAS_API_KEY não definida. Crie o arquivo .env')
    exit(1)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            self._json_response(200, {'status': 'ok', 'message': 'Servidor de consulta CPF online'})
            return
        # Serve arquivos estáticos normalmente
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/consulta-cpf':
            self._handle_consulta()
            return
        self.send_error(404, 'Not Found')

    def _handle_consulta(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode('utf-8'))
        except Exception:
            self._json_response(400, {'success': False, 'error': 'JSON inválido'})
            return

        cpf = data.get('cpf', '')
        cpf_limpo = re.sub(r'\D', '', str(cpf))

        if len(cpf_limpo) != 11:
            self._json_response(400, {'success': False, 'error': 'CPF deve conter exatamente 11 dígitos'})
            return

        url = f'https://api.athenasbuscas.com/api/ext/v1/cpf/{cpf_limpo}'
        req = urllib.request.Request(url, headers={
            'X-API-Key': API_KEY,
            'Accept': 'application/json',
            'User-Agent': 'CPF-Consulta/1.0'
        })

        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                raw = resp.read().decode('utf-8')
                result = json.loads(raw)
                credits = resp.headers.get('X-Credits-Remaining')
                self._json_response(200, {
                    'success': True,
                    'data': result,
                    'creditsRemaining': credits
                })
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode('utf-8')
                err_data = json.loads(err_body)
                error_msg = err_data.get('error') or err_data.get('message') or f'Erro HTTP {e.code}'
            except Exception:
                error_msg = f'Erro HTTP {e.code}'
            credits = e.headers.get('X-Credits-Remaining') if e.headers else None
            self._json_response(e.code, {
                'success': False,
                'error': error_msg,
                'status': e.code,
                'creditsRemaining': credits
            })
        except urllib.error.URLError as e:
            self._json_response(500, {'success': False, 'error': f'Erro de conexão: {e.reason}'})
        except Exception as e:
            self._json_response(500, {'success': False, 'error': f'Erro interno: {str(e)}'})

    def _json_response(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f'[{self.log_date_time_string()}] {args[0]}')


if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('0.0.0.0', PORT), Handler) as httpd:
        print(f'✅ Servidor rodando em http://localhost:{PORT}')
        print(f'🔑 API Key carregada: {API_KEY[:10]}...')
        print('Pressione Ctrl+C para parar')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nServidor encerrado.')
