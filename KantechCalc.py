import tkinter as tk
from tkinter import ttk, messagebox
import math
from collections import defaultdict

# ------------------------------------------------------------
# 1. UPDATED HARDWARE DATA
# ------------------------------------------------------------
RAID_DATA = [
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
    ["2U Rack 175 Ch", "ADVER02RDK", 175, 1000, 12, 13854.20],
    ["2U Rack 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

JBOD_DATA = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50],
    ["1U RAID (JBOD Mode)", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 200 Ch (JBOD Mode)", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 9999, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 9999, 1, 770.85],
]

DEFAULT_HDD_PRICES = {
    1: 93.75, 2: 122.95, 3: 136.5, 4: 218.75, 6: 281.25,
    8: 395.85, 10: 416.7, 12: 687.50, 14: 1041.7, 18: 1052.1,
    22: 1145.85, 24: 1447.95, 26: 1700
}

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 0: return 0, {"qty": 0, "cap": 0, "cost": 0, "usable": 0}
    best_h_cost = float('inf')
    best_h_cfg = None
    for cap, price in sorted(price_dict.items()):
        data_drives = math.ceil(required_tb / cap)
        total_drives = data_drives + parity
        if total_drives <= slots and data_drives >= 1:
            total_price = total_drives * price
            if total_price < best_h_cost:
                best_h_cost = total_price
                best_h_cfg = {"qty": total_drives, "cap": cap, "cost": total_price, "usable": data_drives * cap}
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ULTIMATE CHEAPEST SOLUTION FINDER")
        self.camera_types = [] 
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2 = ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" Optimizer "); self.nb.add(self.t2, text=" HDD Prices ")
        
        # Inputs
        f = ttk.Frame(self.t1, padding=10)
        f.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f, width=10); e.grid(row=0, column=i*2+1, padx=5)
            self.ents[label] = e
        ttk.Button(f, text="Add", command=self.add_c).grid(row=0, column=8)
        
        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=5)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="x", padx=10)

        self.mode = tk.StringVar(value="RAID5")
        mf = ttk.Frame(self.t1)
        mf.pack(pady=5)
        for t, v in [("RAID 5","RAID5"), ("RAID 6","RAID6"), ("JBOD","JBOD"), ("Holis","HOLIS")]:
            ttk.Radiobutton(mf, text=t, variable=self.mode, value=v).pack(side="left", padx=10)

        ttk.Button(self.t1, text="FIND ABSOLUTE CHEAPEST TOTAL COST", command=self.optimize).pack(pady=5)
        self.txt = tk.Text(self.t1, bg="black", fg="lightgreen", font=("Consolas", 10))
        self.txt.pack(fill="both", expand=True, padx=10, pady=5)

        # Price Tab
        pf = ttk.Frame(self.t2, padding=20)
        pf.pack()
        self.p_ents = {}
        for i, (s, p) in enumerate(sorted(self.hdd_prices.items())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{s}TB $:").grid(row=r, column=c*2)
            e = ttk.Entry(pf, width=8); e.insert(0, f"{p:.2f}"); e.grid(row=r, column=c*2+1, pady=2)
            self.p_ents[s] = e
        ttk.Button(self.t2, text="Save Prices", command=self.save_p).pack()

    def add_c(self):
        try:
            d = [self.ents[k].get() for k in ["Name","Qty","Mbps","GB"]]
            self.camera_types.append({'n': d[0], 'q': int(d[1]), 'm': float(d[2]), 't': float(d[3])/1024})
            self.tree.insert("", "end", values=d)
        except: pass

    def save_p(self):
        for s, e in self.p_ents.items(): self.hdd_prices[s] = float(e.get())

    def optimize(self):
        if not self.camera_types: return
        m = self.mode.get()
        if "RAID" in m: hw, p = RAID_DATA, (1 if m=="RAID5" else 2)
        elif m == "JBOD": hw, p = JBOD_DATA, 0
        else: hw, p = HOLIS_DATA, 0

        flat = []
        for c in self.camera_types:
            for _ in range(c['q']): flat.append(c)
        
        best_total = float('inf')
        best_sol = None

        # Absolute Brute Force: Check every NVR model vs every other NVR model
        for n_qty in [1, 2]:
            for m1 in hw:
                # 1 UNIT PATH
                if n_qty == 1:
                    tm, tt = sum(c['m'] for c in flat), sum(c['t'] for c in flat)
                    if len(flat) <= m1[2] and tm <= m1[3]:
                        hc, hf = get_best_hdd(tt, m1[4], p, self.hdd_prices)
                        if hf and (m1[5] + hc) < best_total:
                            best_total = m1[5] + hc
                            best_sol = [{"m": m1, "c": flat, "h": hf, "tt": tt, "tm": tm}]
                # 2 UNIT PATH
                else:
                    for m2 in hw:
                        for i in range(1, len(flat)):
                            l1, l2 = flat[:i], flat[i:]
                            tm1, tt1, tm2, tt2 = sum(x['m'] for x in l1), sum(x['t'] for x in l1), sum(x['m'] for x in l2), sum(x['t'] for x in l2)
                            if len(l1) <= m1[2] and tm1 <= m1[3] and len(l2) <= m2[2] and tm2 <= m2[3]:
                                hc1, hf1 = get_best_hdd(tt1, m1[4], p, self.hdd_prices)
                                hc2, hf2 = get_best_hdd(tt2, m2[4], p, self.hdd_prices)
                                if hf1 and hf2 and (m1[5] + m2[5] + hc1 + hc2) < best_total:
                                    best_total = m1[5] + m2[5] + hc1 + hc2
                                    best_sol = [{"m": m1, "c": l1, "h": hf1, "tt": tt1, "tm": tm1},
                                                {"m": m2, "c": l2, "h": hf2, "tt": tt2, "tm": tm2}]

        self.show(best_sol, best_total)

    def show(self, sol, total):
        self.txt.delete("1.0", tk.END)
        if not sol: self.txt.insert("1.0", "No solution found.")
        else:
            self.txt.insert("1.0", f"--- CHEAPEST OVERALL SOLUTION: ${total:,.2f} ---\n\n")
            for i, u in enumerate(sol):
                self.txt.insert(tk.END, f"UNIT {i+1}: {u['m'][0]} (${u['m'][5]:,.2f})\n")
                self.txt.insert(tk.END, f"  Load: {u['tm']:.1f}Mbps | Storage: {u['tt']:.2f}TB\n")
                self.txt.insert(tk.END, f"  Drives: {u['h']['qty']} x {u['h']['cap']}TB (Cost: ${u['h']['cost']:,.2f})\n")
                self.txt.insert(tk.END, f"  Subtotal: ${u['m'][5]+u['h']['cost']:,.2f}\n" + "-"*40 + "\n")

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("800x700"); app = CCTVApp(r); r.mainloop()
