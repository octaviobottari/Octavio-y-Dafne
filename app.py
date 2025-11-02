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

@app.route("/admin-gestionar")
def admin_gestionar():
    data = load_data()
    # Crear lista plana de todos los items para facilitar la gestión
    all_items = []
    for item_id, item in data["items"].items():
        item_with_id = item.copy()
        item_with_id['id'] = item_id
        item_with_id['reserved'] = item_id in data["reservations"]
        if item_with_id['reserved']:
            item_with_id['reserved_by'] = data["reservations"][item_id]['name']
            item_with_id['reserved_contact'] = data["reservations"][item_id]['contact']
            item_with_id['reserved_date'] = data["reservations"][item_id]['date']
        all_items.append(item_with_id)
    
    return render_template("admin-gestionar.html", items=all_items, categories=data["categories"])

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
        item_count = Item.query.count()
        item_id = str(item_count + 1)
        
        # Sanitizar nombre de archivo
        original_filename = secure_filename(image.filename)
        file_ext = os.path.splitext(original_filename)[1].lower()
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

@app.route("/api/items/<item_id>", methods=["PUT"])
def update_item(item_id):
    try:
        item = Item.query.get(item_id)
        if not item:
            return jsonify({"error": "Item no encontrado"}), 404

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        link = request.form.get("link", "").strip()
        category = request.form.get("category", "").strip()
        image = request.files.get("image")

        # Validaciones
        if not all([name, link, category]):
            return jsonify({"error": "Faltan campos requeridos: nombre, link y categoría"}), 400

        # Actualizar campos básicos
        item.name = name
        item.description = description
        item.link = link
        item.category = category

        # Manejar nueva imagen si se proporciona
        if image and image.filename != '':
            if not allowed_file(image.filename):
                return jsonify({"error": "Formato de imagen no válido. Use PNG, JPG, JPEG, GIF o WEBP."}), 400

            # Eliminar imagen anterior si existe
            old_image_path = item.image.lstrip('/')
            if os.path.exists(old_image_path):
                try:
                    os.remove(old_image_path)
                except Exception as e:
                    logging.warning(f"No se pudo eliminar la imagen anterior: {str(e)}")

            # Guardar nueva imagen
            original_filename = secure_filename(image.filename)
            file_ext = os.path.splitext(original_filename)[1].lower()
            filename = f"{item_id}{file_ext}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            image.save(image_path)
            item.image = f"/static/uploads/{filename}"
            logging.info(f"Nueva imagen guardada: {image_path}")

        # Actualizar categoría si es nueva
        if category and category not in [cat.name for cat in Category.query.all()]:
            db.session.add(Category(name=category))

        db.session.commit()
        
        return jsonify({"success": True, "message": "Item actualizado correctamente"})
        
    except Exception as e:
        logging.error(f"Error en update_item: {str(e)}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

@app.route("/api/items/<item_id>", methods=["DELETE"])
def delete_item(item_id):
    try:
        item = Item.query.get(item_id)
        if not item:
            return jsonify({"error": "Item no encontrado"}), 404

        # Eliminar reserva asociada si existe
        reservation = Reservation.query.filter_by(item_id=item_id).first()
        if reservation:
            db.session.delete(reservation)

        # Eliminar imagen del filesystem si existe
        image_path = item.image.lstrip('/')
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                logging.warning(f"No se pudo eliminar la imagen: {str(e)}")

        # Eliminar item
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Item eliminado correctamente"})
        
    except Exception as e:
        logging.error(f"Error en delete_item: {str(e)}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

@app.route("/api/reservations/<item_id>", methods=["DELETE"])
def delete_reservation(item_id):
    try:
        reservation = Reservation.query.filter_by(item_id=item_id).first()
        if not reservation:
            return jsonify({"error": "Reserva no encontrada"}), 404

        db.session.delete(reservation)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Reserva eliminada correctamente"})
        
    except Exception as e:
        logging.error(f"Error en delete_reservation: {str(e)}")
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

        reservation_count = Reservation.query.count()
        save_reservation({
            "id": str(reservation_count + 1), 
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

# Endpoint para reparar imágenes faltantes
@app.route("/api/fix-images", methods=["POST"])
def fix_images():
    """Endpoint para reparar rutas de imágenes en la base de datos"""
    try:
        items = Item.query.all()
        fixed_count = 0
        
        for item in items:
            # Verificar si la imagen existe
            image_path = item.image.lstrip('/')
            if not os.path.exists(image_path):
                # Buscar archivos que puedan corresponder a este item
                upload_dir = app.config['UPLOAD_FOLDER']
                possible_files = []
                
                for filename in os.listdir(upload_dir):
                    if filename.startswith(item.id + '_') or filename.startswith(item.id + '.'):
                        possible_files.append(filename)
                
                if possible_files:
                    # Usar el primer archivo encontrado
                    new_filename = possible_files[0]
                    item.image = f"/static/uploads/{new_filename}"
                    fixed_count += 1
                    logging.info(f"Imagen reparada para item {item.id}: {new_filename}")
        
        if fixed_count > 0:
            db.session.commit()
            return jsonify({"success": True, "fixed_count": fixed_count})
        else:
            return jsonify({"success": True, "message": "No se encontraron imágenes para reparar"})
            
    except Exception as e:
        logging.error(f"Error en fix_images: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Endpoint para listar archivos en uploads (para debugging)
@app.route("/api/debug-files")
def debug_files():
    """Endpoint para ver qué archivos existen en el directorio de uploads"""
    try:
        upload_dir = app.config['UPLOAD_FOLDER']
        files = []
        if os.path.exists(upload_dir):
            files = os.listdir(upload_dir)
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            migrated_count = 0
            
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
                    migrated_count += 1
            
            db.session.commit()
            return jsonify({"success": f"Data migrated successfully. {migrated_count} items migrated."})
        else:
            return jsonify({"error": "Data file not found"}), 404
    except Exception as e:
        logging.error(f"Error en migrate_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
