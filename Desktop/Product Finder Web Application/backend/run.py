from app import create_app
import os

app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    print("=" * 50)
    print("TechNest - Find Your Perfect Tech")
    print("=" * 50)
    print(f"Starting server at http://localhost:5000")
    print("Using MongoDB Database")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    app.run(debug=True, port=5000)
