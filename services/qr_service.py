import qrcode
import json
import os
from flask import current_app

def generate_qr_code(equipment):
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    qr_data = f"{base_url}/equipment/{equipment.id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    filename = f"{equipment.code}.png"
    filepath = os.path.join('static', 'qr', filename)
    os.makedirs('static/qr', exist_ok=True)
    img.save(filepath)

    return f"/static/qr/{filename}"