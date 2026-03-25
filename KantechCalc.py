import tkinter as tk
from tkinter import ttk, messagebox
import math
from collections import defaultdict

# ------------------------------------------------------------
# 1. HARDWARE & DRIVE DATA
# ------------------------------------------------------------
RAID_DATA = [
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
]

JBOD_DATA = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 80, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 160, 1, 770.85],
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
                best_cfg = {"qty": total_drives, "cap": cap, "cost": total_price, "usable": data_drives * cap}
    return best_cost, best_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Absolute Brute-Force Optimizer")
        self.camera_types = [] 
        self.setup_ui()

    def setup_ui(self):
        # --- CAMERA INPUT ---
        input_frame = ttk.LabelFrame(self.root, text=" Camera Configuration ", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Name:").grid(row=0, column=0)
        self.e_name = ttk.Entry(input_frame, width=15); self.e_name.grid(row=0, column=1, padx=5)
        ttk.Label(input_frame, text="Qty:").grid(row=0, column=2)
        self.e_qty = ttk.Entry(input_frame, width=5); self.e_qty.grid(row=0, column=3, padx=5)
        ttk.Label(input_frame, text="Mbps:").grid(row=0, column=4)
        self.e_mbps = ttk.Entry(input_frame, width=5); self.e_mbps.grid(row=0, column=5, padx=5)
        ttk.Label(input_frame, text="GB:").grid(row=0, column=6)
        self.e_gb = ttk.Entry(input_frame, width=8); self.e_gb.grid(row=0, column=7, padx=5)

        ttk.Button(input_frame, text="Add Camera", command=self.add_cam).grid(row=0, column=8, padx=5)
        ttk.Button(input_frame, text="Reset", command=self.clear).grid(row=0, column=9)

        # --- DATA TABLE ---
        self.tree = ttk.Treeview(self.root, columns=("Name", "Qty", "Mbps", "GB"), show="headings", height=4)
        for c in ["Name", "Qty", "Mbps", "GB"]: self.tree.heading(c, text=c)
        self.tree.pack(fill="x", padx=10, pady=5)

        # --- MODE SELECTION ---
        mode_frame = ttk.Frame(self.root)
        mode_frame.pack(pady=5)
        self.calc_mode = tk.StringVar(value="RAID")
        ttk.Radiobutton(mode_frame, text="RAID 5 (1 Parity)", variable=self.calc_mode, value="RAID5").grid(row=0, column=0, padx=10)
        ttk.Radiobutton(mode_frame, text="RAID 6 (2 Parity)", variable=self.calc_mode, value="RAID6").grid(row=0, column=1, padx=10)
        ttk.Radiobutton(mode_frame, text="JBOD (0 Parity)", variable=self.calc_mode, value="JBOD").grid(row=0, column=2, padx=10)
        ttk.Radiobutton(mode_frame, text="Holis (0 Parity)", variable=self.calc_mode, value="HOLIS").grid(row=0, column=3, padx=10)

        ttk.Button(self.root, text="GENERATE CHEAPEST BOM", command=self.optimize).pack(pady=10)

        # --- OUTPUT CONSOLE ---
        self.txt = tk.Text(self.root, height=25, width=95, state="disabled", font=("Consolas", 10), bg="#0a0a0a", fg="#00FF41")
        self.txt.pack(padx=10, pady=10)

    def add_cam(self):
        try:
            n, q, m, g = self.e_name.get(), int(self.e_qty.get()), float(self.e_mbps.get()), float(self.e_gb.get())
            if not n: n = f"Cam Type {len(self.camera_types)+1}"
            self.camera_types.append({'name': n, 'qty': q, 'tp': m, 'tb': g/1024, 'gb': g})
            self.tree.insert("", "end", values=(n, q, m, g))
            for e in [self.e_name, self.e_qty, self.e_mbps, self.e_gb]: e.delete(0, tk.END)
        except: messagebox.showerror("Error", "Check numeric values")

    def clear(self):
        self.camera_types = []; [self.tree.delete(i) for i in self.tree.get_children()]

    def optimize(self):
        if not self.camera_types: return
        mode = self.calc_mode.get()
        
        # Set Parity and Hardware List based on mode
        if mode == "RAID5": hw, parity = RAID_DATA, 1
        elif mode == "RAID6": hw, parity = RAID_DATA, 2
        elif mode == "JBOD": hw, parity = JBOD_DATA, 0
        else: hw, parity = HOLIS_DATA, 0
        
        flat_cams = []
        for ct in self.camera_types:
            for _ in range(ct['qty']): flat_cams.append(ct)
        
        total_c = len(flat_cams)
        best_overall_cost = float('inf')
        best_overall_sol = None

        for model in hw:
            # Check for 1 NVR and 2 NVR possibilities
            for nvr_qty in [1, 2]:
                if nvr_qty == 1:
                    total_m = sum(c['tp'] for c in flat_cams)
                    total_t = sum(c['tb'] for c in flat_cams)
                    if total_c <= model[2] and total_m <= model[3]:
                        h_cost, h_cfg = get_best_hdd(total_t, model[4], parity)
                        if h_cfg:
                            if (model[5] + h_cost) < best_overall_cost:
                                best_overall_cost = model[5] + h_cost
                                best_overall_sol = {"model": model, "units": [{"cams": flat_cams, "h": h_cfg, "req": total_t}]}
                
                elif nvr_qty == 2:
                    for i in range(1, total_c):
                        list1, list2 = flat_cams[:i], flat_cams[i:]
                        m1, t1 = sum(c['tp'] for c in list1), sum(c['tb'] for c in list1)
                        m2, t2 = sum(c['tp'] for c in list2), sum(c['tb'] for c in list2)
                        
                        if len(list1) <= model[2] and m1 <= model[3] and len(list2) <= model[2] and m2 <= model[3]:
                            c_h1, h1 = get_best_hdd(t1, model[4], parity)
                            c_h2, h2 = get_best_hdd(t2, model[4], parity)
                            if h1 and h2:
                                total_run = (model[5] * 2) + c_h1 + c_h2
                                if total_run < best_overall_cost:
                                    best_overall_cost = total_run
                                    best_overall_sol = {
                                        "model": model, 
                                        "units": [{"cams": list1, "h": h1, "req": t1}, {"cams": list2, "h": h2, "req": t2}]
                                    }

        self.display(best_overall_sol, best_overall_cost, mode)

    def display(self, sol, total_cost, mode):
        self.txt.config(state="normal"); self.txt.delete("1.0", tk.END)
        if not sol:
            self.txt.insert(tk.END, "No valid hardware configuration matches these requirements.")
        else:
            self.txt.insert(tk.END, f"--- {mode} ABSOLUTE OPTIMAL BOM ---\n")
            self.txt.insert(tk.END, f"TOTAL ESTIMATED PROJECT COST: ${total_cost:,.2f}\n" + "="*80 + "\n")
            
            for i, u in enumerate(sol['units']):
                self.txt.insert(tk.END, f"UNIT {i+1}: {sol['model'][0]} ({sol['model'][1]})\n")
                self.txt.insert(tk.END, f"  [ STORAGE REQUIRED: {u['req']:.2f} TB ]\n")
                
                counts = defaultdict(int)
                for c in u['cams']: counts[c['name']] += 1
                
                self.txt.insert(tk.END, f"  CAMERA ASSIGNMENT:\n")
                for name, qty in counts.items():
                    self.txt.insert(tk.END, f"    > {qty} x {name}\n")
                
                h = u['h']
                self.txt.insert(tk.END, f"  DRIVE BOM:\n")
                self.txt.insert(tk.END, f"    > {h['qty']} x {h['cap']} TB Drives (Usable: {h['usable']:.2f} TB)\n")
                self.txt.insert(tk.END, f"    > Subtotal Unit {i+1}: ${sol['model'][5] + h['cost']:,.2f}\n" + "-"*65 + "\n")
        self.txt.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("900x900"); app = CCTVApp(root); root.mainloop()
