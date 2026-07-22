import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# ==========================================
# 1. SETUP TITIK KOORDINAT (NODE) MURNI
# ==========================================
nodes = {
    # Aisle A (kolom kanan, x = 4)
    "A1": (4, -8.5), "A2": (4, -7), "A3": (4, -4.5), "A4": (4, -3),

    # Aisle B (kolom tengah, x = 1.5)
    "B1": (1.5, -8.5), "B2": (1.5, -7), "B3": (1.5, -4.5), "B4": (1.5, -3),

    # Aisle C (kolom kiri, x = -1)
    "C1": (-1, -8.5), "C2": (-1, -7), "C3": (-1, -4.5), "C4": (-1, -3),

    # Crossing Aisle 1 (A-B-C)
    "X1_A": (4, -5.7), "X1_B": (1.5, -5.7), "X1_C": (-1, -5.7),

    # Crossing Aisle 2 (A-B)
    "X2_A": (3.5, -1.5), "X2_B": (1.5, -1.5),

    # Crossing Aisle 3 (B-C)
    "X3_B": (1.5, 0), "X3_C": (-1, 0),

    # T-junction Base-Aisle 1 dan 2
    "XA_T-junc": (4, -1.5),

    # Stage & Base  (Base = titik referensi 0,0)
    "Stage": (3.5, 0.5),
    "Base": (0, 0)   # referensi (0,0)
}

# ==========================================
# 2. SETUP GARIS LINTASAN (VIRTUAL TRACK)
# ==========================================
jalur_track = [
    # -----------------------------------
    # JALUR VERTIKAL (Lorong Rak)
    # -----------------------------------
    # Lorong A (Menyambung sampai ke Stage di Y=1)
    ("A1", "A2"), ("A2", "X1_A"), ("X1_A", "A3"), ("A3", "A4"),       #crosing:
    ("A4","XA_T-junc"),("XA_T-junc","X2_A"),("X2_A", "Stage"),
    
    # Lorong B (Mentok di Crossing 3 Y=1.5)
    ("B1", "B2"), ("B2", "X1_B"), ("X1_B", "B3"), ("B3", "B4"), ("B4", "X2_B"), ("X2_B", "X3_B"),
    
    # Lorong C (Mentok di Crossing 3 Y=1.5)
    ("C1", "C2"), ("C2", "X1_C"), ("X1_C", "C3"), ("C3", "C4"), ("C4", "X3_C"),
    
    # -----------------------------------
    # JALUR HORIZONTAL (Crossing Aisle)
    # -----------------------------------
    # Crossing 1 (Y = 7.5) tembus A-B-C
    ("X1_A", "X1_B"), ("X1_B", "X1_C"),
    
    # Crossing 2 (Y = 2) cuma A-B
    ("X2_A", "X2_B"),
    
    # Crossing 3 (Y = 1.5) B-C ngelewatin Base di tengahnya
    ("X3_B", "Base"), ("Base", "X3_C")     

]

# ==========================================
# 3. MESIN VISUALISATOR LAYOUT
# ==========================================
def cek_custom_layout():
    fig, ax = plt.subplots(figsize=(8, 12))
    
    # 1. Gambar Garis Lintasan
    for u, v in jalur_track:
        if u in nodes and v in nodes:
            x_vals = [nodes[u][0], nodes[v][0]]
            y_vals = [nodes[u][1], nodes[v][1]]
            ax.plot(x_vals, y_vals, color="#797979", linewidth=2.5, linestyle='dashed', zorder=1)

    # 2. Gambar Titik Node
    for name, (x, y) in nodes.items():
        if name == "Base":
            ax.scatter(x, y, c='red', marker='s', s=200, zorder=4)
            ax.text(x, y+0.3, "BASE", ha='center', fontweight='bold', color='red')
        elif name == "Stage":
            ax.scatter(x, y, c='green', marker='s', s=200, zorder=4)
            ax.text(x, y+0.3, "STAGE", ha='center', fontweight='bold', color='green')
        elif name.startswith("X"): # Titik Crossing Aisle
            ax.scatter(x, y, c='gray', s=50, zorder=3)
        else: # Titik Rak PTL
            ax.scatter(x, y, c='#1f77b4', s=180, edgecolors='white', zorder=4)
            ax.text(x, y+0.2, name, ha='center', fontweight='bold', fontsize=10)

    # 3. Styling ala Blueprint
    ax.set_title("Layout WNS 1 - Topological Virtual Track", fontweight='bold', pad=15, fontsize=14)
    ax.set_aspect('equal')
    ax.set_xlabel("Sumbu X (Meter)")
    ax.set_ylabel("Sumbu Y (Meter)")
    
    # Bikin background batas gudang 7x11 Meter
    ax.set_xlim(-2.5, 5.5)
    ax.set_ylim(-9.5, 2.0)
    ax.set_xticks(range(-2, 6))
    ax.set_yticks(range(-9, 3))
    ax.grid(True, linestyle=':', color='lightgray', zorder=0)
    
    # Custom Legend
    custom_lines = [
        Line2D([0], [0], color="#797979", lw=2, linestyle='dashed', label='Virtual Track'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#1f77b4', markersize=10, label='Rak PTL'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=6, label='Persimpangan (X)'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='red', markersize=10, label='Base'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='green', markersize=10, label='Stage')
    ]
    ax.legend(handles=custom_lines, loc='lower center', bbox_to_anchor=(0.5, -0.12), ncol=3, shadow=True, fancybox=True)
    
    plt.tight_layout()
    plt.savefig("layout_gudang_wns1.png", dpi=300, bbox_inches='tight')
    plt.show()


if __name__ == '__main__':
    cek_custom_layout()
    
    
from layout_track import nodes, jalur_track

print("Checking edges that are NOT grid-aligned:")
found = False
for u, v in jalur_track:
    x1, y1 = nodes[u]
    x2, y2 = nodes[v]
    if x1 != x2 and y1 != y2:        # differs in both -> diagonal
        print(f"  DIAGONAL: {u}{nodes[u]}  ->  {v}{nodes[v]}")
        found = True
if not found:
    print("  All edges are horizontal or vertical. Track is clean.")
    
 