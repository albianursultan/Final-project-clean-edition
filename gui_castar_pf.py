# -*- coding: utf-8 -*-
"""
GUI Cooperative A* Pathfinding (Path B - Tkinter)
-------------------------------------------------
Fitur:
1. Assign order multi-agent lewat GUI (pilih agent, node target, dan QUANTITY per node).
   Stop duration tiap node = STOP_BASE + qty * STOP_PER_ITEM detik.
2. Draggable time-slider: geser waktu dari t=0 sampai selesai, lihat tiap agent
   bergerak. Agent yang DIAM terlihat sebagai titik yang tidak bergerak:
   - oranye  = sedang STOP (pick/put) di node target  (durasi sesuai qty)
   - merah   = sedang WAIT (mengalah/menghindari tabrakan)
   - biru/dst= sedang bergerak
3. Tabel reservasi (reservation table) tampil di panel kanan-bawah.

Menggunakan kembali algoritma asli dari track_castar_calc.py + layout_track.py.
"""

import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- pakai algoritma & layout asli (import aman karena __main__ di-guard) ---
from layout_track import nodes, jalur_track
from track_castar_calc import (
    cooperative_a_star_graph, normal_a_star_graph, sorting_node, reservation_table,
    edge_reservation, get_distance, agent_speed, deadlock_zone,
)

# ====== PARAMETER STOP DURATION (berdasarkan jumlah barang) ======
STOP_BASE = 4        # detik dasar tiap berhenti di node target
STOP_PER_ITEM = 2    # tambahan detik per barang

# warna per agent
AGENT_COLORS = ["#0088ff", "#ff9500", "#00b050", "#b000ff", "#00b3b3", "#d10000"]

# node rak = semua node yang bukan crossing (X...) dan bukan Base/Stage
RACK_NODES = [n for n in nodes if not n.startswith("X") and n not in ("Base", "Stage")]
RACK_NODES.sort()


def ceil_travel(a, b):
    """Waktu tempuh antar node (detik), minimal 1 untuk langkah diam."""
    if a == b:
        return 1
    return max(1, math.ceil(get_distance(a, b) / agent_speed))


def compute_agent_plan(agent_id, targets, start_time=0, mode="Cooperative A*"):
    """
    Menghitung timeline plan berdasarkan pilihan mode algoritma.
    """
    target_nodes = [n for n, q in targets]
    qty_map = dict(targets)
    rute_order = sorting_node("Base", target_nodes, "Base")  

    keyframes = []          
    stop_windows = []       
    t = start_time

    for i in range(len(rute_order) - 1):
        # Percabangan pemilihan fungsi algoritma berdasarkan toggle GUI
        if mode == "Cooperative A*":
            seg, finish = cooperative_a_star_graph(
                rute_order[i], rute_order[i + 1], t, agent_id
            )
        else:
            seg, finish = normal_a_star_graph(
                rute_order[i], rute_order[i + 1], t, agent_id
            )
            
        if not seg:
            return None, None, None  

        if i == 0:
            keyframes.append((t, seg[0]))
        local_t = t
        for j in range(len(seg) - 1):
            dt = ceil_travel(seg[j], seg[j + 1])
            local_t += dt
            keyframes.append((local_t, seg[j + 1]))
        t = local_t

        if i < len(rute_order) - 2:
            tgt = rute_order[i + 1]
            stop = STOP_BASE + qty_map.get(tgt, 0) * STOP_PER_ITEM
            t_mulai = t
            for tt in range(t, t + stop + 1):
                reservation_table[(tgt, tt)] = agent_id
                if tgt in deadlock_zone:
                    for g in deadlock_zone[tgt]:
                        reservation_table[(g, tt)] = agent_id
            t += stop
            stop_windows.append((t_mulai, t, tgt))
            keyframes.append((t, tgt))  

    return keyframes, t, stop_windows


