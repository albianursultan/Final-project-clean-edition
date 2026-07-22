import math
import heapq
import json
import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt

# ---------------------------------------------------------
# IMPORT DATA DROM layout_track
from layout_track import nodes, jalur_track

# ---------------------------------------------------------
# 2. Make Graph
# ---------------------------------------------------------

graph = {node: [] for node in nodes}
for u, v in jalur_track:
    graph[u].append(v)
    graph[v].append(u)

# ---------------------------------------------------------
# 3. Cooperative A* Code
# ---------------------------------------------------------
reservation_table = {}
edge_reservation = {}   # (frozenset({u,v}), t) -> agent_id  (anti tabrakan jalur/edge)
agent_speed = 0.2 # (0.5 m/s)

##deadlock zone
deadlock_zone={
    "A1": ["A2"], 
    "B1": ["B2"], 
    "C1": ["C2"]
}

no_parking_zone = ["X1_A", "X1_B", "X1_C", "X2_A", "X2_B", "X3_B", "X3_C"]
agent_tracker ={}

# Fungsi hitung jarak murni pake Euclidean (Garis Lurus antar koordinat)
def get_distance(n1, n2):
    x1, y1 = nodes[n1]
    x2, y2 = nodes[n2]
    return math.hypot(x1 - x2, y1 - y2)

def cooperative_a_star_graph(start, goal, start_time, agent_id):
    open_set = []
    heapq.heappush(open_set, (0, start, start_time))
    came_from = {}
    g_score = {(start, start_time): 0}
    
    while open_set:
        _, curr_node, curr_t = heapq.heappop(open_set)
        
        # Kalau Nyampe Tujuan
        if curr_node == goal:
            #chechking the 10 seconds ahead
            save_wait= True
            for t_cek in range(curr_t, curr_t + 11):
                if (curr_node, t_cek) in reservation_table:
                    save_wait=False
                    break
        #check gatenya juga misal A2, B2, C2
                if curr_node in deadlock_zone:
                    for gate  in deadlock_zone[curr_node]:
                        if (gate, t_cek) in reservation_table:
                            save_wait = False
                            break
                        
        #====IF AMAN=======
            if save_wait:
                # rekonstruksi path BESERTA waktu asli dari hasil search
                path_t = []
                curr = (curr_node, curr_t)
                while curr in came_from:
                    path_t.append(curr)
                    curr = came_from[curr]
                path_t.append((start, start_time))
                path_t.reverse()
                path = [n for n, _ in path_t]

                # Booking node + EDGE pakai waktu asli (anti-serobot & anti-tabrakan jalur)
                for i in range(len(path_t) - 1):
                    n_awal, t_awal = path_t[i]
                    n_tujuan, t_tujuan = path_t[i + 1]
                    reservation_table[(n_tujuan, t_tujuan)] = agent_id
                    if n_awal == n_tujuan:
                        reservation_table[(n_awal, t_awal)] = agent_id   # diam: kunci node selama tunggu
                    else:
                        edge = frozenset((n_awal, n_tujuan))             # kunci GARIS selama lewat
                        for tt in range(t_awal, t_tujuan + 1):
                            edge_reservation[(edge, tt)] = agent_id
                t_booking = path_t[-1][1]
                return path, t_booking

        # Cek Tetangga yang Terhubung Garis + Opsi Nunggu/Diam
        tetangga_tersedia = graph[curr_node] + [curr_node] 
        
        for neighbor in tetangga_tersedia:
            if neighbor == curr_node:
                if curr_node == no_parking_zone:
                    continue
                travel_time = 1 # Nunggu nambah 1 detik
            else:
                travel_time = math.ceil(get_distance(curr_node, neighbor) / agent_speed)
                # CEK EDGE: garis curr_node->neighbor harus bebas selama traversal
                edge = frozenset((curr_node, neighbor))
                blocked = False
                for tt in range(curr_t, curr_t + travel_time + 1):
                    if edge_reservation.get((edge, tt), agent_id) != agent_id:
                        blocked = True
                        break
                if blocked:
                    continue

            next_t = curr_t + travel_time
            
            # Algorithm Check, make sure the checkpoint is clear at present time (di detik tsb.)
            if (neighbor, next_t) not in reservation_table:
                # penalti gerak kecil: kalau harus menunda, lebih suka DIAM di node
                # daripada jalan-jalan bolak-balik (jiggle). Tidak mengubah waktu (booking pakai next_t).
                move_penalty = 0.0 if neighbor == curr_node else 0.001
                temp_g = g_score[(curr_node, curr_t)] + travel_time + move_penalty
                if (neighbor, next_t) not in g_score or temp_g < g_score[(neighbor, next_t)]:
                    g_score[(neighbor, next_t)] = temp_g
                    f_score = temp_g + get_distance(neighbor, goal)
                    heapq.heappush(open_set, (f_score, neighbor, next_t))
                    came_from[(neighbor, next_t)] = (curr_node, curr_t)
                    
    return None, start_time

