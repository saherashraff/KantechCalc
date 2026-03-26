import tkinter as tk
from tkinter import ttk, messagebox
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

JBOD_DATA = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50],
    ["1U RAID (JBOD Mode)", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 200 Ch (JBOD)", "ADVER02RDK", 200, 1500, 12, 12812.50],
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
    if required_tb <= 0: return 0, {"qty": 0, "cap": 0, "cost": 0}
    best_h_cost = float('inf')
    best_h_cfg = None
    for cap, price in sorted(price_dict.items()):
        data_drives = math.ceil(required_tb / cap)
        total_drives = data_drives + parity
        if total_drives <= slots and data_drives >= 1:
            total_price = total_drives * price
            if total_price < best_h_cost:
                best_h_cost = total_price
                best_h_cfg = {"qty": total_drives, "cap": cap, "cost": total_price}
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV PROJECT BUILDER - MANUAL MODE ENABLED")
        self.camera_types = [] 
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.t1 = ttk.Frame(self.nb) # Input
        self.t_fixed = ttk.Frame(self.nb) # Build
        self.t2 = ttk.Frame(self.nb) # Prices
        
        self.nb.add(self.t1, text=" 1. Camera Input ")
        self.nb.add(self.t_fixed, text=" 2. Build Solution ")
        self.nb.add(self.t2, text=" 3. HDD Price List ")
        
        # --- TAB 1: INPUT ---
        f_in = ttk.LabelFrame(self.t1, text=" Camera Entry & Management ", padding=10)
        f_in.pack(fill="x", padx=10, pady=5)
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=10); e.grid(row=0, column=i*2+1, padx=5)
            self.ents[label] = e
        ttk.Button(f_in, text="Save/Update", command=self.save_camera).grid(row=0, column=8, padx=5)
        ttk.Button(f_in, text="Delete Selected", command=self.delete_camera).grid(row=0, column=9)

        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=10)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.load_camera)

        # --- TAB 2: MANUAL BUILDER ---
        f_build = ttk.LabelFrame(self.t_fixed, text=" Configuration Settings ", padding=15)
        f_build.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(f_build, text="Step 1: Choose Mode:").grid(row=0, column=0, sticky="w")
        self.calc_mode = tk.StringVar(value="RAID 5")
        mode_cb = ttk.Combobox(f_build, textvariable=self.calc_mode, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly")
        mode_cb.grid(row=0, column=1, pady=5, sticky="w", padx=5)
        mode_cb.bind("<<ComboboxSelected>>", self.update_nvr_list)

        ttk.Label(f_build, text="Step 2: Select Model:").grid(row=1, column=0, sticky="w")
        self.nvr_sel = ttk.Combobox(f_build, width=35, state="readonly")
        self.nvr_sel.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(f_build, text="Step 3: Number of Units:").grid(row=2, column=0, sticky="w")
        self.nvr_qty_ent = ttk.Entry(f_build, width=10); self.nvr_qty_ent.insert(0, "1")
        self.nvr_qty_ent.grid(row=2, column=1, pady=5, sticky="w", padx=5)

        ttk.Button(f_build, text="GENERATE DETAILED SOLUTION", command=self.run_calc).grid(row=3, column=0, columnspan=2, pady=10)
        
        self.res_txt = tk.Text(self.t_fixed, bg="#1c1c1c", fg="#00ffcc", font=("Consolas", 10))
        self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.update_nvr_list()

        # --- TAB 3: PRICES ---
        pf = ttk.Frame(self.t2, padding=20)
        pf.pack(); self.p_ents = {}
        for i, (s, p) in enumerate(sorted(self.hdd_prices.items())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{s}TB $:").grid(row=r, column=c*2)
            e = ttk.Entry(pf, width=10); e.insert(0, f"{p:.2f}"); e.grid(row=r, column=c*2+1, pady=2)
            self.p_ents[s] = e
        ttk.Button(self.t2, text="Update Price List", command=self.save_p).pack()

    # --- LOGIC ---
    def update_nvr_list(self, event=None):
        mode = self.calc_mode.get()
        if "RAID" in mode: vals = [x[0] for x in RAID_DATA]
        elif mode == "JBOD": vals = [x[0] for x in JBOD_DATA]
        else: vals = [x[0] for x in HOLIS_DATA]
        self.nvr_sel['values'] = vals
        self.nvr_sel.current(0)

    def save_camera(self):
        try:
            d = (self.ents["Name"].get(), int(self.ents["Qty"].get()), float(self.ents["Mbps"].get()), float(self.ents["GB"].get()))
            sel = self.tree.selection()
            if sel: self.tree.item(sel, values=d)
            else: self.tree.insert("", "end", values=d)
        except: messagebox.showerror("Error", "Check your camera inputs.")

    def load_camera(self, e):
        sel = self.tree.selection()
        if sel:
            v = self.tree.item(sel)['values']
            for k, val in zip(["Name", "Qty", "Mbps", "GB"], v):
                self.ents[k].delete(0, tk.END); self.ents[k].insert(0, val)

    def delete_camera(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def save_p(self):
        for s, e in self.p_ents.items(): self.hdd_prices[s] = float(e.get())
        messagebox.showinfo("Success", "Prices updated.")

    def run_calc(self):
        # 1. Gather all cameras from the tree
        cams_list = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams_list.append({'name': v[0], 'qty': int(v[1]), 'mbps': float(v[2]), 'gb': float(v[3])})
        
        if not cams_list: return

        # 2. Get Selection
        mode = self.calc_mode.get()
        n_qty = int(self.nvr_qty_ent.get())
        hw_list = RAID_DATA if "RAID" in mode else (JBOD_DATA if mode == "JBOD" else HOLIS_DATA)
        m_data = next((x for x in hw_list if x[0] == self.nvr_sel.get()), None)
        parity = 1 if mode == "RAID 5" else (2 if mode == "RAID 6" else 0)

        # 3. Calculate Distribution Per Unit
        total_mbps = sum(c['mbps'] * c['qty'] for c in cams_list)
        total_tb = sum((c['gb'] / 1024) * c['qty'] for c in cams_list)
        total_cams = sum(c['qty'] for c in cams_list)

        self.res_txt.delete("1.0", tk.END)
        self.res_txt.insert(tk.END, f"--- PROJECT BOM: {n_qty} x {m_data[0]} ({mode}) ---\n" + "="*60 + "\n")
        
        # Detailed Load Per Unit
        load_per_nvr = total_mbps / n_qty
        tb_per_nvr = total_tb / n_qty
        cams_per_nvr = total_cams / n_qty

        self.res_txt.insert(tk.END, f"DISTRIBUTION PER NVR:\n")
        self.res_txt.insert(tk.END, f" > Cameras: {cams_per_nvr:.2f} avg\n")
        self.res_txt.insert(tk.END, f" > Throughput: {load_per_nvr:.2f} Mbps / {m_data[3]} Mbps Max\n")
        self.res_txt.insert(tk.END, f" > Storage Needed: {tb_per_nvr:.2f} TB\n")
        
        # Check Limits
        if cams_per_nvr > m_data[2]:
            self.res_txt.insert(tk.END, f" ❌ WARNING: Camera count exceeds {m_data[2]} limit per unit!\n")
        if load_per_nvr > m_data[3]:
            self.res_txt.insert(tk.END, f" ❌ WARNING: Mbps load exceeds {m_data[3]} limit per unit!\n")

        # 4. Storage Calculation
        h_cost, h_cfg = get_best_hdd(tb_per_nvr, m_data[4], parity, self.hdd_prices)
        
        if h_cfg:
            unit_total = m_data[5] + h_cost
            self.res_txt.insert(tk.END, "\nHARD DRIVE SOLUTION (Per Unit):\n")
            self.res_txt.insert(tk.END, f" > Config: {h_cfg['qty']} x {h_cfg['cap']}TB\n")
            self.res_txt.insert(tk.END, f" > Subtotal HDD: ${h_cost:,.2f}\n")
            self.res_txt.insert(tk.END, f" > Subtotal NVR: ${m_data[5]:,.2f}\n")
            self.res_txt.insert(tk.END, "-"*40 + "\n")
            self.res_txt.insert(tk.END, f"GRAND TOTAL PROJECT: ${unit_total * n_qty:,.2f}\n")
        else:
            self.res_txt.insert(tk.END, "\n ❌ STORAGE ERROR: Storage cannot fit in available slots!")

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("950x850"); app = CCTVApp(r); r.mainloop()
