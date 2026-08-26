# Flask Template

A minimal Flask project template with a blueprint-based structure, static assets, and a Jinja2 template, ready to be used as a starting point for new projects.

## Project Structure

```
flask_template/
├── main.py                  # Application entry point
├── endpoints/
│   └── index.py              # Index blueprint
├── templates/
│   └── index.html            # Index page template
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│   └── img/
│       └── favicon.ico
├── requirements.txt
└── .gitignore
```

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:

   ```bash
   python main.py
   ```

4. Open [http://localhost:5000](http://localhost:5000) in your browser.