def normal_a_star_graph(start, goal, start_time, agent_id):
    """
    Algoritma A* Konvensional (Normal A*).
    Mencari jalur terpendek tanpa memedulikan reservation_table milik agent lain.
    Sangat berguna untuk melihat efek 'blind multi-agent pathfinding' (potensi tabrakan tinggi).
    """
    open_set = []
    heapq.heappush(open_set, (0, start, start_time))
    came_from = {}
    g_score = {(start, start_time): 0}
    
    while open_set:
        _, curr_node, curr_t = heapq.heappop(open_set)
        
        # Jika sampai di tujuan etape
        if curr_node == goal:
            path_t = []
            curr = (curr_node, curr_t)
            while curr in came_from:
                path_t.append(curr)
                curr = came_from[curr]
            path_t.append((start, start_time))
            path_t.reverse()
            path = [n for n, _ in path_t]

            # Tetap lakukan booking setelah path ketemu!
            # Tujuannya agar reservation_table terisi dan GUI bisa mendeteksi 
            # overlaps/tabrakan di fungsi detect_traffic().
            for i in range(len(path_t) - 1):
                n_awal, t_awal = path_t[i]
                n_tujuan, t_tujuan = path_t[i + 1]
                reservation_table[(n_tujuan, t_tujuan)] = agent_id
                if n_awal == n_tujuan:
                    reservation_table[(n_awal, t_awal)] = agent_id   
                else:
                    edge = frozenset((n_awal, n_tujuan))             
                    for tt in range(t_awal, t_tujuan + 1):
                        edge_reservation[(edge, tt)] = agent_id
            t_booking = path_t[-1][1]
            return path, t_booking

        # Di Normal A*, agent hanya bergerak maju ke tetangga langsung tanpa opsi DIAM/WAIT di jalan
        for neighbor in graph[curr_node]:
            travel_time = math.ceil(get_distance(curr_node, neighbor) / agent_speed)
            next_t = curr_t + travel_time
            
            temp_g = g_score[(curr_node, curr_t)] + travel_time
            if (neighbor, next_t) not in g_score or temp_g < g_score[(neighbor, next_t)]:
                g_score[(neighbor, next_t)] = temp_g
                f_score = temp_g + get_distance(neighbor, goal)
                heapq.heappush(open_set, (f_score, neighbor, next_t))
                came_from[(neighbor, next_t)] = (curr_node, curr_t)
                    
    return None, start_time

# ---------------------------------------------------------
# Sort the node
# ---------------------------------------------------------
def sorting_node(start_node, target_nodes, end_node):
    # Kalau cuma disuruh dari Base langsung ke Stage tanpa mampir rak
    if not target_nodes:
        return [start_node, end_node]

    optimal_route = [start_node]
    current_node = start_node
    target_remaining = target_nodes.copy()

    print("\nNode Sorted")
    print(f"Input from User: {target_nodes}")

    while target_remaining:
        # Cari rak terdekat dari posisi Agent sekarang
        nearest_node= min(target_remaining, key=lambda x: get_distance(current_node, x))
        
        optimal_route.append(nearest_node)
        target_remaining.remove(nearest_node)
        current_node = nearest_node # Update posisi Agent

    # Terakhir, pastiin Agent balik ke titik akhir
    optimal_route.append(end_node)
    
    print(f"Sorted Node : {optimal_route[1:-1]}")
    return optimal_route
