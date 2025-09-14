from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
import pytz
from werkzeug.utils import secure_filename

app = Flask(__name__)

DATA_FILE = "reservations.json"
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding='utf-8') as file:
            return json.load(file)
    return {"items": {}, "reservations": {}, "categories": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False)

@app.route("/")
def index():
    data = load_data()
    return render_template("index.html", items=data["items"], reservations=data["reservations"])

@app.route("/nuestra-historia")
def gallery():
    return render_template("nuestra-historia.html")

@app.route("/lista-de-regalos")
def lista_de_regalos():
    data = load_data()
    categories = {}
    for item_id, item in data["items"].items():
        category = item.get("category", "Sin Categoría")
        if category not in categories:
            categories[category] = {}
        categories[category][item_id] = item
    return render_template("lista-de-regalos.html", categories=categories, reservations=data["reservations"])

@app.route("/lista-crear")
def lista_crear():
    data = load_data()
    return render_template("lista-crear-cosas.html", categories=data["categories"])

@app.route("/api/items", methods=["POST"])
def add_item():
    name = request.form.get("name")
    description = request.form.get("description")
    link = request.form.get("link")
    category = request.form.get("category")
    image = request.files.get("image")

    if not all([name, link, category, image]):
        return jsonify({"error": "Missing required fields"}), 400

    if not allowed_file(image.filename):
        return jsonify({"error": "Invalid image format. Use PNG, JPG, JPEG, or GIF."}), 400

    data_store = load_data()
    item_id = str(len(data_store["items"]))
    filename = secure_filename(image.filename)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{item_id}_{filename}")
    image.save(image_path)

    data_store["items"][item_id] = {
        "name": name,
        "description": description,
        "link": link,
        "image": f"/{image_path}",
        "category": category
    }
    if category not in data_store["categories"]:
        data_store["categories"].append(category)
    save_data(data_store)
    return jsonify({"success": True, "item_id": item_id})

@app.route("/api/reservations", methods=["GET"])
def get_reservations():
    data = load_data()
    return jsonify(data["reservations"])

@app.route("/api/reservations", methods=["POST"])
def add_reservation():
    data = request.json
    item_id = data.get("item_id")
    name = data.get("name")
    contact = data.get("contact")

    if item_id is None or not name or not contact:
        return jsonify({"error": "Invalid data: name and contact are required"}), 400

    data_store = load_data()
    if str(item_id) in data_store["reservations"]:
        return jsonify({"error": "Item already reserved"}), 400

    argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
    reservation_time = datetime.now(argentina_tz).strftime("%d/%m/%Y %H:%M")

    data_store["reservations"][str(item_id)] = {
        "name": name,
        "contact": contact,
        "date": reservation_time
    }
    save_data(data_store)
    return jsonify({"success": True, "reservations": data_store["reservations"]})

if __name__ == "__main__":
    app.run(debug=True)