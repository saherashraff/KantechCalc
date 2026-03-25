import tkinter as tk
from tkinter import ttk, messagebox
import math
from collections import defaultdict

# ------------------------------------------------------------
# 1. HARDWARE DATA
# ------------------------------------------------------------
# Format: [Name, Part Number, Max Cameras, Max Mbps, Drive Slots, Price]
RAID_DATA = [
    ["1U NVR", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
    ["2U 175 Ch", "ADVER00RN2K", 175, 1000, 12, 13854.20],
]

JBOD_DATA = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00],
    ["1U NVR", "ADVER00N0NP16G", 32, 100, 4, 3750.00],
    ["Desktop NVR", "ADVED00N0N5H", 50, 200, 2, 2291.70],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 80, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 160, 1, 770.85],
]

# HDD PRICE LIST (Capacity in TB, Price)
HDD_LIST = [
    (1, 63.15), (2, 94.71), (3, 105.26), (4, 168.42), (6, 215.78),
    (8, 306.42), (10, 355.53), (12, 442.10), (14, 617.98), (18, 720.55),
    (22, 685.28), (24, 863.48), (26, 822.88)
]

# ------------------------------------------------------------
# 2. LOGIC FUNCTIONS
# ------------------------------------------------------------

def find_cheapest_hdd_config(required_tb, slots_available, parity):
    """Calculates the absolute lowest price for HDDs to hit the TB target."""
    best_cost = float('inf')
    best_cfg = None

    for cap, price in HDD_LIST:
        # RAID 5/6 Math: Data Drives + Parity Drives
        data_drives = math.ceil(required_tb / cap)
        total_drives = data_drives + parity

        # Check if it fits in NVR and meets RAID minimums
        if total_drives <= slots_available and data_drives >= 1:
            total_price = total_drives * price
            if total_price < best_cost:
                best_cost = total_price
                best_cfg = {
                    "qty": total_drives,
                    "cap": cap,
                    "usable": data_drives * cap,
                    "cost": total_price
                }
            # If price is tied, use fewer drives to save slots
            elif total_price == best_cost and best_cfg:
                if total_drives < best_cfg['qty']:
                    best_cfg = {
                        "qty": total_drives, "cap": cap, 
                        "usable": data_drives * cap, "cost": total_price
                    }
    return best_cost, best_cfg