# ---------------------------------------------------------
# 4. VISUALIZE ROUTE 
# ---------------------------------------------------------
def visualize_route(rute_node_str, agent_id, sort_destination):
    fig, ax = plt.subplots(figsize=(8, 12))
    
    # Render Jalur Kosong
    for u, v in jalur_track:
        x_vals = [nodes[u][0], nodes[v][0]]
        y_vals = [nodes[u][1], nodes[v][1]]
        ax.plot(x_vals, y_vals, color="#797979", linewidth=2.5, linestyle='dashed', zorder=1)

    # Render Rute Merah si Agent
    rx, ry = [], []
    for n in rute_node_str:
        rx.append(nodes[n][0])
        ry.append(nodes[n][1])
    ax.plot(rx, ry, color="#ff1900", linewidth=6, solid_capstyle='round', zorder=2)

    # Render Titik
    for name, (x, y) in nodes.items():
        if name == "Base":
            ax.scatter(x, y, c='red', marker='s', s=200, zorder=4)
            ax.text(x, y-0.2, "BASE", ha='center', fontweight='bold', color='red')
        elif name == "Stage":
            ax.scatter(x, y, c='green', marker='s', s=200, zorder=4)
            ax.text(x, y-0.2, "STAGE", ha='center', fontweight='bold', color='green')
        elif name.startswith("X"): 
            ax.scatter(x, y, c='gray', s=50, zorder=3)
        else:
            ax.scatter(x, y, c='#1f77b4', s=180, edgecolors='white', zorder=4)
            ax.text(x, y+0.2, name, ha='center', fontweight='bold', fontsize=10)



    target_nodes = sort_destination[1:-1] 
    for i, node_name in enumerate(target_nodes):
        tx, ty = nodes[node_name]
        # made the orange circle
        ax.text(tx, ty, str(i + 1), color='white', ha='center', va='center', 
                fontsize=11, fontweight='bold', zorder=10, 
                bbox=dict(boxstyle='circle,pad=0.3', facecolor='darkorange', edgecolor='black', linewidth=1.5))

    ax.set_title(f"Visualisasi CA* [{agent_id}]\nRute: {' -> '.join(rute_order)}", fontweight='bold', pad=15, fontsize=14)
    ax.set_aspect('equal')
    ax.set_xlim(-2.5, 5.5); ax.set_ylim(-9.5, 2.0)
    ax.grid(True, linestyle=':', color='lightgray', zorder=0)
    plt.tight_layout()
    plt.show(block=False) 
    plt.pause(0.1)

