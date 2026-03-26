import tkinter as tk
from tkinter import ttk, messagebox
import math
from itertools import product

# ------------------------------------------------------------
# 1. HARDWARE DATA
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
    ["1U RAID (JBOD)", "ADVER00N0NP16G", 32, 100, 4, 3750.00],
    ["2U 200 Ch (JBOD)", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 160, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 320, 2, 770.85],
]

DEFAULT_HDD_PRICES = {
    1: 93.75, 2: 122.95, 4: 218.75, 6: 281.25, 8: 395.85, 
    10: 416.7, 12: 687.50, 14: 1041.7, 18: 1052.1, 22: 1145.85, 
    24: 1447.95, 26: 1700.00
}

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 0: return 0, {"qty": 0, "cap": 0, "cost": 0}
    best_h_cost = float('inf')
    best_h_cfg = None
    for cap, price in sorted(price_dict.items()):
        if price <= 0: continue
        data_drives = math.ceil(required_tb / cap)
        if parity > 0: data_drives = max(data_drives, 2)
        total_drives = data_drives + parity
        if total_drives <= slots:
            total_price = total_drives * price
            if total_price < best_h_cost:
                best_h_cost = total_price
                best_h_cfg = {"qty": total_drives, "cap": cap, "cost": total_price}
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV BRUTE-FORCE OPTIMIZER V10")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root); self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Camera Input "); self.nb.add(self.t2, text=" 2. Permutation Report "); self.nb.add(self.t3, text=" 3. HDD List ")

        f = ttk.Frame(self.t1, padding=10); f.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f, width=10); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        
        btn_f = ttk.Frame(self.t1); btn_f.pack(fill="x", padx=10)
        ttk.Button(btn_f, text="Add Camera", command=self.save_camera).pack(side="left", padx=5)
        ttk.Button(btn_f, text="Clear List", command=self.clear_all_cams).pack(side="left", padx=5)

        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=10)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        f_b = ttk.Frame(self.t2, padding=15); f_b.pack(fill="x")
        self.mode_var = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly").pack(side="left", padx=5)
        ttk.Button(f_b, text="TEST ALL DIVISIONS", command=self.find_cheapest).pack(side="left", padx=5)
        
        self.res_txt = tk.Text(self.t2, bg="#0d0d0d", fg="#00FF41", font=("Consolas", 10))
        self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)

        pf = ttk.Frame(self.t3, padding=20); pf.pack()
        self.p_ents = {}
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{cap}TB: $").grid(row=r, column=c*2)
            e = ttk.Entry(pf, width=12); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1, padx=10)
            self.p_ents[cap] = e

    def save_camera(self):
        try: self.tree.insert("", "end", values=(self.ents["Name"].get(), self.ents["Qty"].get(), self.ents["Mbps"].get(), self.ents["GB"].get()))
        except: pass

    def clear_all_cams(self):
        for i in self.tree.get_children(): self.tree.delete(i)

    def find_cheapest(self):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": v[0], "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        
        if not cams: return
        total_cams = sum(c['qty'] for c in cams)
        total_mbps = sum(c['qty'] * c['mbps'] for c in cams)
        total_tb = sum(c['qty'] * c['tb'] for c in cams)

        mode = self.mode_var.get()
        hw_list, parity = (HOLIS_DATA, 0) if mode == "Holis" else (RAID_DATA, 1) if mode == "RAID 5" else (RAID_DATA, 2) if mode == "RAID 6" else (JBOD_DATA, 0)
        
        best_overall_cost = float('inf')
        best_overall_config = None

        # Test hardware options
        for m in hw_list:
            n_qty = max(math.ceil(total_cams / m[2]), math.ceil(total_mbps / m[3]))
            
            # If we only need 1 NVR, the logic is simple
            if n_qty == 1:
                h_cost, h_cfg = get_best_hdd(total_tb, m[4], parity, self.hdd_prices)
                if h_cfg:
                    total_cost = m[5] + h_cost
                    if total_cost < best_overall_cost:
                        best_overall_cost = total_cost
                        best_overall_config = {"m": m, "n_qty": 1, "units": [{"cams": cams, "h": h_cfg}]}
            
            # If we need 2 NVRs, we test permutations (1:8, 2:7, 3:6, etc.)
            elif n_qty == 2:
                # We iterate through all possible ways to split the FIRST camera type
                # For simplicity in brute force, we split the bulk camera load
                for i in range(0, total_cams + 1):
                    # Logic: Split total load by 'i' and 'total-i'
                    ratio = i / total_cams
                    tb_1, mb_1 = total_tb * ratio, total_mbps * ratio
                    tb_2, mb_2 = total_tb * (1-ratio), total_mbps * (1-ratio)
                    
                    cost1, h1 = get_best_hdd(tb_1, m[4], parity, self.hdd_prices)
                    cost2, h2 = get_best_hdd(tb_2, m[4], parity, self.hdd_prices)
                    
                    if h1 and h2:
                        total_cost = (m[5] * 2) + cost1 + cost2
                        if total_cost < best_overall_cost:
                            best_overall_cost = total_cost
                            best_overall_config = {
                                "m": m, "n_qty": 2, 
                                "units": [
                                    {"tb": tb_1, "mb": mb_1, "h": h1, "split": i},
                                    {"tb": tb_2, "mb": mb_2, "h": h2, "split": total_cams-i}
                                ]
                            }
            # For 3+ NVRs, we fallback to balanced distribution to prevent PC crash from 1000s of permutations
            else:
                h_cost, h_cfg = get_best_hdd(total_tb / n_qty, m[4], parity, self.hdd_prices)
                if h_cfg:
                    total_cost = (m[5] + h_cost) * n_qty
                    if total_cost < best_overall_cost:
                        best_overall_cost = total_cost
                        best_overall_config = {"m": m, "n_qty": n_qty, "h_balanced": h_cfg, "cams": cams}

        self.res_txt.delete("1.0", tk.END)
        if not best_overall_config: return
        
        self.res_txt.insert(tk.END, f"--- PERMUTATION OPTIMIZED REPORT ---\n")
        self.res_txt.insert(tk.END, f"GRAND TOTAL: ${best_overall_cost:,.2f}\n")
        self.res_txt.insert(tk.END, f"HARDWARE:    {best_overall_config['m'][1]}\n\n")

        if "units" in best_overall_config:
            for idx, u in enumerate(best_overall_config['units']):
                self.res_txt.insert(tk.END, f"UNIT #{idx+1}:\n")
                self.res_txt.insert(tk.END, f"  Drives: {u['h']['qty']} x {u['h']['cap']}TB\n")
                self.res_txt.insert(tk.END, f"  Load:   ~{u['split']} cameras total\n")
                self.res_txt.insert(tk.END, "-"*30 + "\n")
        else:
            self.res_txt.insert(tk.END, f"DISTRIBUTION: {best_overall_config['n_qty']} Balanced Units\n")
            self.res_txt.insert(tk.END, f"Drives: {best_overall_config['h_balanced']['qty']} x {best_overall_config['h_balanced']['cap']}TB per unit\n")

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("900x850"); app = CCTVApp(r); r.mainloop()
