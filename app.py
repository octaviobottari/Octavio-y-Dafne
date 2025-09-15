from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
import pytz
from werkzeug.utils import secure_filename
import logging
import json

app = Flask(__name__)

# Configure PostgreSQL database (set DATABASE_URL in Render environment variables)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Database Models
class Item(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    link = db.Column(db.String, nullable=False)
    image = db.Column(db.String, nullable=False)
    category = db.Column(db.String, nullable=False)

class Reservation(db.Model):
    id = db.Column(db.String, primary_key=True)
    item_id = db.Column(db.String, db.ForeignKey('item.id'), nullable=False)
    name = db.Column(db.String, nullable=False)
    contact = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=False)

class Category(db.Model):
    name = db.Column(db.String, primary_key=True)

# Initialize database
with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_data():
    items = {item.id: {
        "name": item.name, "description": item.description,
        "link": item.link, "image": item.image, "category": item.category
    } for item in Item.query.all()}
    reservations = {res.item_id: {
        "name": res.name, "contact": res.contact, "date": res.date
    } for res in Reservation.query.all()}
    categories = [cat.name for cat in Category.query.all()]
    return {"items": items, "reservations": reservations, "categories": categories}

def save_item(item_data):
    item = Item(**item_data)
    db.session.add(item)
    if item_data["category"] and item_data["category"] not in [cat.name for cat in Category.query.all()]:
        db.session.add(Category(name=item_data["category"]))
    db.session.commit()

def save_reservation(res_data):
    reservation = Reservation(**res_data)
    db.session.add(reservation)
    db.session.commit()

@app.route("/")
def index():
    data = load_data()
    return render_template("index.html", items=data["items"], reservations=data["reservations"])

@app.route("/nuestra-historia")
def historia():
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

@app.route("/admin-lista")
def admin_lista():
    data = load_data()
    categories = {}
    for item_id, item in data["items"].items():
        category = item.get("category", "Sin Categoría")
        if category not in categories:
            categories[category] = {}
        categories[category][item_id] = item
    return render_template("admin-lista.html", categories=categories, reservations=data["reservations"])

@app.route("/api/items", methods=["POST"])
def add_item():
    name = request.form.get("name")
    description = request.form.get("description")
    link = request.form.get("link")
    category = request.form.get("category")
    image = request.files.get("image")

    # Handle new category from form
    if category == "new":
        category = request.form.get("new_category")
        if not category:
            return jsonify({"error": "New category name is required"}), 400

    if not all([name, link, category, image]):
        return jsonify({"error": "Missing required fields"}), 400

    if not allowed_file(image.filename):
        return jsonify({"error": "Invalid image format. Use PNG, JPG, JPEG, GIF, or WEBP."}), 400

    item_id = str(Item.query.count())
    filename = secure_filename(image.filename)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{item_id}_{filename}")
    try:
        image.save(image_path)
        logging.info(f"Image saved: {image_path}")
    except Exception as e:
        logging.error(f"Error saving image: {str(e)}")
        return jsonify({"error": "Failed to save image"}), 500

    save_item({
        "id": item_id, "name": name, "description": description,
        "link": link, "image": f"/{image_path}", "category": category
    })
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

    if Reservation.query.filter_by(item_id=str(item_id)).first():
        return jsonify({"error": "Item already reserved"}), 400

    argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
    reservation_time = datetime.now(argentina_tz).strftime("%d/%m/%Y %H:%M")

    save_reservation({
        "id": str(Reservation.query.count()), "item_id": str(item_id),
        "name": name, "contact": contact, "date": reservation_time
    })
    return jsonify({"success": True, "reservations": load_data()["reservations"]})

# Temporary endpoint to download reservations.json for backup
DATA_FILE = "reservations.json"
@app.route("/download-reservations")
def download_reservations():
    if os.path.exists(DATA_FILE):
        return send_file(DATA_FILE, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

# Temporary endpoint to migrate reservations.json to PostgreSQL
@app.route("/migrate-data")
def migrate_data():
    try:
        data = json.load(open(DATA_FILE))
        for item_id, item in data["items"].items():
            db.session.add(Item(
                id=item_id, name=item["name"], description=item["description"],
                link=item["link"], image=item["image"], category=item["category"]
            ))
            if item["category"] and item["category"] not in [cat.name for cat in Category.query.all()]:
                db.session.add(Category(name=item["category"]))
        db.session.commit()
        return jsonify({"success": "Data migrated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)