# ------------------------------------------------------------
# 3. GUI APPLICATION
# ------------------------------------------------------------

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Absolute Cheapest BOM Optimizer")
        self.camera_list = []
        self.setup_ui()

    def setup_ui(self):
        # Input Frame
        input_frame = ttk.LabelFrame(self.root, text=" Camera Entry (GB per Camera) ", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Qty:").grid(row=0, column=0)
        self.ent_qty = ttk.Entry(input_frame, width=8); self.ent_qty.grid(row=0, column=1, padx=5)
        ttk.Label(input_frame, text="Mbps:").grid(row=0, column=2)
        self.ent_mbps = ttk.Entry(input_frame, width=8); self.ent_mbps.grid(row=0, column=3, padx=5)
        ttk.Label(input_frame, text="GB:").grid(row=0, column=4)
        self.ent_gb = ttk.Entry(input_frame, width=8); self.ent_gb.grid(row=0, column=5, padx=5)

        ttk.Button(input_frame, text="Add", command=self.add_camera).grid(row=0, column=6, padx=5)
        ttk.Button(input_frame, text="Reset", command=self.clear_all).grid(row=0, column=7)

        # Table
        self.tree = ttk.Treeview(self.root, columns=("ID", "Qty", "Mbps", "GB", "TotalTB"), show="headings", height=5)
        for col in ["ID", "Qty", "Mbps", "GB", "TotalTB"]: self.tree.heading(col, text=col)
        self.tree.pack(fill="x", padx=10, pady=5)

        # Tabs
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)
        self.t_raid, self.t_jbod, self.t_holis = ttk.Frame(self.tabs), ttk.Frame(self.tabs), ttk.Frame(self.tabs)
        self.tabs.add(self.t_raid, text=" RAID "); self.tabs.add(self.t_jbod, text=" JBOD "); self.tabs.add(self.t_holis, text=" HOLIS ")

        self.raid_var = tk.IntVar(value=1) # Parity: RAID 5 = 1, RAID 6 = 2
        ttk.Radiobutton(self.t_raid, text="RAID 5 (1 Parity)", variable=self.raid_var, value=1).pack(pady=5)
        ttk.Radiobutton(self.t_raid, text="RAID 6 (2 Parity)", variable=self.raid_var, value=2).pack()

        ttk.Button(self.root, text="FIND ABSOLUTE CHEAPEST OPTION", command=self.calculate).pack(pady=10)

        self.txt_res = tk.Text(self.root, height=20, width=95, state="disabled", font=("Consolas", 10), bg="#000000", fg="#00FF00")
        self.txt_res.pack(padx=10, pady=10)

    def add_camera(self):
        try:
            q, m, gb = int(self.ent_qty.get()), float(self.ent_mbps.get()), float(self.ent_gb.get())
            tb_val = (gb * q) / 1024
            self.camera_list.append({'qty': q, 'tp': m, 'tb': tb_val})
            self.tree.insert("", "end", values=(len(self.camera_list), q, m, gb, f"{tb_val:.2f}"))
            for e in [self.ent_qty, self.ent_mbps, self.ent_gb]: e.delete(0, tk.END)
        except: pass

    def clear_all(self):
        self.camera_list = []; [self.tree.delete(i) for i in self.tree.get_children()]

    def calculate(self):
        if not self.camera_list: return
        
        # Determine Mode Data
        idx = self.tabs.index(self.tabs.select())
        if idx == 0: hw_list, parity, mode_name = RAID_DATA, self.raid_var.get(), f"RAID {self.raid_var.get()+4}"
        elif idx == 1: hw_list, parity, mode_name = JBOD_DATA, 0, "JBOD"
        else: hw_list, parity, mode_name = HOLIS_DATA, 0, "Holis"

        total_c = sum(c['qty'] for c in self.camera_list)
        total_m = sum(c['qty'] * c['tp'] for c in self.camera_list)
        total_t = sum(c['tb'] for c in self.camera_list)

        best_project_cost = float('inf')
        best_solution = None

        # TEST EVERY SINGLE NVR MODEL
        for model in hw_list:
            name, part, max_c, max_m, slots, unit_price = model
            
            # 1. How many units of THIS model do we need?
            num_nvrs = max(math.ceil(total_c / max_c), math.ceil(total_m / max_m))
            
            # Try from minimum units up to +2 (splitting sometimes saves HDD costs)
            for q in range(num_nvrs, num_nvrs + 2):
                tb_per_nvr = total_t / q
                h_cost, h_cfg = find_cheapest_hdd_config(tb_per_nvr, slots, parity)

                if h_cfg:
                    total_run_cost = (unit_price * q) + (h_cost * q)
                    if total_run_cost < best_project_cost:
                        best_project_cost = total_run_cost
                        best_solution = {
                            "model": name, "part": part, "qty": q,
                            "hdd": h_cfg, "mode": mode_name, "total": total_run_cost
                        }

        self.display(best_solution)

    def display(self, res):
        self.txt_res.config(state="normal"); self.txt_res.delete("1.0", tk.END)
        if not res:
            self.txt_res.insert(tk.END, "No valid solution found.")
        else:
            self.txt_res.insert(tk.END, f"--- CHEAPEST {res['mode']} SOLUTION FOUND ---\n\n")
            self.txt_res.insert(tk.END, f"HARDWARE:\n")
            self.txt_res.insert(tk.END, f"  NVR Model:      {res['model']} ({res['part']})\n")
            self.txt_res.insert(tk.END, f"  NVR Quantity:   {res['qty']} Unit(s)\n")
            self.txt_res.insert(tk.END, f"  Unit Price:     ${(res['total']/res['qty'] - res['hdd']['cost']):,.2f}\n\n")
            
            self.txt_res.insert(tk.END, f"STORAGE PER UNIT:\n")
            self.txt_res.insert(tk.END, f"  HDD Config:     {res['hdd']['qty']} x {res['hdd']['cap']} TB\n")
            self.txt_res.insert(tk.END, f"  Usable / Unit:  {res['hdd']['usable']:.2f} TB\n")
            self.txt_res.insert(tk.END, f"  Total HDDs:     {res['hdd']['qty'] * res['qty']} drives across project\n\n")
            
            self.txt_res.insert(tk.END, f"PROJECT TOTALS:\n")
            self.txt_res.insert(tk.END, f"  Hardware Total: ${(res['total'] - (res['hdd']['cost'] * res['qty'])):,.2f}\n")
            self.txt_res.insert(tk.END, f"  HDD Total:      ${(res['hdd']['cost'] * res['qty']):,.2f}\n")
            self.txt_res.insert(tk.END, f"  GRAND TOTAL:    ${res['total']:,.2f}\n")
            self.txt_res.insert(tk.END, "="*60 + "\n")
        self.txt_res.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("800x800"); app = CCTVApp(root); root.mainloop()
