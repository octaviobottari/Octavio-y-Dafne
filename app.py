from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
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
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS and \
           filename != ''

def load_data():
    try:
        items = {}
        for item in Item.query.all():
            items[item.id] = {
                "name": item.name, 
                "description": item.description,
                "link": item.link, 
                "image": item.image, 
                "category": item.category
            }
            
        reservations = {}
        for res in Reservation.query.all():
            reservations[res.item_id] = {
                "name": res.name, 
                "contact": res.contact, 
                "date": res.date
            }
            
        categories = [cat.name for cat in Category.query.all()]
        
        return {"items": items, "reservations": reservations, "categories": categories}
    
    except Exception as e:
        logging.error(f"Error en load_data: {str(e)}")
        return {"items": {}, "reservations": {}, "categories": []}

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

@app.route("/static/uploads/<filename>")
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/api/items", methods=["POST"])
def add_item():
    try:
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        link = request.form.get("link", "").strip()
        category = request.form.get("category", "").strip()
        image = request.files.get("image")

        # Validaciones
        if not all([name, link, category]):
            return jsonify({"error": "Faltan campos requeridos: nombre, link y categoría"}), 400

        if not image or image.filename == '':
            return jsonify({"error": "No se seleccionó ninguna imagen"}), 400

        if not allowed_file(image.filename):
            return jsonify({"error": "Formato de imagen no válido. Use PNG, JPG, JPEG, GIF o WEBP."}), 400

        # Handle new category from form
        if category == "new":
            category = request.form.get("new_category", "").strip()
            if not category:
                return jsonify({"error": "El nombre de la nueva categoría es requerido"}), 400

        # Generar ID único
        item_id = str(Item.query.count() + 1)
        
        # Sanitizar nombre de archivo y mantener extensión
        file_ext = os.path.splitext(image.filename)[1].lower()
        filename = f"{item_id}{file_ext}"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Asegurar que el directorio existe
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Guardar imagen
        image.save(image_path)
        logging.info(f"Imagen guardada exitosamente: {image_path}")

        # Guardar en base de datos con ruta relativa
        save_item({
            "id": item_id, 
            "name": name, 
            "description": description,
            "link": link, 
            "image": f"/static/uploads/{filename}",
            "category": category
        })
        
        return jsonify({"success": True, "item_id": item_id})
        
    except Exception as e:
        logging.error(f"Error en add_item: {str(e)}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

@app.route("/api/reservations", methods=["GET"])
def get_reservations():
    data = load_data()
    return jsonify(data["reservations"])

@app.route("/api/reservations", methods=["POST"])
def add_reservation():
    try:
        data = request.json
        item_id = data.get("item_id")
        name = data.get("name", "").strip()
        contact = data.get("contact", "").strip()

        if item_id is None or not name or not contact:
            return jsonify({"error": "Datos inválidos: nombre y contacto son requeridos"}), 400

        if Reservation.query.filter_by(item_id=str(item_id)).first():
            return jsonify({"error": "El ítem ya está reservado"}), 400

        argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        reservation_time = datetime.now(argentina_tz).strftime("%d/%m/%Y %H:%M")

        save_reservation({
            "id": str(Reservation.query.count() + 1), 
            "item_id": str(item_id),
            "name": name, 
            "contact": contact, 
            "date": reservation_time
        })
        
        return jsonify({
            "success": True, 
            "reservations": load_data()["reservations"]
        })
        
    except Exception as e:
        logging.error(f"Error en add_reservation: {str(e)}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

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
        if os.path.exists(DATA_FILE):
            data = json.load(open(DATA_FILE))
            for item_id, item in data["items"].items():
                # Verificar si el ítem ya existe
                if not Item.query.get(item_id):
                    db.session.add(Item(
                        id=item_id, 
                        name=item["name"], 
                        description=item["description"],
                        link=item["link"], 
                        image=item["image"], 
                        category=item["category"]
                    ))
                    if item["category"] and item["category"] not in [cat.name for cat in Category.query.all()]:
                        db.session.add(Category(name=item["category"]))
            db.session.commit()
            return jsonify({"success": "Data migrated successfully"})
        else:
            return jsonify({"error": "Data file not found"}), 404
    except Exception as e:
        logging.error(f"Error en migrate_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