def visualize_batch_routes(batch_data):
    fig, ax = plt.subplots(figsize=(8, 12))
    
    # 1. Render Jalur Kosong & Titik Node (Sama seperti sebelumnya)
    for u, v in jalur_track:
        x_vals = [nodes[u][0], nodes[v][0]]
        y_vals = [nodes[u][1], nodes[v][1]]
        ax.plot(x_vals, y_vals, color="#797979", linewidth=2.5, linestyle='dashed', zorder=1)

    for name, (x, y) in nodes.items():
        if name == "Base":
            ax.scatter(x, y, c='red', marker='s', s=200, zorder=4)
            ax.text(x, y-0.2, "BASE", ha='center', fontweight='bold', color='red')
        elif name == "Stage":
            ax.scatter(x, y, c='green', marker='s', s=200, zorder=4)
            ax.text(x, y-0.2, "STAGE", ha='center', fontweight='bold', color='green')
        elif name.startswith("X"): 
            ax.scatter(x, y, c='gray', s=50, zorder=3)
        else:
            ax.scatter(x, y, c='#1f77b4', s=180, edgecolors='white', zorder=4)
            ax.text(x, y+0.2, name, ha='center', fontweight='bold', fontsize=10)

    # 2. Render Rute Semua Agent dengan Warna Berbeda
    # Merah, Biru, Hijau, Ungu
    colors = ["#ff1900", "#0088ff", "#00cc00", "#ff00ff"] 
    
    for idx, data in enumerate(batch_data):
        agent_id = data['agent_id']
        rute_node_str = data['rute']
        sort_destination = data['targets']
        warna = colors[idx % len(colors)] # Otomatis ganti warna tiap Agent
        
        # Gambar Garis Rute (Pakai alpha=0.6 biar agak transparan & kelihatan kalau numpuk)
        rx, ry = [], []
        for n in rute_node_str:
            rx.append(nodes[n][0])
            ry.append(nodes[n][1])
        ax.plot(rx, ry, color=warna, linewidth=6, solid_capstyle='round', zorder=2, alpha=0.6, label=agent_id)

        # Gambar Angka Urutan Target
        target_nodes = sort_destination[1:-1] 
        for i, node_name in enumerate(target_nodes):
            tx, ty = nodes[node_name]
            # Geser label sedikit ke atas/bawah biar nggak tabrakan kalau 2 agent ke rak yang sama
            offset_y = 0.3 if idx % 2 == 1 else 0 
            ax.text(tx, ty + offset_y, str(i + 1), color='white', ha='center', va='center', 
                    fontsize=10, fontweight='bold', zorder=10, 
                    bbox=dict(boxstyle='circle,pad=0.3', facecolor=warna, edgecolor='black', linewidth=1.5))

    ax.set_title("Visualisasi Multi-Agent Cooperative A*", fontweight='bold', pad=15, fontsize=14)
    ax.set_aspect('equal')
    ax.set_xlim(-2.5, 5.5); ax.set_ylim(-9.5, 2.0)
    ax.grid(True, linestyle=':', color='lightgray', zorder=0)
    
    # Munculkan Legend (Keterangan Warna Agent)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.1), ncol=3)
    
    plt.tight_layout()
    plt.show(block=False) 
    plt.pause(0.1)


