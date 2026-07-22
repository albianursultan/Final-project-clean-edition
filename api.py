import requests
import csv , os

from flask import Flask, request, jsonify, render_template,send_from_directory
from flask_cors import CORS
from datetime import datetime

import mysql.connector

app = Flask(__name__)
CORS(app)


def get_db():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        database="ptl_database"
    )


@app.route('/<path:filename>')
def serve_asset(filename):
    return send_from_directory('static', filename)

@app.route ('/')
def dashboard():
    return render_template('dashboard_new_mirror_map.html')
    

# ===== NEW: list ALL kabinets (dashboard pakai ini buat tampilkan stok) =====
@app.route('/kabinet', methods=['GET'])
def get_all_kabinet():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM kabinet")
    results = cursor.fetchall()
    db.close()
    return jsonify(results)   # -> [{"kabinet_id":"A1-1","quantity":50,...}, ...]


# ----- read one kabinet -----
@app.route('/kabinet/<kabinet_id>', methods=['GET'])
def get_kabinet(kabinet_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM kabinet WHERE kabinet_id = %s", (kabinet_id,))
    result = cursor.fetchone()
    db.close()
    return jsonify(result)


# ----- adjust one kabinet by delta (Put-Away = +, Picking = -) -----
@app.route('/kabinet/<kabinet_id>/adjust', methods=['PUT'])
def adjust_quantity(kabinet_id):
    data = request.json
    qty = int(data.get('qty', 0))
    order_type = data.get('order_type', 'Put-Away')
    delta = qty if 'put' in order_type.lower() else -qty

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE kabinet SET quantity = GREATEST(0, quantity + %s) WHERE kabinet_id = %s",
        (delta, kabinet_id))
    db.commit()
    rows = cursor.rowcount
    db.close()
    if rows == 0:
        return jsonify({"status": "error", "msg": f"{kabinet_id} not found"}), 404
    return jsonify({"status": "ok", "kabinet_id": kabinet_id, "delta": delta})


# ===== NEW: bulk update for a whole order (dashboard pakai ini saat update) =====
# Body: { "order_type": "Put-Away", "items": [{"kabinet_id":"A1-1","qty":2}, ...] }
@app.route('/transaksi-bulk', methods=['POST'])
def transaksi_bulk():
    data = request.get_json(force=True, silent=True)
    if not data or 'items' not in data:
        return jsonify({"error": "Body harus berisi 'items'"}), 400

    order_type = data.get('order_type', 'Put-Away')
    is_putaway = 'put' in order_type.lower()
    items = data['items']

    db = get_db()
    cursor = db.cursor()
    try:
        updated = []
        for it in items:
            kab = it['kabinet_id']
            qty = int(it['qty'])

            # pastikan kabinet ada & cek stok untuk Picking
            cursor.execute("SELECT quantity FROM kabinet WHERE kabinet_id = %s", (kab,))
            row = cursor.fetchone()
            if row is None:
                db.rollback()
                return jsonify({"error": f"Kabinet {kab} tidak ditemukan"}), 404

            current = row[0]
            if not is_putaway and qty > current:
                db.rollback()
                return jsonify({"error": f"Stok {kab} tidak cukup (ada {current}, diminta {qty})"}), 400

            delta = qty if is_putaway else -qty
            cursor.execute(
                "UPDATE kabinet SET quantity = quantity + %s WHERE kabinet_id = %s",
                (delta, kab))
            updated.append({"kabinet_id": kab, "new_quantity": current + delta})

        db.commit()
        return jsonify({"status": "ok", "updated": updated})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ===== RELAY ke AMR (hindari CORS: browser -> api.py -> robot) =====
AMR_BASE = "http://192.168.0.100:5000"   # IP robot partner

