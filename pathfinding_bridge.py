"""
pathfinding_bridge.py  (versi waypoint / Mode B + Option B)
-----------------------------------------------------------
Jembatan antara DASHBOARD <-> CA* PATHFINDING lewat MQTT.

Kirim hasil rute ke  TA_PTL_bee/Order/<order_id>/route :
    {
      order_id,
      node_sequence,   # rak saja (checkpoint dashboard + stop AMR)
      full_path,       # SEMUA node dilewati, termasuk crossing (waypoint AMR)
      path_xy,         # koordinat full_path (garis biru dashboard)
      qty_per_node,
      route_display
    }
Taruh di folder yang sama dgn track_castar_calc.py & layout_track.py.
"""
import json
import paho.mqtt.client as mqtt

from track_castar_calc import (
    nodes, cooperative_a_star_graph, sorting_node, reservation_table
)

BROKER = "localhost"
PORT = 1883
TOPIC_ORDER = "TA_PTL_bee/Order/baru"


def hitung_rute(order):
    order_id = order["order_id"]
    order_type = order.get("order_type", "Put-Away")
    items = order.get("items", [])

    targets = []
    qty_per_node = {}
    for it in items:
        node = str(it["rak"]).split("-")[0]
        if node not in targets:          # FIX: rak benar-benar masuk daftar target
            targets.append(node)
        qty_per_node[node] = qty_per_node.get(node, 0) + int(it.get("qty", 0))

    start = "Base"
    end = "Stage" if order_type.lower().startswith("pick") else "Base"

    reservation_table.clear()
    rute_order = sorting_node(start, targets, end)

    # rangkai JALUR LENGKAP antar etape (termasuk crossing)
    rute_total = []
    t = 0
    for i in range(len(rute_order) - 1):
        etape, t = cooperative_a_star_graph(
            rute_order[i], rute_order[i + 1], t, "AGV-01")
        if not etape:
            return None
        rute_total.extend(etape if i == 0 else etape[1:])

    # buang node berturut-turut yang sama (kalau AGV "diam"/menunggu)
    full_path = []
    for n in rute_total:
        if not full_path or full_path[-1] != n:
            full_path.append(n)

    path_xy = [[nodes[n][0], nodes[n][1]] for n in full_path]
    rack_only = rute_order[1:-1]
    return {
        "order_id": order_id,
        "node_sequence": rack_only,
        "full_path": full_path,
        "qty_per_node": qty_per_node,
        "path_xy": path_xy,
        "route_display": " -> ".join(rute_order)
    }


def on_connect(client, userdata, flags, rc):
    print("Bridge tersambung ke broker (rc=%s)" % rc)
    client.subscribe(TOPIC_ORDER)
    print("Subscribe:", TOPIC_ORDER)


def on_message(client, userdata, msg):
    if msg.topic != TOPIC_ORDER:
        return
    try:
        order = json.loads(msg.payload.decode())
    except Exception as e:
        print("Order bukan JSON:", e)
        return

    print("\nOrder masuk:", order.get("order_id"), "| tipe:", order.get("order_type"))
    hasil = hitung_rute(order)
    if hasil is None:
        print("  Rute GAGAL dihitung (jalur terblokir).")
        return

    topic_out = "TA_PTL_bee/Order/%s/route" % hasil["order_id"]
    client.publish(topic_out, json.dumps(hasil))
    print("  Rute terkirim ->", topic_out)
    print("  ", hasil["route_display"])
    print("   full_path:", " -> ".join(hasil["full_path"]))


def main():
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except (AttributeError, TypeError):
        client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    print("PTL Pathfinding Bridge (waypoint) aktif...")
    client.loop_forever()


if __name__ == "__main__":
    main()