def print_reservation_table():
    print("\n" + "=" * 48)
    print("        TABEL RESERVASI (Reservation Table)")
    print("=" * 48)
    if not reservation_table:
        print("  (kosong - belum ada reservasi)")
        print("=" * 48 + "\n")
        return
    print(f"  {'Waktu(t)':<9}{'Node':<14}{'Agent'}")
    print("  " + "-" * 40)
    for (node, t), agent in sorted(reservation_table.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        print(f"  {t:<9}{node:<14}{agent}")
    print(f"\n  Total entri reservasi: {len(reservation_table)}")
    print("=" * 48 + "\n")


MQTT_BROKER = "192.168.0.101"
MQTT_PORT = 1883
MQTT_TOPIC = "TA_PTL/"
# ---------------------------------------------------------
# 5. DISPATCHER & JSON GENERATOR (Multi-Node)
# ---------------------------------------------------------
if __name__ == '__main__':
    print("=== SISTEM NAVIGASI WNS 1 (VIRTUAL TRACK) AKTIF ===")
    print("Contoh Perintah: Agent-1, Base, A4, B2, Stage")
    print("Ketik 'exit' untuk keluar.\n")

    current_server_time = 0 

    while True:
        print("\nOpsi Perintah:")
        print("1. Kirim AGV -> Format: Agent-ID, Target1, Target2 (Multi-order pisahkan dengan ';')")
        print("   Contoh: Agent-1, A1, A2 ; Agent-2, B3")
        print("2. Majuin Jam -> Format: maju <angka_detik> (Contoh: maju 10)")
        
        order = input(f"\n[Waktu Server: {current_server_time}s] > ")
        if order.lower() == 'exit': break
        
        # Fitur Mesin Waktu
        if order.lower().startswith('maju '):
            try:
                add_time = int(order.split(' ')[1])
                current_server_time += add_time
                print(f"Server time dimajuin {add_time} detik. Sekarang: t={current_server_time}s")
            except:
                print("❌ Format salah! Ketik 'maju 10'")
            continue
            
        try:
            # 🔥 FITUR BARU: BATCH DISPATCH (Pisahkan dengan titik koma)
            daftar_pesanan = [p.strip() for p in order.split(';') if p.strip()]
            batch_visual_data = []
            for pesanan in daftar_pesanan:
                print(f"\n--- Memproses: {pesanan} ---")
                data = [item.strip() for item in pesanan.split(',')]

                if len(data) < 2:
                    print(f"Format salah pada '{pesanan}'. Minimal: Agent-ID, Target1")
                    continue

                agent_id = data[0]
                node_targets = data[1:]
                node_start = "Base"
                node_end = "Base"

                if agent_id in agent_tracker:
                    waktu_berangkat = max(current_server_time, agent_tracker[agent_id]["finish_time"])
                    print(f"{agent_id} punya antrean! Berangkat dari Base pada t={waktu_berangkat}s")
                else:
                    waktu_berangkat = current_server_time

                if any(n not in nodes for n in node_targets):
                    print(f"Ada node yang salah ketik/tidak ada di layout pada {agent_id}!")
                    continue

                rute_order = sorting_node(node_start, node_targets, node_end)

                rute_total_agent = []
                temp_time = waktu_berangkat
                rute_sukses = True

                for i in range(len(rute_order) - 1):
                    node_awal_etape = rute_order[i]
                    node_tujuan_etape = rute_order[i + 1]

                    rute_etape, waktu_finish_etape = cooperative_a_star_graph(
                        start=node_awal_etape, goal=node_tujuan_etape,
                        start_time=temp_time, agent_id=agent_id
                    )

                    if rute_etape:
                        if i > 0:
                            rute_total_agent.extend(rute_etape[1:])
                        else:
                            rute_total_agent.extend(rute_etape)

                        temp_time = waktu_finish_etape

                        if i < len(rute_order) - 2:
                            waktu_awal_tunggu = temp_time
                            for t_tunggu in range(waktu_awal_tunggu, temp_time + 1):
                                reservation_table[(node_tujuan_etape, t_tunggu)] = agent_id
                                if node_tujuan_etape in deadlock_zone:
                                    for gerbang in deadlock_zone[node_tujuan_etape]:
                                        reservation_table[(gerbang, t_tunggu)] = agent_id
                    else:
                        print(f"Terblokir di etape {node_awal_etape} ke {node_tujuan_etape}!")
                        rute_sukses = False
                        break

                if rute_sukses:
                    batch_visual_data.append({
                        "agent_id": agent_id,
                        "rute": rute_total_agent,
                        "targets": rute_order
                    })
                    print(f"Route Found, {agent_id} akan tiba pada t={temp_time}s.")

                    collision_report = {}
                    for j in range(len(rute_total_agent) - 1):
                        if rute_total_agent[j] == rute_total_agent[j + 1]:
                            cn = rute_total_agent[j]
                            collision_report[cn] = collision_report.get(cn, 0) + 1

                    print("\nCollision Report:")
                    if collision_report:
                        for wait_node, duration in collision_report.items():
                            print(f"  {agent_id} berhenti di {wait_node}, waktu tunggu = {duration}s")
                    else:
                        print(f"  {agent_id} tidak menemui tabrakan (lancar).")

                    waypoints_coordinate = [nodes[n] for n in rute_total_agent]
                    payload_mqtt = {
                        "agent_id": agent_id,
                        "perintah": "JALAN_WAYPOINT",
                        "waypoints": waypoints_coordinate
                    }
                    print("\npayload MQTT:")
                    print(json.dumps(payload_mqtt, indent=2))

                    agent_tracker[agent_id] = {
                        "finish_time": temp_time,
                        "last_node": rute_total_agent[-1]
                    }

            # === setelah SEMUA agent diproses ===
            if batch_visual_data:
                visualize_batch_routes(batch_visual_data)
            print_reservation_table()
        except Exception as e:
            print(f"Error teknis: {e}")