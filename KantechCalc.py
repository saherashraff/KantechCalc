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
        self.root.title("CCTV MASTER V22 - GRANULAR CAMERA SPLIT ENGINE")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root); self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Camera Management "); self.nb.add(self.t2, text=" 2. Final Audit Report "); self.nb.add(self.t3, text=" 3. HDD Settings ")

        # Tab 1
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

        # Tab 2
        f_b = ttk.Frame(self.t2, padding=15); f_b.pack(fill="x")
        self.mode_var = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly").pack(side="left", padx=5)
        ttk.Button(f_b, text="RUN GRANULAR AUDIT", command=self.find_cheapest).pack(side="left", padx=5)
        self.res_txt = tk.Text(self.t2, bg="#ffffff", fg="#000000", font=("Consolas", 10), wrap="none")
        self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # Tab 3
        pf = ttk.Frame(self.t3, padding=20); pf.pack(fill="both", expand=True)
        self.p_ents = {}
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{cap}TB Drive $:").grid(row=r, column=c*2, sticky="e", pady=5)
            e = ttk.Entry(pf, width=15); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1, padx=10, pady=5); self.p_ents[cap] = e
        ttk.Button(self.t3, text="SAVE HDD PRICES", command=self.update_prices).pack(pady=20)

    def update_prices(self):
        try:
            for cap, entry in self.p_ents.items(): self.hdd_prices[cap] = float(entry.get())
            messagebox.showinfo("Success", "Updated.")
        except: messagebox.showerror("Error", "Invalid format.")

    def save_camera(self):
        n, q, m, g = self.ents["Name"].get(), self.ents["Qty"].get(), self.ents["Mbps"].get(), self.ents["GB"].get()
        if n: self.tree.insert("", "end", values=(n, q, m, g))

    def delete_camera(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def find_cheapest(self):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": str(v[0]), "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        
        if not cams: return
        total_cams = sum(c['qty'] for c in cams)
        total_mbps = sum(c['qty']*c['mbps'] for c in cams)
        total_tb = sum(c['qty']*c['tb'] for c in cams)
        
        mode = self.mode_var.get()
        if mode == "Holis": hw_list, parity = HOLIS_DATA, 0
        elif mode == "RAID 5": hw_list, parity = RAID_DATA, 1
        elif mode == "RAID 6": hw_list, parity = RAID_DATA, 2
        else: hw_list, parity = RAID_DATA + JBOD_ONLY_DATA, 0
        
        best_cost, best_cfg = float('inf'), None

        # --- 1. Check Single Units ---
        for m in hw_list:
            if total_cams <= m[2] and total_mbps <= m[3]:
                hc, h = get_best_hdd(total_tb, m[4], parity, self.hdd_prices)
                if h and (m[5] + hc) < best_cost:
                    best_cost, best_cfg = m[5] + hc, {"units": [{"m": m, "c": total_cams, "mb": total_mbps, "tb": total_tb, "h": h}]}

        # --- 2. Check Granular Split (1-Camera Increments) ---
        # We test every NVR A against every NVR B
        for m_a in hw_list:
            for m_b in hw_list:
                # Test every possible camera count on NVR A
                for c_a in range(1, total_cams):
                    c_b = total_cams - c_a
                    
                    # Calculate proportional load
                    ratio_a = c_a / total_cams
                    mb_a, tb_a = total_mbps * ratio_a, total_tb * ratio_a
                    mb_b, tb_b = total_mbps - mb_a, total_tb - tb_a
                    
                    # Physical check
                    if c_a > m_a[2] or mb_a > m_a[3] or c_b > m_b[2] or mb_b > m_b[3]: continue
                    
                    cost_a, h_a = get_best_hdd(tb_a, m_a[4], parity, self.hdd_prices)
                    cost_b, h_b = get_best_hdd(tb_b, m_b[4], parity, self.hdd_prices)
                    
                    if h_a and h_b:
                        total = m_a[5] + cost_a + m_b[5] + cost_b
                        if total < best_cost:
                            best_cost, best_cfg = total, {"units": [
                                {"m": m_a, "c": c_a, "mb": mb_a, "tb": tb_a, "h": h_a},
                                {"m": m_b, "c": c_b, "mb": mb_b, "tb": tb_b, "h": h_b}
                            ]}

        self.res_txt.delete("1.0", tk.END)
        if not best_cfg:
            self.res_txt.insert(tk.END, "CRITICAL: Load exceeds physical capacity of dual-unit combinations.")
            return

        out = f"--- GRANULAR CAM-BY-CAM AUDIT ({mode}) ---\n"
        out += f"TOTAL SOLUTION COST: ${best_cost:,.2f}\n" + "="*65 + "\n\n"
        for i, u in enumerate(best_cfg['units']):
            out += f"UNIT #{i+1} | {u['m'][1]} ({u['m'][0]})\n"
            out += f"  - Cameras: {u['c']} units\n"
            out += f"  - Load:    {u['mb']:.1f} Mbps\n"
            out += f"  - Drives:  {u['h']['qty']} x {u['h']['cap']}TB\n"
            out += f"  - Storage: {u['h']['total_tb']:.2f} TB Usable (Req: {u['tb']:.2f})\n"
            out += "-"*65 + "\n"
        self.res_txt.insert(tk.END, out)

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("950x850"); app = CCTVApp(r); r.mainloop()
