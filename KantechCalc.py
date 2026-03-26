import tkinter as tk
from tkinter import ttk, messagebox
import math
from collections import defaultdict

# ------------------------------------------------------------
# 1. HARDWARE DATA (Corrected Mbps Limits)
# ------------------------------------------------------------
# Format: [Name, Part Number, Max Cam, Max Mbps, Slots, Price]
RAID_DATA = [
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
    ["2U Rack Mount 175 Ch", "ADVER02RDK", 175, 1000, 12, 13854.20],
    ["2U Rack Mount 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

JBOD_DATA = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50],
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
    ["2U Rack Mount 175 Ch", "ADVER02RDK", 175, 1000, 12, 13854.20],
    ["2U Rack Mount 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 9999, 1, 520.85], # NO LIMITS
    ["Holis 16 Ch", "HRN-16023P", 16, 9999, 1, 770.85], # NO LIMITS
]

DEFAULT_HDD_PRICES = {
    1: 63.15, 2: 94.71, 3: 105.26, 4: 168.42, 6: 215.78,
    8: 306.42, 10: 355.53, 12: 442.10, 14: 617.98, 18: 720.55,
    22: 685.28, 24: 863.48, 26: 822.88
}

# ------------------------------------------------------------
# 2. CALCULATION ENGINE
# ------------------------------------------------------------

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 0: return 0, {"qty": 0, "cap": 0, "cost": 0, "usable": 0}
    best_cost = float('inf')
    best_cfg = None
    for cap, price in sorted(price_dict.items()):
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
        self.root.title("CCTV Absolute Brute-Force Optimizer v4.1")
        self.camera_types = [] 
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        self.tab_calc, self.tab_prices = ttk.Frame(self.notebook), ttk.Frame(self.notebook)
        self.notebook.add(self.tab_calc, text=" Optimizer "); self.notebook.add(self.tab_prices, text=" HDD Prices ")
        self.setup_calc_tab(); self.setup_price_tab()

    def setup_calc_tab(self):
        input_frame = ttk.LabelFrame(self.tab_calc, text=" Camera Configuration ", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)
        
        f_names = ["Name", "Qty", "Mbps", "GB"]
        self.entries = {}
        for i, f in enumerate(f_names):
            ttk.Label(input_frame, text=f"{f}:").grid(row=0, column=i*2)
            ent = ttk.Entry(input_frame, width=10)
            ent.grid(row=0, column=i*2+1, padx=5)
            self.entries[f] = ent

        ttk.Button(input_frame, text="Add", command=self.add_cam).grid(row=0, column=8, padx=5)
        ttk.Button(input_frame, text="Reset", command=self.clear).grid(row=0, column=9)

        self.tree = ttk.Treeview(self.tab_calc, columns=f_names, show="headings", height=5)
        for c in f_names: self.tree.heading(c, text=c)
        self.tree.pack(fill="x", padx=10, pady=5)

        self.calc_mode = tk.StringVar(value="RAID5")
        m_frame = ttk.Frame(self.tab_calc)
        m_frame.pack(pady=5)
        for i, (t, v) in enumerate([("RAID 5", "RAID5"), ("RAID 6", "RAID6"), ("JBOD", "JBOD"), ("Holis", "HOLIS")]):
            ttk.Radiobutton(m_frame, text=t, variable=self.calc_mode, value=v).grid(row=0, column=i, padx=10)

        ttk.Button(self.tab_calc, text="CALCULATE CHEAPEST BOM", command=self.optimize).pack(pady=5)
        self.txt = tk.Text(self.tab_calc, height=22, width=95, font=("Consolas", 10), bg="#000", fg="#0f0", state="disabled")
        self.txt.pack(padx=10, pady=5)

    def setup_price_tab(self):
        container = ttk.Frame(self.tab_prices, padding=20)
        container.pack()
        self.price_entries = {}
        for i, (size, price) in enumerate(sorted(self.hdd_prices.items())):
            r, c = divmod(i, 2)
            ttk.Label(container, text=f"{size} TB Price ($):").grid(row=r, column=c*2, padx=5, pady=2, sticky="e")
            ent = ttk.Entry(container, width=10); ent.insert(0, f"{price:.2f}")
            ent.grid(row=r, column=c*2+1, padx=5, pady=2)
            self.price_entries[size] = ent
        ttk.Button(self.tab_prices, text="Save Prices", command=self.save_p).pack(pady=10)

    def save_p(self):
        try:
            for s, e in self.price_entries.items(): self.hdd_prices[s] = float(e.get())
            messagebox.showinfo("Saved", "Prices Updated")
        except: messagebox.showerror("Error", "Invalid Input")

    def add_cam(self):
        try:
            n, q, m, g = self.entries["Name"].get(), int(self.entries["Qty"].get()), float(self.entries["Mbps"].get()), float(self.entries["GB"].get())
            self.camera_types.append({'name': n or f"Type {len(self.camera_types)+1}", 'qty': q, 'tp': m, 'tb': g/1024, 'gb': g})
            self.tree.insert("", "end", values=(n, q, m, g))
        except: pass

    def clear(self):
        self.camera_types = []; [self.tree.delete(i) for i in self.tree.get_children()]

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
        best_cost = float('inf')
        best_sol = None

        for nvr_qty in [1, 2]:
            for m1 in hw:
                for m2 in hw if nvr_qty == 2 else [None]:
                    if nvr_qty == 1:
                        t_m, t_t = sum(c['tp'] for c in flat_cams), sum(c['tb'] for c in flat_cams)
                        if total_c <= m1[2] and t_m <= m1[3]: # RESTRICTION RESTORED
                            h_c, h_f = get_best_hdd(t_t, m1[4], parity, self.hdd_prices)
                            if h_f and (m1[5] + h_c) < best_cost:
                                best_cost = m1[5] + h_c
                                best_sol = {"units": [{"m": m1, "cams": flat_cams, "h": h_f, "req": t_t}]}
                    else:
                        for i in range(1, total_c):
                            l1, l2 = flat_cams[:i], flat_cams[i:]
                            m1_t, t1 = sum(c['tp'] for c in l1), sum(c['tb'] for c in l1)
                            m2_t, t2 = sum(c['tp'] for c in l2), sum(c['tb'] for c in l2)
                            if len(l1) <= m1[2] and m1_t <= m1[3] and len(l2) <= m2[2] and m2_t <= m2[3]: # RESTRICTION RESTORED
                                hc1, hf1 = get_best_hdd(t1, m1[4], parity, self.hdd_prices)
                                hc2, hf2 = get_best_hdd(t2, m2[4], parity, self.hdd_prices)
                                if hf1 and hf2:
                                    total_run = m1[5] + m2[5] + hc1 + hc2
                                    if total_run < best_cost:
                                        best_cost = total_run
                                        best_sol = {"units": [{"m": m1, "cams": l1, "h": hf1, "req": t1}, {"m": m2, "cams": l2, "h": hf2, "req": t2}]}

        self.display(best_sol, best_cost, mode)

    def display(self, sol, cost, mode):
        self.txt.config(state="normal"); self.txt.delete("1.0", tk.END)
        if not sol: self.txt.insert(tk.END, "No valid configuration. (Check Mbps or Cam Count limits)")
        else:
            self.txt.insert(tk.END, f"--- {mode} OPTIMIZED BILL OF MATERIALS | TOTAL: ${cost:,.2f} ---\n" + "="*80 + "\n")
            for i, u in enumerate(sol['units']):
                self.txt.insert(tk.END, f"UNIT {i+1}: {u['m'][0]} ({u['m'][1]})\n")
                self.txt.insert(tk.END, f"  Storage Required: {u['req']:.2f} TB\n")
                counts = defaultdict(int)
                for c in u['cams']: counts[c['name']] += 1
                self.txt.insert(tk.END, "  Cameras:\n")
                for n, q in counts.items(): self.txt.insert(tk.END, f"    > {q} x {n}\n")
                self.txt.insert(tk.END, f"  Drive: {u['h']['qty']} x {u['h']['cap']} TB (Usable: {u['h']['usable']:.2f} TB)\n")
                self.txt.insert(tk.END, f"  Subtotal: ${u['m'][5] + u['h']['cost']:,.2f}\n" + "-"*70 + "\n")
        self.txt.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("900x850"); app = CCTVApp(root); root.mainloop()
