from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

DATA_FILE = "reservations.json"

# Sample list of items
ITEMS = {
    0: {"name": "Juego de Platos", "link": "https://www.mercadolibre.com.ar/juego-de-vajilla-bormioli-rocco-parma-de-18-piezas-blanco/p/MLA41380341#polycard_client=search-nordic&wid=MLA1929005134&sid=search&searchVariation=MLA41380341&position=19&search_layout=grid&type=product&tracking_id=6cfa5b3a-9896-425a-a0ad-e2044c3c0a8f", "image": "https://http2.mlstatic.com/D_NQ_NP_2X_813842-MLA79709616883_102024-F.webp"},
    1: {"name": "Set de Toallas", "link": "https://articulo.mercadolibre.com.ar/MLA-1122357828-set-de-toalla-y-toallon-100-algodon-_JM?searchVariation=176819319491#polycard_client=search-nordic&searchVariation=176819319491&position=26&search_layout=grid&type=item&tracking_id=90c72cc3-8bed-4f51-ad57-edd9ac3da2da", "image": "https://http2.mlstatic.com/D_NQ_NP_2X_879872-MLA54037681349_022023-F.webp"},
    2: {"name": "Cubiertos", "link": "https://www.mercadolibre.com.ar/set-de-cubiertos-alpina-home-box-24-piezas-acero-inoxidable-color-plateado/p/MLA42327209?pdp_filters=item_id:MLA1458768257#is_advertising=true&searchVariation=MLA42327209&position=1&search_layout=grid&type=pad&tracking_id=19fc771a-aeea-451e-9966-8f90f60102bd&is_advertising=true&ad_domain=VQCATCORE_LST&ad_position=1&ad_click_id=YmNmYTQxM2YtY2JhNC00YjAyLWI5N2YtZjY2OWI3ODc4M2Iw", "image": "https://http2.mlstatic.com/D_NQ_NP_2X_917918-MLA80234657551_102024-F.webp"},
    3: {"name": "Cubiertos", "link": "https://www.mercadolibre.com.ar/set-de-cubiertos-alpina-home-box-24-piezas-acero-inoxidable-color-plateado/p/MLA42327209?pdp_filters=item_id:MLA1458768257#is_advertising=true&searchVariation=MLA42327209&position=1&search_layout=grid&type=pad&tracking_id=19fc771a-aeea-451e-9966-8f90f60102bd&is_advertising=true&ad_domain=VQCATCORE_LST&ad_position=1&ad_click_id=YmNmYTQxM2YtY2JhNC00YjAyLWI5N2YtZjY2OWI3ODc4M2Iw", "image": "https://http2.mlstatic.com/D_NQ_NP_2X_917918-MLA80234657551_102024-F.webp"}
}

def load_reservations():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    return {}

def save_reservations(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

@app.route("/")
def index():
    """Render the main page with items and reservations."""
    reservations = load_reservations()
    return render_template("index.html", items=ITEMS, reservations=reservations)

@app.route("/gallery")
def gallery():
    """Render the gallery page."""
    return render_template("gallery.html")

@app.route("/lista-de-cosas")
def lista_de_cosas():
    """Render the list of items and reservations."""
    reservations = load_reservations()
    return render_template("lista-de-cosas.html", items=ITEMS, reservations=reservations)

@app.route("/api/reservations", methods=["GET"])
def get_reservations():
    """Return all reservations."""
    reservations = load_reservations()
    return jsonify(reservations)

@app.route("/api/reservations", methods=["POST"])
def add_reservation():
    """Add a new reservation."""
    data = request.json
    item_id = data.get("item_id")
    name = data.get("name")

    if item_id is None or not name:
        return jsonify({"error": "Invalid data"}), 400

    reservations = load_reservations()

    if str(item_id) in reservations:
        return jsonify({"error": "Item already reserved"}), 400

    reservations[str(item_id)] = name
    save_reservations(reservations)

    return jsonify({"success": True, "reservations": reservations})

if __name__ == "__main__":
    app.run(debug=True)