def position_at(keyframes, t):
    """Posisi (x, y, node, diam?) agent pada waktu t dari keyframes."""
    if not keyframes:
        return None
    if t <= keyframes[0][0]:
        n = keyframes[0][1]
        return nodes[n][0], nodes[n][1], n, True
    if t >= keyframes[-1][0]:
        n = keyframes[-1][1]
        return nodes[n][0], nodes[n][1], n, True
    for k in range(len(keyframes) - 1):
        t0, n0 = keyframes[k]
        t1, n1 = keyframes[k + 1]
        if t0 <= t <= t1:
            x0, y0 = nodes[n0]
            x1, y1 = nodes[n1]
            if n0 == n1 or t1 == t0:
                return x0, y0, n0, True   # diam (wait / stop)
            frac = (t - t0) / (t1 - t0)
            return x0 + (x1 - x0) * frac, y0 + (y1 - y0) * frac, n0, False
    n = keyframes[-1][1]
    return nodes[n][0], nodes[n][1], n, True


class PathfindingGUI:
    def __init__(self, root):
        self.root = root
        root.title("Cooperative A* — Multi-Agent Pathfinding GUI")
        root.geometry("1240x900")

        self.current_targets = []   # [(node, qty)] untuk agent yang sedang disusun
        self.orders = []            # [(agent_id, [(node, qty), ...])]
        self.plans = {}             # agent_id -> dict(keyframes, finish, stops, color)
        self.max_time = 0

        # ===== layout: kiri kontrol, kanan visual =====
        left = ttk.Frame(root, padding=10)
        left.pack(side="left", fill="y")
        right = ttk.Frame(root, padding=6)
        right.pack(side="right", fill="both", expand=True)

        # ---------- PANEL KIRI: ASSIGNMENT ----------
        ttk.Label(left, text="ASSIGN ORDER", font=("Segoe UI", 12, "bold")).pack(anchor="w")

        f1 = ttk.LabelFrame(left, text="1. Pilih Agent", padding=8)
        f1.pack(fill="x", pady=5)
        self.agent_var = tk.StringVar(value="Agent-1")
        ttk.Combobox(f1, textvariable=self.agent_var,
                     values=[f"Agent-{i}" for i in range(1, 7)],
                     state="readonly", width=18).pack(fill="x")

        f2 = ttk.LabelFrame(left, text="2. Tambah Node + Qty", padding=8)
        f2.pack(fill="x", pady=5)
        ttk.Label(f2, text="Node target:").pack(anchor="w")
        self.node_var = tk.StringVar(value=RACK_NODES[0] if RACK_NODES else "")
        ttk.Combobox(f2, textvariable=self.node_var, values=RACK_NODES,
                     state="readonly", width=18).pack(fill="x")
        row = ttk.Frame(f2); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Qty:").pack(side="left")
        self.qty_var = tk.IntVar(value=1)
        ttk.Spinbox(row, from_=1, to=99, textvariable=self.qty_var, width=6).pack(side="left", padx=6)
        ttk.Button(row, text="+ Tambah Node", command=self.add_node).pack(side="left")
        self.target_list = tk.Listbox(f2, height=4)
        self.target_list.pack(fill="x", pady=4)

        ttk.Button(left, text="✓ Assign Agent Ini", command=self.assign_agent).pack(fill="x", pady=3)
        
        # ---------- TOGGLE MODE ALGORITMA ----------
        f_mode = ttk.LabelFrame(left, text="Pilih Mode Algoritma", padding=8)
        f_mode.pack(fill="x", pady=5)
        self.algo_mode_var = tk.StringVar(value="Cooperative A*")
        
        ttk.Radiobutton(f_mode, text="Cooperative A* (Anti-Tabrakan)", 
                        variable=self.algo_mode_var, value="Cooperative A*").pack(anchor="w", pady=2)
        ttk.Radiobutton(f_mode, text="Normal A* (Abaikan Agen Lain)", 
                        variable=self.algo_mode_var, value="Normal A*").pack(anchor="w", pady=2)

        f3 = ttk.LabelFrame(left, text="Order Tersimpan", padding=8)
        f3.pack(fill="both", expand=True, pady=5)
        self.order_list = tk.Listbox(f3, height=6)
        self.order_list.pack(fill="both", expand=True)

        ttk.Button(left, text="▶ RUN SIMULATION", command=self.run_simulation).pack(fill="x", pady=3)
        ttk.Button(left, text="✖ Clear Semua", command=self.clear_all).pack(fill="x")
        ttk.Button(left, text="💾 Simpan Log ke CSV", command=self.save_to_csv).pack(fill="x", pady=(15, 3))
        ttk.Label(left, text=f"Stop = {STOP_BASE} + qty×{STOP_PER_ITEM} detik",
                  foreground="gray").pack(anchor="w", pady=(8, 0))

        # ---------- PANEL KANAN: dibagi 2 (divider bisa digeser) ----------
        paned = ttk.PanedWindow(right, orient="vertical")
        paned.pack(fill="both", expand=True)

        # --- PANE ATAS: map + slider + toggle + status ---
        top_pane = ttk.Frame(paned)
        paned.add(top_pane, weight=3)

        self.fig = Figure(figsize=(6, 5.0), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=top_pane)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        sl = ttk.Frame(top_pane); sl.pack(fill="x", pady=4)
        ttk.Label(sl, text="Waktu (t):").pack(side="left")
        self.time_var = tk.DoubleVar(value=0)
        self.slider = ttk.Scale(sl, from_=0, to=0, orient="horizontal",
                                variable=self.time_var, command=self.on_slider)
        self.slider.pack(side="left", fill="x", expand=True, padx=6)
        self.time_label = ttk.Label(sl, text="t = 0.0 s", width=12)
        self.time_label.pack(side="left")

        self.vis_frame = ttk.LabelFrame(top_pane, text="Tampilkan Agent", padding=4)
        self.vis_frame.pack(fill="x", pady=2)
        self.visible = {}

        self.status_label = ttk.Label(top_pane, text="Assign order lalu klik RUN.", foreground="#444")
        self.status_label.pack(fill="x")

        # --- PANE BAWAH: tabel (lebih besar, bisa diperbesar via divider) ---
        bottom_pane = ttk.Frame(paned)
        paned.add(bottom_pane, weight=2)

        nb = ttk.Notebook(bottom_pane)
        nb.pack(fill="both", expand=True)

        tab_res = ttk.Frame(nb); nb.add(tab_res, text="Tabel Reservasi")
        self.tree = ttk.Treeview(tab_res, columns=("t", "node", "agent"), show="headings", height=14)
        for c, w in [("t", 70), ("node", 110), ("agent", 110)]:
            self.tree.heading(c, text=c.upper()); self.tree.column(c, width=w, anchor="center")
        vs = ttk.Scrollbar(tab_res, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True); vs.pack(side="right", fill="y")

        tab_traf = ttk.Frame(nb); nb.add(tab_traf, text="Log Konflik Lalu Lintas")
        self.traf = ttk.Treeview(tab_traf, columns=("detik", "agent", "lokasi", "menuju", "pemicu"),
                                 show="headings", height=14)
        for c, w in [("detik", 80), ("agent", 80), ("lokasi", 75), ("menuju", 75), ("pemicu", 110)]:
            self.traf.heading(c, text=c.upper()); self.traf.column(c, width=w, anchor="center")
        vt = ttk.Scrollbar(tab_traf, orient="vertical", command=self.traf.yview)
        self.traf.configure(yscrollcommand=vt.set)
        self.traf.pack(side="left", fill="both", expand=True); vt.pack(side="right", fill="y")

        self.draw_map(0)

    # ---------- handler assignment ----------
    def add_node(self):
        node = self.node_var.get()
        qty = self.qty_var.get()
        if any(n == node for n, _ in self.current_targets):
            messagebox.showinfo("Info", f"{node} sudah ada di order ini.")
            return
        self.current_targets.append((node, qty))
        self.target_list.insert("end", f"{node}  (qty {qty})")

    def assign_agent(self):
        if not self.current_targets:
            messagebox.showwarning("Kosong", "Tambah minimal 1 node dulu.")
            return
        agent = self.agent_var.get()
        if any(a == agent for a, _ in self.orders):
            messagebox.showwarning("Duplikat", f"{agent} sudah punya order. Clear dulu untuk ganti.")
            return
        self.orders.append((agent, list(self.current_targets)))
        tgt_str = ", ".join(f"{n}×{q}" for n, q in self.current_targets)
        self.order_list.insert("end", f"{agent}: {tgt_str}")
        self.current_targets = []
        self.target_list.delete(0, "end")

    def build_visibility_toggles(self):
        for w in self.vis_frame.winfo_children():
            w.destroy()
        self.visible = {}
        for agent in self.plans:
            var = tk.BooleanVar(value=True)
            self.visible[agent] = var
            color = self.plans[agent]["color"]
            tk.Checkbutton(self.vis_frame, text=agent, variable=var,
                           fg=color, activeforeground=color,
                           command=lambda: self.draw_map(float(self.time_var.get()))
                           ).pack(side="left", padx=4)
        ttk.Button(self.vis_frame, text="Semua",
                   command=lambda: self._set_all_visible(True)).pack(side="left", padx=(12, 2))
        ttk.Button(self.vis_frame, text="Sembunyikan Semua",
                   command=lambda: self._set_all_visible(False)).pack(side="left", padx=2)

    def _set_all_visible(self, val):
        for var in self.visible.values():
            var.set(val)
        self.draw_map(float(self.time_var.get()))

    def clear_all(self):
        self.current_targets = []
        self.orders = []
        self.plans = {}
        self.max_time = 0
        self.target_list.delete(0, "end")
        self.order_list.delete(0, "end")
        self.tree.delete(*self.tree.get_children())
        self.traf.delete(*self.traf.get_children())
        self.slider.configure(to=0)
        self.time_var.set(0)
        for w in self.vis_frame.winfo_children():
            w.destroy()
        self.visible = {}
        reservation_table.clear()
        edge_reservation.clear()
        self.status_label.config(text="Sudah di-clear. Assign order baru.")
        self.draw_map(0)

    # ---------- jalankan simulasi ----------
    def run_simulation(self):
        if not self.orders:
            messagebox.showwarning("Kosong", "Assign minimal 1 agent dulu.")
            return
        reservation_table.clear()
        edge_reservation.clear()
        self.plans = {}
        self.max_time = 0
        gagal = []
        
        # Ambil mode aktif dari GUI
        mode_aktif = self.algo_mode_var.get()
        
        for idx, (agent, targets) in enumerate(self.orders):
            # Kirim parameter mode_aktif ke fungsi kalkulasi rute
            keyframes, finish, stops = compute_agent_plan(agent, targets, start_time=0, mode=mode_aktif)
            if keyframes is None:
                gagal.append(agent)
                continue
            self.plans[agent] = {
                "keyframes": keyframes,
                "finish": finish,
                "stops": stops,
                "color": AGENT_COLORS[idx % len(AGENT_COLORS)],
            }
            self.max_time = max(self.max_time, finish)

        self.slider.configure(to=self.max_time)
        self.time_var.set(0)
        self.populate_reservation_table()
        events, tabrakan = self.detect_traffic()
        self.populate_traffic(events)
        self.build_visibility_toggles()
        self.draw_map(0)
        
        # Tampilkan ringkasan hasil simulasi berdasarkan mode
        msg = (f"[{mode_aktif}] Selesai. {len(self.plans)} agent, makespan {self.max_time}s. "
               f"Konflik dihindari: {len(events)}. Tabrakan tersisa: {tabrakan}.")
        if gagal:
            msg += f"  Gagal rute: {', '.join(gagal)}."
        self.status_label.config(text=msg)
        
    def populate_reservation_table(self):
        self.tree.delete(*self.tree.get_children())
        for (node, t), agent in sorted(reservation_table.items(),
                                       key=lambda kv: (kv[0][1], kv[0][0])):
            self.tree.insert("", "end", values=(t, node, agent))

    # ---------- deteksi konflik lalu lintas ----------
    def _node_at(self, kf, t):
        if t <= kf[0][0]:
            return kf[0][1]
        if t >= kf[-1][0]:
            return kf[-1][1]
        for k in range(len(kf) - 1):
            t0, n0 = kf[k]; t1, n1 = kf[k + 1]
            if t0 <= t < t1:
                return n0 if n0 == n1 else None   # None = sedang di tengah edge
        return kf[-1][1]

    def _edge_at(self, kf, t):
        if t <= kf[0][0] or t >= kf[-1][0]:
            return None
        for k in range(len(kf) - 1):
            t0, n0 = kf[k]; t1, n1 = kf[k + 1]
            if t0 <= t < t1 and n0 != n1:
                return frozenset((n0, n1))
        return None

    def detect_traffic(self):
        """Kembalikan (events, jumlah_tabrakan_tersisa).
        events: (detik, agent_menunggu, lokasi, menuju, pemicu)."""
        agents = list(self.plans.keys())
        tmax = int(self.max_time)

        # 1) validasi: cek tabrakan tersisa (harusnya 0 setelah edge-avoidance)
        tabrakan = 0
        for t in range(tmax + 1):
            occ_n = {}; occ_e = {}
            for ag in agents:
                kf = self.plans[ag]["keyframes"]
                n = self._node_at(kf, t)
                if n and n not in ("Base", "Stage"):
                    if n in occ_n and occ_n[n] != ag:
                        tabrakan += 1
                    occ_n[n] = ag
                e = self._edge_at(kf, t)
                if e:
                    if e in occ_e and occ_e[e] != ag:
                        tabrakan += 1
                    occ_e[e] = ag

        # 2) yield events: agent berhenti paksa (bukan stop qty) utk hindari tabrakan.
        #    Detik tunggu yang berurutan di node yang sama DIGABUNG jadi satu baris,
        #    dan pemicu diambil dari SELURUH rentang tunggu (bukan per-detik).
        events = []
        for ag in agents:
            kf = self.plans[ag]["keyframes"]; stops = self.plans[ag]["stops"]
            k = 0
            while k < len(kf) - 1:
                t0, n0 = kf[k]; t1, n1 = kf[k + 1]
                if not (n0 == n1 and t1 > t0):
                    k += 1
                    continue
                if any(a <= t0 and t1 <= b and nd == n0 for a, b, nd in stops):
                    k += 1
                    continue

                # gabung segmen tunggu berurutan di node yang sama
                node = n0
                wait_start, wait_end = t0, t1
                kk = k + 1
                while kk < len(kf) - 1:
                    tt0, nn0 = kf[kk]; tt1, nn1 = kf[kk + 1]
                    if nn0 == nn1 == node and tt1 > tt0 and \
                       not any(a <= tt0 and tt1 <= b and nd == node for a, b, nd in stops):
                        wait_end = tt1
                        kk += 1
                    else:
                        break

                # node tujuan berikutnya setelah tunggu selesai
                nxt = None
                for kj in range(kk, len(kf)):
                    if kf[kj][1] != node:
                        nxt = kf[kj][1]; break

                # pemicu: agent lain yang menempati node/edge kontes selama rentang tunggu
                pemicu = set()
                for other in agents:
                    if other == ag:
                        continue
                    okf = self.plans[other]["keyframes"]
                    for tt in range(int(wait_start), int(wait_end) + 1):
                        on = self._node_at(okf, tt)
                        oe = self._edge_at(okf, tt)
                        if on in (nxt, node) or (nxt and oe == frozenset((node, nxt))):
                            pemicu.add(other)

                events.append((f"{int(wait_start)}-{int(wait_end)}", ag, node, nxt or "-",
                               ", ".join(sorted(pemicu)) or "-"))
                k = kk
        events.sort(key=lambda e: int(e[0].split("-")[0]))
        return events, tabrakan

    def populate_traffic(self, events):
        self.traf.delete(*self.traf.get_children())
        for ev in events:
            self.traf.insert("", "end", values=ev)

    # ---------- gambar peta ----------
    def draw_map(self, t):
        ax = self.ax
        ax.clear()
        # jalur
        for u, v in jalur_track:
            ax.plot([nodes[u][0], nodes[v][0]], [nodes[u][1], nodes[v][1]],
                    color="#bbbbbb", lw=2, ls="dashed", zorder=1)
        # node
        for name, (x, y) in nodes.items():
            if name == "Base":
                ax.scatter(x, y, c="red", marker="s", s=160, zorder=3)
                ax.text(x, y - 0.35, "BASE", ha="center", fontsize=8, fontweight="bold", color="red")
            elif name == "Stage":
                ax.scatter(x, y, c="green", marker="s", s=160, zorder=3)
                ax.text(x, y - 0.35, "STAGE", ha="center", fontsize=8, fontweight="bold", color="green")
            elif name.startswith("X"):
                ax.scatter(x, y, c="#cccccc", s=40, zorder=2)
            else:
                ax.scatter(x, y, c="#1f77b4", s=120, edgecolors="white", zorder=3)
                ax.text(x, y + 0.28, name, ha="center", fontsize=8, fontweight="bold")

        # rute tiap agent (transparan) + posisi agent saat t
        for agent, p in self.plans.items():
            if agent in self.visible and not self.visible[agent].get():
                continue
            kf = p["keyframes"]
            rx = [nodes[n][0] for _, n in kf]
            ry = [nodes[n][1] for _, n in kf]
            ax.plot(rx, ry, color=p["color"], lw=4, alpha=0.25, zorder=2)

            pos = position_at(kf, t)
            if pos:
                x, y, node, diam = pos
                # status: STOP (pick/put) vs WAIT (yield) vs moving
                color = p["color"]; ring = p["color"]; label = agent
                if diam:
                    in_stop = any(a <= t <= b and node == nd for a, b, nd in p["stops"])
                    if in_stop:
                        ring = "#ff9500"; label = f"{agent} (STOP)"
                    elif t < p["finish"]:
                        ring = "#d10000"; label = f"{agent} (WAIT)"
                ax.scatter(x, y, c=color, s=260, edgecolors=ring, linewidths=3, zorder=5)
                ax.text(x, y, agent.split("-")[-1], ha="center", va="center",
                        color="white", fontsize=8, fontweight="bold", zorder=6)

        ax.set_title(f"Cooperative A* — t = {t:.1f}s", fontweight="bold")
        ax.set_aspect("equal")
        ax.set_xlim(-2.5, 5.5)
        ax.set_ylim(-9.5, 2.0)
        ax.grid(True, ls=":", color="#eeeeee", zorder=0)
        self.canvas.draw()

    def on_slider(self, val):
        t = float(val)
        self.time_label.config(text=f"t = {t:.1f} s")
        self.draw_map(t)
    
    def save_to_csv(self):
        # Cek apakah ada data di salah satu tabel
        if not self.tree.get_children() and not self.traf.get_children():
            messagebox.showwarning("Data Kosong", "Tidak ada data simulasi yang bisa disimpan. Silakan jalankan simulasi terlebih dahulu.")
            return

        # Buka dialog untuk memilih lokasi simpan file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Simpan Log & Reservasi Agent",
            initialfile="Log_Simulasi_WNS.csv"
        )

        if not file_path:
            return # Dibatalkan oleh user

        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # --- 1. Menulis Data Tabel Reservasi ---
                writer.writerow(["=== TABEL RESERVASI (Cooperative A*) ==="])
                writer.writerow(["Waktu (t)", "Node", "Agent"])
                for child in self.tree.get_children():
                    # Ambil values dari setiap baris di treeview reservasi
                    row_data = self.tree.item(child)["values"]
                    writer.writerow(row_data)

                writer.writerow([]) # Baris kosong sebagai pemisah
                writer.writerow([]) 

                # --- 2. Menulis Data Log Konflik Lalu Lintas ---
                writer.writerow(["=== LOG KONFLIK LALU LINTAS ==="])
                writer.writerow(["Detik", "Agent", "Lokasi", "Menuju", "Pemicu"])
                for child in self.traf.get_children():
                    # Ambil values dari setiap baris di treeview traffic
                    row_data = self.traf.item(child)["values"]
                    writer.writerow(row_data)

            messagebox.showinfo("Sukses", f"Data saved to:\n{file_path}")
        
        except Exception as e:
            messagebox.showerror("Error", f"falied saving CSV file:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PathfindingGUI(root)
    root.mainloop()