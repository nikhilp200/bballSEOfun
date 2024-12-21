from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    with app.app_context():
        from .routes import init_routes
        init_routes(app)  # Ensure routes are imported correctly
        return app