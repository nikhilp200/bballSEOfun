# my-flask-app/my-flask-app/README.md

# My Flask App

This is a basic Flask application to practice Python web development skills.

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   ```

2. Navigate to the project directory:
   ```
   cd my-flask-app
   ```

3. Create a virtual environment:
   ```
   python -m venv venv
   ```

4. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

5. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

To run the Flask application, use the following command:
```
flask run
```

Make sure to set the `FLASK_APP` environment variable to `app`:
- On Windows:
  ```
  set FLASK_APP=app
  ```
- On macOS/Linux:
  ```
  export FLASK_APP=app
  ```

## Accessing the Application

Once the application is running, you can access it at `http://127.0.0.1:5000/`.

## License

This project is licensed under the MIT License.