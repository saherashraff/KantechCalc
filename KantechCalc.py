import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math

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
        self.root.title("CCTV MASTER V22.1 - AUTO & MANUAL HYBRID")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root); self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t4, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Cameras "); self.nb.add(self.t2, text=" 2. Auto Audit "); 
        self.nb.add(self.t4, text=" 3. Manual Hybrid "); self.nb.add(self.t3, text=" 4. HDD Settings ")

        # --- TAB 1: CAMERAS ---
        f_in = ttk.Frame(self.t1, padding=10); f_in.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=12); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        btn_f = ttk.Frame(self.t1, padding=5); btn_f.pack(fill="x", padx=10)
        ttk.Button(btn_f, text="Add/Update Row", command=self.save_camera).pack(side="left", padx=2)
        ttk.Button(btn_f, text="Delete", command=self.delete_camera).pack(side="left", padx=2)
        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=15)
        for c, h in zip(self.tree["columns"], ["Type Name","Qty","Mbps","GB/Cam"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 2: AUTO ---
        f_b = ttk.Frame(self.t2, padding=15); f_b.pack(fill="x")
        self.mode_var = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly").pack(side="left", padx=5)
        ttk.Button(f_b, text="RUN GRANULAR AUTO AUDIT", command=lambda: self.run_logic(auto=True)).pack(side="left", padx=5)
        self.res_txt = tk.Text(self.t2, bg="#ffffff", font=("Consolas", 10)); self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 3: MANUAL HYBRID ---
        f_m = ttk.Frame(self.t4, padding=15); f_m.pack(fill="x")
        
        # NVR A Selection
        ttk.Label(f_m, text="NVR A:").grid(row=0, column=0, sticky="w")
        self.nvr_a_var = tk.StringVar()
        self.combo_a = ttk.Combobox(f_m, textvariable=self.nvr_a_var, width=30, values=[m[1] for m in ALL_MODELS], state="readonly")
        self.combo_a.grid(row=0, column=1, padx=5)
        self.mode_a = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_m, textvariable=self.mode_a, values=["RAID 5", "RAID 6", "JBOD", "Holis"], width=10, state="readonly").grid(row=0, column=2)

        # NVR B Selection
        ttk.Label(f_m, text="NVR B:").grid(row=1, column=0, sticky="w")
        self.nvr_b_var = tk.StringVar()
        self.combo_b = ttk.Combobox(f_m, textvariable=self.nvr_b_var, width=30, values=["None"] + [m[1] for m in ALL_MODELS], state="readonly")
        self.combo_b.grid(row=1, column=1, padx=5, pady=5)
        self.mode_b = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_m, textvariable=self.mode_b, values=["RAID 5", "RAID 6", "JBOD", "Holis"], width=10, state="readonly").grid(row=1, column=2)

        # Manual Cam Split
        ttk.Label(f_m, text="Cams on NVR A:").grid(row=2, column=0, sticky="w")
        self.cam_split_val = tk.IntVar(value=1)
        self.split_slider = tk.Scale(f_m, from_=1, to=100, orient="horizontal", variable=self.cam_split_val, length=200)
        self.split_slider.grid(row=2, column=1, sticky="w")

        ttk.Button(f_m, text="CALCULATE MANUAL SPLIT", command=lambda: self.run_logic(auto=False)).grid(row=3, column=1, pady=10)
        self.man_txt = tk.Text(self.t4, bg="#f5f5f5", font=("Consolas", 10)); self.man_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 4: HDD SETTINGS ---
        pf = ttk.Frame(self.t3, padding=20); pf.pack(fill="both", expand=True)
        self.p_ents = {}
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{cap}TB Drive $:").grid(row=r, column=c*2, sticky="e", pady=5)
            e = ttk.Entry(pf, width=15); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1, padx=10, pady=5); self.p_ents[cap] = e
        ttk.Button(self.t3, text="SAVE PRICES", command=self.update_prices).pack(pady=20)

    def update_prices(self):
        for cap, entry in self.p_ents.items(): self.hdd_prices[cap] = float(entry.get())
        messagebox.showinfo("Success", "Prices Updated.")

    def save_camera(self):
        n, q, m, g = self.ents["Name"].get(), self.ents["Qty"].get(), self.ents["Mbps"].get(), self.ents["GB"].get()
        if n: 
            self.tree.insert("", "end", values=(n, q, m, g))
            total_cams = sum(int(self.tree.item(i)['values'][1]) for i in self.tree.get_children())
            self.split_slider.config(to=total_cams)

    def delete_camera(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def run_logic(self, auto=True):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        
        if not cams: return
        t_c, t_m, t_t = sum(c['qty'] for c in cams), sum(c['qty']*c['mbps'] for c in cams), sum(c['qty']*c['tb'] for c in cams)
        
        best_cost, best_cfg = float('inf'), None

        if auto:
            mode = self.mode_var.get()
            if mode == "Holis": hw_list, parity = HOLIS_DATA, 0
            elif mode == "RAID 5": hw_list, parity = RAID_DATA, 1
            elif mode == "RAID 6": hw_list, parity = RAID_DATA, 2
            else: hw_list, parity = RAID_DATA + JBOD_ONLY_DATA, 0
            
            # Auto Scan
            for m_a in hw_list:
                for m_b in hw_list:
                    for c_a in range(1, t_c + 1):
                        c_b = t_c - c_a
                        ratio = c_a / t_c
                        ma, ta = t_m * ratio, t_t * ratio
                        mb, tb = t_m - ma, t_t - ta
                        
                        # Unit A
                        if c_a > m_a[2] or ma > m_a[3]: continue
                        ca, ha = get_best_hdd(ta, m_a[4], parity, self.hdd_prices)
                        if not ha: continue
                        
                        if c_b == 0: # Single NVR
                            if (m_a[5] + ca) < best_cost:
                                best_cost, best_cfg = m_a[5] + ca, {"units": [{"m": m_a, "c": c_a, "mb": ma, "tb": ta, "h": ha}]}
                        else: # Dual NVR
                            if c_b > m_b[2] or mb > m_b[3]: continue
                            cb, hb = get_best_hdd(tb, m_b[4], parity, self.hdd_prices)
                            if hb and (m_a[5] + ca + m_b[5] + cb) < best_cost:
                                best_cost, best_cfg = m_a[5] + ca + m_b[5] + cb, {"units": [
                                    {"m": m_a, "c": c_a, "mb": ma, "tb": ta, "h": ha},
                                    {"m": m_b, "c": c_b, "mb": mb, "tb": tb, "h": hb}
                                ]}
        else:
            # Manual Mode
            nvr_a = [m for m in ALL_MODELS if m[1] == self.nvr_a_var.get()][0]
            par_a = 1 if self.mode_a.get() == "RAID 5" else 2 if self.mode_a.get() == "RAID 6" else 0
            c_a = self.cam_split_val.get()
            ratio = c_a / t_c
            ma, ta = t_m * ratio, t_t * ratio
            ca, ha = get_best_hdd(ta, nvr_a[4], par_a, self.hdd_prices)
            
            if self.nvr_b_var.get() == "None":
                best_cost, best_cfg = nvr_a[5] + ca, {"units": [{"m": nvr_a, "c": c_a, "mb": ma, "tb": ta, "h": ha}]}
            else:
                nvr_b = [m for m in ALL_MODELS if m[1] == self.nvr_b_var.get()][0]
                par_b = 1 if self.mode_b.get() == "RAID 5" else 2 if self.mode_b.get() == "RAID 6" else 0
                c_b = t_c - c_a
                mb, tb = t_m - ma, t_t - ta
                cb, hb = get_best_hdd(tb, nvr_b[4], par_b, self.hdd_prices)
                best_cost, best_cfg = nvr_a[5] + ca + nvr_b[5] + cb, {"units": [
                    {"m": nvr_a, "c": c_a, "mb": ma, "tb": ta, "h": ha},
                    {"m": nvr_b, "c": c_b, "mb": mb, "tb": tb, "h": hb}
                ]}

        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if not best_cfg: return
        out = f"AUDIT RESULT | TOTAL: ${best_cost:,.2f}\n" + "="*50 + "\n"
        for i, u in enumerate(best_cfg['units']):
            out += f"UNIT {i+1}: {u['m'][1]} | {u['c']} Cams | {u['h']['qty']}x{u['h']['cap']}TB\n"
        txt.insert(tk.END, out)

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("950x850"); app = CCTVApp(r); r.mainloop()
