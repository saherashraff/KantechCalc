import tkinter as tk
from tkinter import ttk, messagebox
import math

# ------------------------------------------------------------
# 1. HARDWARE DATA (All Modes Included)
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
    ["1U RAID (JBOD Mode)", "ADVER00N0NP16G", 32, 100, 4, 3750.00],
    ["2U 200 Ch (JBOD)", "ADVER02RDK", 200, 1500, 12, 12812.50],  
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
    ["2U Rack 175 Ch", "ADVER02RDK", 175, 1000, 12, 13854.20],
    ["2U 200 Ch (JBOD)", "ADVER02RDK", 200, 1500, 12, 12812.50],
    
]

DEFAULT_HDD_PRICES = {
    1: 93.75, 2: 122.95, 4: 218.75, 6: 281.25, 8: 395.85, 
    10: 416.7, 12: 687.50, 14: 1041.7, 18: 1052.1, 22: 1145.85 , 24: 1447.95 , 26: 1700,
}

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 0: return 0, {"qty": 0, "cap": 0, "cost": 0}
    best_h_cost = float('inf')
    best_h_cfg = None
    # Filter only prices that are > 0
    valid_prices = {k: v for k, v in price_dict.items() if v > 0}
    for cap, price in sorted(valid_prices.items()):
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
        self.root.title("CCTV ULTIMATE CHEAPEST FINDER")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Camera Input ")
        self.nb.add(self.t2, text=" 2. Ultimate Cheapest ")
        self.nb.add(self.t3, text=" 3. HDD Price List ")

        # --- TAB 1: INPUT ---
        f = ttk.Frame(self.t1, padding=10); f.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f, width=10); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        ttk.Button(f, text="Add/Update Row", command=self.save_camera).grid(row=0, column=8, padx=5)
        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=10)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.load_camera)

        # --- TAB 2: CHEAPEST CALCULATOR ---
        f_b = ttk.Frame(self.t2, padding=15); f_b.pack(fill="x")
        ttk.Label(f_b, text="Select Mode:").grid(row=0, column=0, sticky="w")
        self.mode_var = tk.StringVar(value="JBOD")
        mode_cb = ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "JBOD"], state="readonly")
        mode_cb.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(f_b, text="FIND ULTIMATE CHEAPEST", command=self.find_cheapest).grid(row=1, column=0, columnspan=2, pady=10)
        
        self.res_txt = tk.Text(self.t2, bg="#0d0d0d", fg="#00ff44", font=("Consolas", 10))
        self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 3: FIXED HDD PRICE UPDATER ---
        pf = ttk.Frame(self.t3, padding=20); pf.pack()
        self.p_ents = {}
        # Clear/Create price inputs
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{cap}TB Price: $").grid(row=r, column=c*2, sticky="e", pady=2)
            e = ttk.Entry(pf, width=12)
            e.insert(0, f"{self.hdd_prices[cap]:.2f}")
            e.grid(row=r, column=c*2+1, padx=10, pady=2)
            self.p_ents[cap] = e
        ttk.Button(self.t3, text="SAVE HDD PRICES", command=self.save_prices).pack(pady=10)

    def save_prices(self):
        try:
            for cap, entry in self.p_ents.items():
                self.hdd_prices[cap] = float(entry.get())
            messagebox.showinfo("Success", "HDD Prices Updated for all calculations.")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for prices.")

    def save_camera(self):
        try:
            d = (self.ents["Name"].get(), int(self.ents["Qty"].get()), float(self.ents["Mbps"].get()), float(self.ents["GB"].get()))
            sel = self.tree.selection()
            if sel: self.tree.item(sel, values=d)
            else: self.tree.insert("", "end", values=d)
        except: pass

    def load_camera(self, e):
        sel = self.tree.selection()
        if sel:
            v = self.tree.item(sel)['values']
            for k, val in zip(["Name", "Qty", "Mbps", "GB"], v):
                self.ents[k].delete(0, tk.END); self.ents[k].insert(0, val)

    def find_cheapest(self):
        t_mbps, t_tb, t_cams = 0, 0, 0
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            q = int(v[1]); t_cams += q; t_mbps += (float(v[2])*q); t_tb += ((float(v[3])/1024)*q)
        
        if t_cams == 0: return

        mode = self.mode_var.get()
        hw_list = RAID_DATA if "RAID" in mode else JBOD_DATA
        parity = 1 if mode == "RAID 5" else 0
        
        final_list = []
        for m in hw_list:
            # We start with minimum units for cameras/bandwidth
            n_qty = max(math.ceil(t_cams / m[2]), math.ceil(t_mbps / m[3]))
            
            # Check if storage fits in the slots of these units
            h_cost, h_cfg = get_best_hdd(t_tb / n_qty, m[4], parity, self.hdd_prices)
            
            # If storage doesn't fit, we keep adding NVRs until it does
            while not h_cfg and n_qty < 50: 
                n_qty += 1
                h_cost, h_cfg = get_best_hdd(t_tb / n_qty, m[4], parity, self.hdd_prices)

            if h_cfg:
                total_cost = (m[5] + h_cost) * n_qty
                final_list.append({"total": total_cost, "m": m, "n_qty": n_qty, "h": h_cfg})

        final_list.sort(key=lambda x: x['total'])
        self.res_txt.delete("1.0", tk.END)
        self.res_txt.insert(tk.END, f"--- TOP 3 CHEAPEST SOLUTIONS ({mode}) ---\n\n")
        
        for i, s in enumerate(final_list[:3]):
            self.res_txt.insert(tk.END, f"RANK #{i+1}: ${s['total']:,.2f} Total Cost\n")
            self.res_txt.insert(tk.END, f" > Hardware: {s['n_qty']} x {s['m'][0]} ({s['m'][1]})\n")
            self.res_txt.insert(tk.END, f" > Drives: {s['h']['qty']} x {s['h']['cap']}TB per unit\n")
            self.res_txt.insert(tk.END, f" > Load/NVR: {t_cams/s['n_qty']:.1f} Cams | {t_tb/s['n_qty']:.2f} TB\n")
            self.res_txt.insert(tk.END, "-"*50 + "\n")

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("900x800"); app = CCTVApp(r); r.mainloop()
