import tkinter as tk
from tkinter import ttk, messagebox
import math
from collections import defaultdict

# ------------------------------------------------------------
# 1. HARDWARE DATA
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

# Initial Default HDD Prices
DEFAULT_HDD_PRICES = {
    1: 63.15, 2: 94.71, 3: 105.26, 4: 168.42, 6: 215.78,
    8: 306.42, 10: 355.53, 12: 442.10, 14: 617.98, 18: 720.55,
    22: 685.28, 24: 863.48, 26: 822.88
}

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Absolute Brute-Force Optimizer v3.0")
        self.camera_types = [] 
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        # --- TAB CONTROL ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_calc = ttk.Frame(self.notebook)
        self.tab_prices = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_calc, text=" Optimizer ")
        self.notebook.add(self.tab_prices, text=" Manage HDD Prices ")

        self.setup_calc_tab()
        self.setup_price_tab()

    def setup_calc_tab(self):
        # --- CAMERA INPUT ---
        input_frame = ttk.LabelFrame(self.tab_calc, text=" Camera Configuration ", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        fields = [("Name:", 15), ("Qty:", 5), ("Mbps:", 5), ("GB:", 8)]
        self.entries = {}
        for i, (label, width) in enumerate(fields):
            ttk.Label(input_frame, text=label).grid(row=0, column=i*2)
            ent = ttk.Entry(input_frame, width=width)
            ent.grid(row=0, column=i*2+1, padx=5)
            self.entries[label] = ent

        ttk.Button(input_frame, text="Add Camera", command=self.add_cam).grid(row=0, column=8, padx=5)
        ttk.Button(input_frame, text="Reset", command=self.clear).grid(row=0, column=9)

        # --- DATA TABLE ---
        self.tree = ttk.Treeview(self.tab_calc, columns=("Name", "Qty", "Mbps", "GB"), show="headings", height=5)
        for c in ["Name", "Qty", "Mbps", "GB"]: self.tree.heading(c, text=c)
        self.tree.pack(fill="x", padx=10, pady=5)

        # --- MODE SELECTION ---
        mode_frame = ttk.Frame(self.tab_calc)
        mode_frame.pack(pady=5)
        self.calc_mode = tk.StringVar(value="RAID5")
        modes = [("RAID 5", "RAID5"), ("RAID 6", "RAID6"), ("JBOD", "JBOD"), ("Holis", "HOLIS")]
        for i, (txt, val) in enumerate(modes):
            ttk.Radiobutton(mode_frame, text=txt, variable=self.calc_mode, value=val).grid(row=0, column=i, padx=10)

        ttk.Button(self.tab_calc, text="GENERATE CHEAPEST BOM", command=self.optimize).pack(pady=10)

        self.txt = tk.Text(self.tab_calc, height=20, width=95, state="disabled", font=("Consolas", 10), bg="#0a0a0a", fg="#00FF41")
        self.txt.pack(padx=10, pady=10)

    def setup_price_tab(self):
        ttk.Label(self.tab_prices, text="Update current HDD prices below. These will be used for calculations.", padding=10).pack()
        
        container = ttk.Frame(self.tab_prices)
        container.pack(fill="both", expand=True, padx=20)

        self.price_entries = {}
        # Create a grid for prices
        for i, (size, price) in enumerate(sorted(self.hdd_prices.items())):
            row, col = divmod(i, 3)
            lbl = ttk.Label(container, text=f"{size} TB Price ($):")
            lbl.grid(row=row, column=col*2, padx=5, pady=5, sticky="e")
            ent = ttk.Entry(container, width=10)
            ent.insert(0, f"{price:.2f}")
            ent.grid(row=row, column=col*2+1, padx=5, pady=5, sticky="w")
            self.price_entries[size] = ent

        ttk.Button(self.tab_prices, text="Save Prices", command=self.save_prices).pack(pady=20)

    def save_prices(self):
        try:
            for size, entry in self.price_entries.items():
                self.hdd_prices[size] = float(entry.get())
            messagebox.showinfo("Success", "HDD Prices updated successfully!")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for all prices.")

    def add_cam(self):
        try:
            n = self.entries["Name:"].get()
            q = int(self.entries["Qty:"].get())
            m = float(self.entries["Mbps:"].get())
            g = float(self.entries["GB:"].get())
            if not n: n = f"Type {len(self.camera_types)+1}"
            self.camera_types.append({'name': n, 'qty': q, 'tp': m, 'tb': g/1024, 'gb': g})
            self.tree.insert("", "end", values=(n, q, m, g))
            for ent in self.entries.values(): ent.delete(0, tk.END)
        except: messagebox.showerror("Error", "Check numeric values")

    def clear(self):
        self.camera_types = []; [self.tree.delete(i) for i in self.tree.get_children()]

    def get_best_hdd(self, required_tb, slots, parity):
        if required_tb <= 0: return 0, {"qty": 0, "cap": 0, "cost": 0, "usable": 0}
        best_cost = float('inf')
        best_cfg = None
        # Use live prices from the tab
        current_list = sorted(self.hdd_prices.items())
        for cap, price in current_list:
            data_drives = math.ceil(required_tb / cap)
            total_drives = data_drives + parity
            if total_drives <= slots and data_drives >= 1:
                total_price = total_drives * price
                if total_price < best_cost:
                    best_cost = total_price
                    best_cfg = {"qty": total_drives, "cap": cap, "cost": total_price, "usable": data_drives * cap}
        return best_cost, best_cfg

    def optimize(self):
        if not self.camera_types: return
        mode = self.calc_mode.get()
        if "RAID" in mode: hw, parity = RAID_DATA, (1 if mode == "RAID5" else 2)
        elif mode == "JBOD": hw, parity = JBOD_DATA, 0
        else: hw, parity = HOLIS_DATA, 0
        
        flat_cams = []
        for ct in self.camera_types:
            for _ in range(ct['qty']): flat_cams.append(ct)
        
        total_c = len(flat_cams)
        best_overall_cost = float('inf')
        best_overall_sol = None

        for model in hw:
            for nvr_qty in [1, 2]:
                if nvr_qty == 1:
                    total_m, total_t = sum(c['tp'] for c in flat_cams), sum(c['tb'] for c in flat_cams)
                    if total_c <= model[2] and total_m <= model[3]:
                        h_cost, h_cfg = self.get_best_hdd(total_t, model[4], parity)
                        if h_cfg and (model[5] + h_cost) < best_overall_cost:
                            best_overall_cost = model[5] + h_cost
                            best_overall_sol = {"model": model, "units": [{"cams": flat_cams, "h": h_cfg, "req": total_t}]}
                
                elif nvr_qty == 2:
                    for i in range(1, total_c):
                        l1, l2 = flat_cams[:i], flat_cams[i:]
                        m1, t1, m2, t2 = sum(c['tp'] for l in [l1] for c in l), sum(c['tb'] for l in [l1] for c in l), \
                                         sum(c['tp'] for l in [l2] for c in l), sum(c['tb'] for l in [l2] for c in l)
                        
                        if len(l1) <= model[2] and m1 <= model[3] and len(l2) <= model[2] and m2 <= model[3]:
                            c_h1, h1 = self.get_best_hdd(t1, model[4], parity)
                            c_h2, h2 = self.get_best_hdd(t2, model[4], parity)
                            if h1 and h2:
                                total_run = (model[5] * 2) + c_h1 + c_h2
                                if total_run < best_overall_cost:
                                    best_overall_cost = total_run
                                    best_overall_sol = {"model": model, "units": [{"cams": l1, "h": h1, "req": t1}, {"cams": l2, "h": h2, "req": t2}]}

        self.display(best_overall_sol, best_overall_cost, mode)

    def display(self, sol, total_cost, mode):
        self.txt.config(state="normal"); self.txt.delete("1.0", tk.END)
        if not sol:
            self.txt.insert(tk.END, "No valid configuration found.")
        else:
            self.txt.insert(tk.END, f"--- {mode} ABSOLUTE OPTIMAL BOM ---\n")
            self.txt.insert(tk.END, f"TOTAL ESTIMATED PROJECT COST: ${total_cost:,.2f}\n" + "="*80 + "\n")
            for i, u in enumerate(sol['units']):
                self.txt.insert(tk.END, f"UNIT {i+1}: {sol['model'][0]} ({sol['model'][1]})\n")
                self.txt.insert(tk.END, f"  [ STORAGE REQUIRED: {u['req']:.2f} TB ]\n")
                counts = defaultdict(int)
                for c in u['cams']: counts[c['name']] += 1
                self.txt.insert(tk.END, f"  CAMERA ASSIGNMENT:\n")
                for name, qty in counts.items(): self.txt.insert(tk.END, f"    > {qty} x {name}\n")
                h = u['h']
                self.txt.insert(tk.END, f"  DRIVE BOM:\n")
                self.txt.insert(tk.END, f"    > {h['qty']} x {h['cap']} TB (Usable: {h['usable']:.2f} TB)\n")
                self.txt.insert(tk.END, f"    > Subtotal Unit {i+1}: ${sol['model'][5] + h['cost']:,.2f}\n" + "-"*65 + "\n")
        self.txt.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("900x900"); app = CCTVApp(root); root.mainloop()
