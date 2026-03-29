import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math

# ------------------------------------------------------------
# 1. HARDWARE POOLS
# ------------------------------------------------------------
RAID_DATA = [
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
    ["2U Rack 175 Ch", "ADVER02RDK", 175, 1000, 12, 13854.20],
    ["2U Rack 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

JBOD_ONLY_DATA = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 160, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 320, 2, 770.85],
]

ALL_MODELS = RAID_DATA + JBOD_ONLY_DATA + HOLIS_DATA

DEFAULT_HDD_PRICES = {
    1: 93.75, 2: 122.95, 4: 218.75, 6: 281.25, 8: 395.85, 
    10: 416.7, 12: 687.50, 14: 1041.7, 18: 1052.1, 22: 1145.85, 
    24: 1447.95, 26: 1700.00
}

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 1e-6: return 0, {"qty": 0, "cap": 0, "cost": 0, "total_tb": 0}
    best_h_cost = float('inf')
    best_h_cfg = None
    for cap, price in sorted(price_dict.items()):
        if price <= 0: continue
        min_data = 2 if parity > 0 else 1
        data_drives = max(math.ceil(required_tb / cap), min_data)
        total_drives = data_drives + parity
        if total_drives <= slots:
            total_price = total_drives * price
            if total_price < best_h_cost:
                best_h_cost, best_h_cfg = total_price, {"qty": total_drives, "cap": cap, "cost": total_price, "total_tb": (data_drives * cap)}
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER V19 - MANUAL & AUTO OPTIMIZER")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root); self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1 = ttk.Frame(self.nb) # Cam Management
        self.t2 = ttk.Frame(self.nb) # Auto Report
        self.t4 = ttk.Frame(self.nb) # Manual Selection (New)
        self.t3 = ttk.Frame(self.nb) # HDD Settings
        
        self.nb.add(self.t1, text=" 1. Cameras "); self.nb.add(self.t2, text=" 2. Auto Audit "); 
        self.nb.add(self.t4, text=" 3. Manual Selection "); self.nb.add(self.t3, text=" 4. HDD Settings ")

        # --- TAB 1: CAMERA MGMT ---
        f_in = ttk.Frame(self.t1, padding=10); f_in.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=12); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        
        btn_f = ttk.Frame(self.t1, padding=5); btn_f.pack(fill="x", padx=10)
        ttk.Button(btn_f, text="Add/Update Row", command=self.save_camera).pack(side="left", padx=2)
        ttk.Button(btn_f, text="Delete Selected", command=self.delete_camera).pack(side="left", padx=2)

        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=15)
        for c, h in zip(self.tree["columns"], ["Type Name","Qty","Mbps","GB/Cam"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 2: AUTO AUDIT ---
        f_b = ttk.Frame(self.t2, padding=15); f_b.pack(fill="x")
        self.mode_var = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly").pack(side="left", padx=5)
        ttk.Button(f_b, text="FIND CHEAPEST AUTO", command=lambda: self.run_logic(auto=True)).pack(side="left", padx=5)
        
        self.res_txt = tk.Text(self.t2, bg="#ffffff", fg="#000000", font=("Consolas", 10))
        self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 4: MANUAL SELECTION (THE NEW REQUEST) ---
        f_m = ttk.Frame(self.t4, padding=20); f_m.pack(fill="x")
        ttk.Label(f_m, text="Choose NVR Model:").grid(row=0, column=0, sticky="w")
        self.manual_nvr = tk.StringVar()
        self.nvr_combo = ttk.Combobox(f_m, textvariable=self.manual_nvr, width=40, state="readonly")
        self.nvr_combo['values'] = [f"{m[1]} ({m[0]})" for m in ALL_MODELS]
        self.nvr_combo.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(f_m, text="Choose Recording Method:").grid(row=1, column=0, sticky="w")
        self.manual_mode = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_m, textvariable=self.manual_mode, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly").grid(row=1, column=1, padx=10, pady=5)

        ttk.Button(f_m, text="CALCULATE THIS SELECTION", command=lambda: self.run_logic(auto=False)).grid(row=2, column=1, pady=15, sticky="w")

        self.man_txt = tk.Text(self.t4, bg="#f0f0f0", fg="#000000", font=("Consolas", 10))
        self.man_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 3: HDD SETTINGS ---
        pf = ttk.Frame(self.t3, padding=20); pf.pack(fill="both", expand=True)
        self.p_ents = {}
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{cap}TB Drive $:").grid(row=r, column=c*2, sticky="e", pady=5)
            e = ttk.Entry(pf, width=15); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1, padx=10, pady=5)
            self.p_ents[cap] = e
        ttk.Button(self.t3, text="SAVE HDD PRICES", command=self.update_prices).pack(pady=20)

    # ------------------------------------------------------------
    # LOGIC HELPERS
    # ------------------------------------------------------------
    def update_prices(self):
        try:
            for cap, entry in self.p_ents.items(): self.hdd_prices[cap] = float(entry.get())
            messagebox.showinfo("Success", "Prices Updated.")
        except: messagebox.showerror("Error", "Check formats.")

    def save_camera(self):
        n, q, m, g = self.ents["Name"].get(), self.ents["Qty"].get(), self.ents["Mbps"].get(), self.ents["GB"].get()
        if n: self.tree.insert("", "end", values=(n, q, m, g))

    def delete_camera(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def run_logic(self, auto=True):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": str(v[0]), "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        
        if not cams: return
        t_c, t_m, t_t = sum(c['qty'] for c in cams), sum(c['qty']*c['mbps'] for c in cams), sum(c['qty']*c['tb'] for c in cams)
        
        if auto:
            mode = self.mode_var.get()
            if mode == "Holis": hw_pool, parity = HOLIS_DATA, 0
            elif mode == "RAID 5": hw_pool, parity = RAID_DATA, 1
            elif mode == "RAID 6": hw_pool, parity = RAID_DATA, 2
            else: hw_pool, parity = RAID_DATA + JBOD_ONLY_DATA, 0
        else:
            # Manual Mode: Filter to the one selected NVR
            selected_name = self.manual_nvr.get()
            hw_pool = [m for m in ALL_MODELS if f"{m[1]} ({m[0]})" == selected_name]
            mode = self.manual_mode.get()
            parity = 1 if mode == "RAID 5" else 2 if mode == "RAID 6" else 0

        best_cost, best_cfg = float('inf'), None

        for m in hw_pool:
            # Try Single Unit
            if t_c <= m[2] and t_m <= m[3]:
                h_c, h = get_best_hdd(t_t, m[4], parity, self.hdd_prices)
                if h and (m[5] + h_c) < best_cost:
                    best_cost, best_cfg = m[5]+h_c, {"m": m, "units": [{"mb":t_m, "tb":t_t, "h":h, "ratio":1.0}]}
            
            # Try Dual Unit split
            for i in range(1, t_c):
                r = i/t_c
                m1, t1, m2, t2 = t_m*r, t_t*r, t_m*(1-r), t_t*(1-r)
                if i > m[2] or (t_c-i) > m[2] or m1 > m[3] or m2 > m[3]: continue
                c1, h1 = get_best_hdd(t1, m[4], parity, self.hdd_prices)
                c2, h2 = get_best_hdd(t2, m[4], parity, self.hdd_prices)
                if h1 and h2 and (m[5]*2 + c1 + c2) < best_cost:
                    best_cost, best_cfg = m[5]*2 + c1 + c2, {"m": m, "units": [{"h":h1,"mb":m1,"tb":t1,"ratio":r}, {"h":h2,"mb":m2,"tb":t2,"ratio":1-r}]}

        target_text = self.res_txt if auto else self.man_txt
        target_text.delete("1.0", tk.END)
        
        if not best_cfg:
            target_text.insert(tk.END, "CRITICAL: The selected NVR cannot handle this camera load/storage requirement.")
            return

        out = f"--- {'AUTO' if auto else 'MANUAL'} PERMUTATION REPORT ({mode}) ---\n"
        out += f"GRAND TOTAL: ${best_cost:,.2f}\n" + "="*65 + "\n\n"
        for idx, u in enumerate(best_cfg['units']):
            out += f"NVR UNIT #{idx+1} | {best_cfg['m'][1]} ({best_cfg['m'][0]})\n" + "-"*65 + "\n"
            for c in cams:
                tk_amt = round(c['qty'] * u['ratio'])
                if tk_amt > 0: out += f"  > {c['name']}: {tk_amt} units\n"
            out += f"\nTHROUGHPUT: {u['mb']:.1f} Mbps / {best_cfg['m'][3]} Mbps\n"
            out += f"STORAGE: {u['h']['qty']} x {u['h']['cap']}TB | Usable: {u['h']['total_tb']:.2f} TB (Req: {u['tb']:.2f} TB)\n\n" + "="*65 + "\n\n"
        
        target_text.insert(tk.END, out)

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("950x850"); app = CCTVApp(r); r.mainloop()
