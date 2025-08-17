from flask import Flask
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

app = Flask(__name__)

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

@app.route('/')
def index():
    return "Katana-AI Metrics Server"

def main():
    print("--- Katana-AI API Server (Metrics) ---")
    print("Running on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
