from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import subprocess
import urllib.parse

class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/controller_webapp.html'
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/execute':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            command = data.get('command')

            if not command:
                self.send_error(400, "No command provided")
                return

            try:
                result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
                response = {"output": result.stdout, "error": result.stderr}
            except subprocess.CalledProcessError as e:
                response = {"error": str(e), "output": e.output}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")
if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, CustomHandler)
    print('Server running on port 8000...')
    httpd.serve_forever()