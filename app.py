from flask import Flask, render_template, request
import json
import pandas as pd
import os
import qrcode
import base64
from io import BytesIO

app = Flask(__name__)

def load_guests():
    with open("guests.json") as f:
        return json.load(f)

def generate_qr(data):
    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=2
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name").strip().lower()
        guests = load_guests()

        for guest in guests:
            if guest["name"].lower() == name:
                return render_template("result.html", guest=guest)

        return render_template("result.html", guest=None)

    return render_template("index.html")


# Optional: QR-based lookup (BEST UX)
@app.route("/guest/<guest_id>")
def guest_lookup(guest_id):
    guests = load_guests()

    for guest in guests:
        if guest["id"] == guest_id:
            return render_template("result.html", guest=guest)

    return render_template("result.html", guest=None)

@app.route("/search")
def search():
    query = request.args.get("q", "").lower()
    guests = load_guests()

    results = []

    for guest in guests:
        if query in guest["name"].lower():
            results.append({
                "name": guest["name"],
                "id": guest["id"]
            })

    return {"results": results[:5]}  # limit to 5 suggestions

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.args.get("key") != "secret123":
        return "Unauthorized", 403

    if request.method == "POST":
        file = request.files.get("file")

        if not file:
            return "No file uploaded", 400

        # Save temp file
        filepath = os.path.join("uploads", file.filename)
        os.makedirs("uploads", exist_ok=True)
        file.save(filepath)

        # Read Excel
        # df = pd.read_excel(filepath)
        df = pd.read_excel(filepath, engine="openpyxl")

        # Validate columns
        df.columns = df.columns.str.lower()

        if "name" not in df.columns or "table" not in df.columns:
            return "Excel must contain 'name' and 'table' columns", 400

        guests = []

        for idx, row in df.iterrows():
            guests.append({
                "id": str(idx + 1),
                "name": str(row["name"]).strip(),
                "table": str(row["table"]).strip()
            })

        # Save to JSON
        with open("guests.json", "w") as f:
            import json
            json.dump(guests, f, indent=2)

        return "Upload successful! Guests updated."

    return '''
    <h2>Upload Guest List</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" accept=".xlsx" required>
        <button type="submit">Upload</button>
    </form>
    '''

@app.route("/cards")
def all_cards():
    guests = load_guests()
    return render_template("cards.html", guests=guests)

@app.route("/card/<guest_id>")
def printable_card(guest_id):
    guests = load_guests()

    for guest in guests:
        if guest["id"] == guest_id:
            qr_data = f"{request.host_url}guest/{guest_id}"
            qr_img = generate_qr(qr_data)
            print(guest)
            return render_template(
                "card.html",
                guest=guest,
                qr=qr_img
            )

    return "Guest not found", 404

if __name__ == "__main__":
    app.run(debug=True)