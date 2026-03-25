import tkinter as tk
from tkinter import ttk, messagebox
import math
from collections import defaultdict

# ------------------------------------------------------------
# 1. HARDWARE DATA
# ------------------------------------------------------------
RAID_DATA = [
    ["1U NVR", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
    ["2U 175 Ch", "ADVER00RN2K", 175, 1000, 12, 13854.20],
]

HDD_LIST = [
    (1, 63.15), (2, 94.71), (3, 105.26), (4, 168.42), (6, 215.78),
    (8, 306.42), (10, 355.53), (12, 442.10), (14, 617.98), (18, 720.55),
    (22, 685.28), (24, 863.48), (26, 822.88)
]

# ------------------------------------------------------------
# 2. OPTIMIZED LOGIC FUNCTIONS
# ------------------------------------------------------------

def find_cheapest_hdd_config(required_tb, slots_available, parity):
    """Calculates the lowest price to hit TB. Returns (cost, config)."""
    if required_tb <= 0: return 0, {"qty": 0, "cap": 0, "usable": 0, "cost": 0}
    best_cost = float('inf')
    best_cfg = None
    for cap, price in HDD_LIST:
        data_drives = math.ceil(required_tb / cap)
        total_drives = data_drives + parity
        if total_drives <= slots_available and data_drives >= 1:
            total_price = total_drives * price
            if total_price < best_cost:
                best_cost = total_price
                best_cfg = {"qty": total_drives, "cap": cap, "usable": data_drives * cap, "cost": total_price}
    return best_cost, best_cfg

def distribute_weighted(nvr_count, model, camera_list, parity):
    """
    Tests multiple distribution ratios (from balanced to skewed) 
    to find which one results in the cheapest drive BOM.
    """
    best_dist_cost = float('inf')
    best_dist_layout = None

    # We test different 'fill' percentages for the primary NVR
    # to see if packing it to a certain TB threshold saves money.
    total_t = sum(c['qty'] * c['tb_per_unit'] for c in camera_list)
    total_c = sum(c['qty'] for c in camera_list)
    total_m = sum(c['qty'] * c['tp'] for c in camera_list)

    # Simplified heuristic: Try 50/50, 60/40, 70/30, 80/20, 90/10 splits
    for ratio in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        if nvr_count == 1: ratio = 1.0
        
        # Split TB by ratio
        tb1 = total_t * ratio
        tb2 = total_t - tb1
        
        # Check if cameras and mbps fit this split (estimated)
        c1 = math.ceil(total_c * ratio)
        c2 = total_c - c1
        m1 = total_m * ratio
        m2 = total_m - m1

        if c1 <= model[2] and c2 <= model[2] and m1 <= model[3] and m2 <= model[3]:
            cost1, cfg1 = find_cheapest_hdd_config(tb1, model[4], parity)
            cost2, cfg2 = find_cheapest_hdd_config(tb2, model[4], parity) if nvr_count > 1 else (0, None)
            
            if cfg1 and (nvr_count == 1 or (nvr_count > 1 and cfg2)):
                current_total = (model[5] * nvr_count) + cost1 + cost2
                if current_total < best_dist_cost:
                    best_dist_cost = current_total
                    best_dist_layout = [
                        {"cams": c1, "mbps": m1, "tb": tb1, "h_cfg": cfg1},
                        {"cams": c2, "mbps": m2, "tb": tb2, "h_cfg": cfg2}
                    ] if nvr_count > 1 else [{"cams": c1, "mbps": m1, "tb": tb1, "h_cfg": cfg1}]
        
        if nvr_count == 1: break
            
    return best_dist_layout, best_dist_cost

# ------------------------------------------------------------
# 3. GUI APPLICATION
# ------------------------------------------------------------

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Absolute Lowest Cost BOM")
        self.camera_list = []
        self.setup_ui()

    def setup_ui(self):
        input_frame = ttk.LabelFrame(self.root, text=" Camera Entry ", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Qty:").grid(row=0, column=0)
        self.ent_qty = ttk.Entry(input_frame, width=8); self.ent_qty.grid(row=0, column=1, padx=5)
        ttk.Label(input_frame, text="Mbps:").grid(row=0, column=2)
        self.ent_mbps = ttk.Entry(input_frame, width=8); self.ent_mbps.grid(row=0, column=3, padx=5)
        ttk.Label(input_frame, text="GB:").grid(row=0, column=4)
        self.ent_gb = ttk.Entry(input_frame, width=8); self.ent_gb.grid(row=0, column=5, padx=5)

        ttk.Button(input_frame, text="Add", command=self.add_camera).grid(row=0, column=6, padx=5)
        ttk.Button(input_frame, text="Reset", command=self.clear_all).grid(row=0, column=7)

        self.tree = ttk.Treeview(self.root, columns=("Q", "M", "GB", "TotalTB"), show="headings", height=5)
        for col in ["Q", "M", "GB", "TotalTB"]: self.tree.heading(col, text=col)
        self.tree.pack(fill="x", padx=10, pady=5)

        self.raid_var = tk.IntVar(value=1)
        ttk.Radiobutton(self.root, text="RAID 5 (1 Parity)", variable=self.raid_var, value=1).pack()
        ttk.Radiobutton(self.root, text="RAID 6 (2 Parity)", variable=self.raid_var, value=2).pack()

        ttk.Button(self.root, text="CALCULATE LOWEST PROJECT COST", command=self.calculate).pack(pady=10)

        self.txt_res = tk.Text(self.root, height=22, width=95, state="disabled", font=("Consolas", 10), bg="#000000", fg="#00FF00")
        self.txt_res.pack(padx=10, pady=10)

    def add_camera(self):
        try:
            q, m, gb = int(self.ent_qty.get()), float(self.ent_mbps.get()), float(self.ent_gb.get())
            self.camera_list.append({'qty': q, 'tp': m, 'tb_per_unit': gb / 1024})
            self.tree.insert("", "end", values=(q, m, gb, f"{(gb*q)/1024:.2f}"))
        except: pass

    def clear_all(self):
        self.camera_list = []; [self.tree.delete(i) for i in self.tree.get_children()]

    def calculate(self):
        if not self.camera_list: return
        parity = self.raid_var.get()
        best_overall_cost = float('inf')
        best_overall_solution = None

        for model in RAID_DATA:
            total_c = sum(c['qty'] for c in self.camera_list)
            total_m = sum(c['qty'] * c['tp'] for c in self.camera_list)
            min_u = max(math.ceil(total_c / model[2]), math.ceil(total_m / model[3]))

            for q in range(min_u, min_u + 2):
                layout, run_cost = distribute_weighted(q, model, self.camera_list, parity)
                if layout and run_cost < best_overall_cost:
                    best_overall_cost = run_cost
                    best_overall_solution = {"model": model, "units": layout, "total": run_cost}

        self.display(best_overall_solution)

    def display(self, res):
        self.txt_res.config(state="normal"); self.txt_res.delete("1.0", tk.END)
        if not res:
            self.txt_res.insert(tk.END, "No configuration found.")
        else:
            self.txt_res.insert(tk.END, f"CHEAPEST COST-DRIVEN DISTRIBUTION | TOTAL: ${res['total']:,.2f}\n" + "="*85 + "\n")
            for i, unit in enumerate(res['units']):
                if unit['cams'] == 0 and i > 0: continue
                self.txt_res.insert(tk.END, f"UNIT {i+1}: {res['model'][0]} ({res['model'][1]})\n")
                self.txt_res.insert(tk.END, f"  - Distribution: {unit['cams']} Cameras | {unit['mbps']:.2f} Mbps | {unit['tb']:.2f} TB Load\n")
                h = unit['h_cfg']
                self.txt_res.insert(tk.END, f"  - HDD BOM: {h['qty']} x {h['cap']} TB | Usable: {h['usable']:.2f} TB | Slots: {h['qty']}/{res['model'][4]}\n")
                self.txt_res.insert(tk.END, f"  - Subtotal: ${res['model'][5] + h['cost']:,.2f}\n" + "-"*75 + "\n")
        self.txt_res.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("850x850"); app = CCTVApp(root); root.mainloop()