@app.route('/amr/go_to_rack', methods=['POST'])
def amr_go_to_rack():
    try:
        r = requests.post(f"{AMR_BASE}/go_to_rack", json=request.json, timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 502

@app.route('/amr/status', methods=['GET'])
def amr_status():
    try:
        r = requests.get(f"{AMR_BASE}/status", timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 502

@app.route('/amr/cancel', methods=['POST'])
def amr_cancel():
    try:
        r = requests.post(f"{AMR_BASE}/cancel", timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 502

CSV_LOG = "log_latensi.csv"

@app.route('/log-latensi', methods=['POST'])
def log_latensi():
    data = request.json or {}
    row = {
        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "order_id":    data.get("order_id", ""),
        "rack_id":     data.get("rack_id", ""),
        "order_type":  data.get("order_type", ""),
        "uplink_ms":   data.get("uplink_ms", ""),
        "downlink_ms": data.get("downlink_ms", "")
    }
    file_baru = not os.path.exists(CSV_LOG)            # header ditulis sekali saja
    with open(CSV_LOG, "a", newline="", encoding="utf-8") as f:   # "a" = append, tidak menimpa
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if file_baru:
            writer.writeheader()
        writer.writerow(row)
    return jsonify({"status": "ok", "saved": row})

CSV_SYNC = "log_sync_stok.csv"

@app.route('/log-sync', methods=['POST'])
def log_sync():
    data = request.json or {}
    row = {
        "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "order_id":   data.get("order_id", ""),
        "rack_id":    data.get("rack_id", ""),
        "order_type": data.get("order_type", ""),
        "sync_ms":    data.get("sync_ms", "")
    }
    file_baru = not os.path.exists(CSV_SYNC)
    with open(CSV_SYNC, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if file_baru:
            w.writeheader()
        w.writerow(row)
    return jsonify({"status": "ok", "saved": row})

@app.route('/amr/follow_waypoints', methods=['POST'])
def amr_follow_waypoints():
    try:
        r = requests.post(f"{AMR_BASE}/follow_waypoints", json=request.json, timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 502

CSV_RAK = "log_rak.csv"

@app.route('/lapor-lengkap', methods=['POST'])
def lapor_lengkap():
    d = request.json or {}
    rack_id    = d.get('rack_id')
    order_id   = d.get('order_id', '')
    order_type = d.get('order_type', '')
    qty        = int(d.get('req_qty') or 0)

    db = get_db()
    cur = db.cursor(dictionary=True)

    # --- baca stok SEBELUM ---
    cur.execute("SELECT quantity FROM kabinet WHERE kabinet_id=%s", (rack_id,))
    row = cur.fetchone()
    stok_sebelum = row['quantity'] if row else None

    stok_sesudah = None
    stok_diharapkan = None
    sukses = False

    if stok_sebelum is not None:
        # Put-Away = tambah, Picking = kurang
        if 'put' in order_type.lower():
            stok_diharapkan = stok_sebelum + qty
        else:
            stok_diharapkan = stok_sebelum - qty
        try:
            cur2 = db.cursor()
            cur2.execute("UPDATE kabinet SET quantity=%s WHERE kabinet_id=%s",
                         (stok_diharapkan, rack_id))
            db.commit()
            # --- baca stok SESUDAH ---
            cur.execute("SELECT quantity FROM kabinet WHERE kabinet_id=%s", (rack_id,))
            stok_sesudah = cur.fetchone()['quantity']
            sukses = True
        except Exception as e:
            print("UPDATE gagal:", e)
            sukses = False
    db.close()

    # sinkronisasi benar = stok sesudah sesuai yang diharapkan
    sinkron_benar = (stok_sesudah is not None and stok_sesudah == stok_diharapkan)
    berhasil = sukses and sinkron_benar

    row_log = {
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "order_id":        order_id,
        "rack_id":         rack_id,
        "order_type":      order_type,
        "req_qty":         qty,
        "stok_sebelum":    stok_sebelum,
        "stok_sesudah":    stok_sesudah,
        "stok_diharapkan": stok_diharapkan,
        "sinkron_benar":   "YA" if sinkron_benar else "TIDAK",
        "sukses":          "BERHASIL" if berhasil else "GAGAL",
        "d_tunggu":        d.get('d_tunggu', ''),
        "d_ambil":         d.get('d_ambil', ''),
        "d_konfirm":       d.get('d_konfirm', ''),
        "d_total":         d.get('d_total', '')
    }
    file_baru = not os.path.exists(CSV_RAK)
    with open(CSV_RAK, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row_log.keys()))
        if file_baru:
            w.writeheader()
        w.writerow(row_log)
    return jsonify({"status": "ok", "log": row_log})
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)