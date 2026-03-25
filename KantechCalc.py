import tkinter as tk
from tkinter import ttk, messagebox
import math
from collections import defaultdict

# ------------------------------------------------------------
# 1. HARDWARE & DRIVE DATA
# ------------------------------------------------------------
RAID_DATA = [
    ["1U NVR", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
]

HDD_LIST = [
    (1, 63.15), (2, 94.71), (3, 105.26), (4, 168.42), (6, 215.78),
    (8, 306.42), (10, 355.53), (12, 442.10), (14, 617.98), (18, 720.55),
    (22, 685.28), (24, 863.48), (26, 822.88)
]

# ------------------------------------------------------------
# 2. CALCULATION ENGINE
# ------------------------------------------------------------

def get_best_hdd(required_tb, slots, parity):
    """Finds the cheapest HDD configuration for a specific TB requirement."""
    if required_tb <= 0: return 0, {"qty": 0, "cap": 0, "cost": 0, "usable": 0}
    best_cost = float('inf')
    best_cfg = None
    
    for cap, price in HDD_LIST:
        data_drives = math.ceil(required_tb / cap)
        total_drives = data_drives + parity
        if total_drives <= slots and data_drives >= 1:
            total_price = total_drives * price
            if total_price < best_cost:
                best_cost = total_price
                best_cfg = {
                    "qty": total_drives, 
                    "cap": cap, 
                    "cost": total_price, 
                    "usable": data_drives * cap
                }
    return best_cost, best_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Absolute Brute-Force Optimizer")
        self.camera_types = [] 
        self.setup_ui()

    def setup_ui(self):
        # --- INPUT SECTION ---
        input_frame = ttk.LabelFrame(self.root, text=" Add Camera Type ", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Qty:").grid(row=0, column=0)
        self.e_qty = ttk.Entry(input_frame, width=5); self.e_qty.grid(row=0, column=1, padx=5)
        ttk.Label(input_frame, text="Mbps:").grid(row=0, column=2)
        self.e_mbps = ttk.Entry(input_frame, width=5); self.e_mbps.grid(row=0, column=3, padx=5)
        ttk.Label(input_frame, text="GB:").grid(row=0, column=4)
        self.e_gb = ttk.Entry(input_frame, width=8); self.e_gb.grid(row=0, column=5, padx=5)

        ttk.Button(input_frame, text="Add Type", command=self.add_cam).grid(row=0, column=6, padx=5)
        ttk.Button(input_frame, text="Clear All", command=self.clear).grid(row=0, column=7)

        # --- DATA TABLE ---
        self.tree = ttk.Treeview(self.root, columns=("ID", "Qty", "Mbps", "GB"), show="headings", height=4)
        for c in ["ID", "Qty", "Mbps", "GB"]: self.tree.heading(c, text=c)
        self.tree.pack(fill="x", padx=10, pady=5)

        # --- RAID CONFIG ---
        self.raid_var = tk.IntVar(value=1)
        ttk.Label(self.root, text="Select Redundancy Level:").pack()
        ttk.Radiobutton(self.root, text="RAID 5 (1 Drive Parity)", variable=self.raid_var, value=1).pack()
        ttk.Radiobutton(self.root, text="RAID 6 (2 Drive Parity)", variable=self.raid_var, value=2).pack()

        ttk.Button(self.root, text="RUN BRUTE-FORCE OPTIMIZATION", command=self.optimize, style="Accent.TButton").pack(pady=10)

        # --- OUTPUT CONSOLE ---
        self.txt = tk.Text(self.root, height=25, width=95, state="disabled", font=("Consolas", 10), bg="#000", fg="#0f0")
        self.txt.pack(padx=10, pady=10)

    def add_cam(self):
        try:
            q, m, g = int(self.e_qty.get()), float(self.e_mbps.get()), float(self.e_gb.get())
            self.camera_types.append({'id': len(self.camera_types)+1, 'qty': q, 'tp': m, 'tb': g/1024, 'gb': g})
            self.tree.insert("", "end", values=(len(self.camera_types), q, m, g))
            for e in [self.e_qty, self.e_mbps, self.e_gb]: e.delete(0, tk.END)
        except: messagebox.showerror("Error", "Enter valid numeric data")

    def clear(self):
        self.camera_types = []; [self.tree.delete(i) for i in self.tree.get_children()]

    def optimize(self):
        if not self.camera_types: return
        parity = self.raid_var.get()
        
        # Create a flat list of cameras (e.g., 24 individual objects)
        flat_cams = []
        for ct in self.camera_types:
            for _ in range(ct['qty']):
                flat_cams.append(ct)
        
        total_c = len(flat_cams)
        best_overall_cost = float('inf')
        best_overall_sol = None

        for model in RAID_DATA:
            # Check single unit vs dual unit
            for nvr_qty in [1, 2]:
                if nvr_qty == 1:
                    total_m = sum(c['tp'] for c in flat_cams)
                    total_t = sum(c['tb'] for c in flat_cams)
                    if total_c <= model[2] and total_m <= model[3]:
                        h_cost, h_cfg = get_best_hdd(total_t, model[4], parity)
                        if h_cfg:
                            if (model[5] + h_cost) < best_overall_cost:
                                best_overall_cost = model[5] + h_cost
                                best_overall_sol = {"model": model, "units": [{"cams": flat_cams, "h": h_cfg}]}
                
                elif nvr_qty == 2:
                    # BRUTE FORCE: Split at every possible point (i)
                    for i in range(1, total_c):
                        list1 = flat_cams[:i]
                        list2 = flat_cams[i:]
                        
                        m1, t1 = sum(c['tp'] for c in list1), sum(c['tb'] for c in list1)
                        m2, t2 = sum(c['tp'] for c in list2), sum(c['tb'] for c in list2)
                        
                        # Validate NVR capacity
                        if len(list1) <= model[2] and m1 <= model[3] and len(list2) <= model[2] and m2 <= model[3]:
                            c_h1, h1 = get_best_hdd(t1, model[4], parity)
                            c_h2, h2 = get_best_hdd(t2, model[4], parity)
                            
                            if h1 and h2:
                                total_run = (model[5] * 2) + c_h1 + c_h2
                                if total_run < best_overall_cost:
                                    best_overall_cost = total_run
                                    best_overall_sol = {
                                        "model": model, 
                                        "units": [{"cams": list1, "h": h1}, {"cams": list2, "h": h2}]
                                    }

        self.display(best_overall_sol, best_overall_cost)

    def display(self, sol, total_cost):
        self.txt.config(state="normal"); self.txt.delete("1.0", tk.END)
        if not sol:
            self.txt.insert(tk.END, "No valid solution found.")
        else:
            self.txt.insert(tk.END, f"--- ABSOLUTE OPTIMAL SOLUTION (COST-DRIVEN) ---\n")
            self.txt.insert(tk.END, f"PROJECT GRAND TOTAL: ${total_cost:,.2f}\n" + "="*80 + "\n")
            
            for i, u in enumerate(sol['units']):
                self.txt.insert(tk.END, f"UNIT {i+1}: {sol['model'][0]} ({sol['model'][1]})\n")
                
                # Summary of cameras on this unit
                counts = defaultdict(int)
                for c in u['cams']: counts[f"{c['tp']} Mbps, {c['gb']} GB"] += 1
                
                self.txt.insert(tk.END, f"  CAMERA ASSIGNMENT:\n")
                for desc, qty in counts.items():
                    self.txt.insert(tk.END, f"    - {qty} x {desc}\n")
                
                h = u['h']
                self.txt.insert(tk.END, f"  DRIVE BOM:\n")
                self.txt.insert(tk.END, f"    - {h['qty']} x {h['cap']} TB Drives\n")
                self.txt.insert(tk.END, f"    - Usable Storage: {h['usable']:.2f} TB\n")
                self.txt.insert(tk.END, f"    - Unit Subtotal: ${sol['model'][5] + h['cost']:,.2f}\n" + "-"*65 + "\n")
        self.txt.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("900x900"); app = CCTVApp(root); root.mainloop()
