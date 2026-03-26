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
    ["1U RAID (JBOD)", "ADVER00N0NP16G", 32, 100, 4, 3750.00],
    ["2U 200 Ch (JBOD)", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 999, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 999, 1, 770.85],
]

DEFAULT_HDD_PRICES = {
    1: 93.75, 2: 122.95, 4: 218.75, 6: 281.25, 8: 395.85, 
    10: 416.7, 12: 687.50, 14: 1041.7, 18: 1052.1, 22: 1145.85, 
    24: 1447.95, 26: 1700.00
}

# ------------------------------------------------------------
# 2. LOGIC FUNCTIONS
# ------------------------------------------------------------
def get_best_hdd(required_tb, slots, parity, price_dict):
    """
    Logic: Find min drives for data, THEN add parity.
    Ensures RAID 5 has +1 and RAID 6 has +2.
    """
    if required_tb <= 0: return 0, {"qty": 0, "cap": 0, "cost": 0}
    best_h_cost = float('inf')
    best_h_cfg = None
    valid_prices = {k: v for k, v in price_dict.items() if v > 0}
    
    for cap, price in sorted(valid_prices.items()):
        # Step 1: Min drives needed for the DATA only
        data_drives = math.ceil(required_tb / cap)
        # Step 2: Add parity overhead
        total_drives = data_drives + parity
        
        # Validation: RAID must have at least 1 data drive + parity
        if total_drives <= slots and data_drives >= 1:
            total_price = total_drives * price
            if total_price < best_h_cost:
                best_h_cost = total_price
                best_h_cfg = {"qty": total_drives, "cap": cap, "cost": total_price}
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER CALCULATOR - RAIDs & HOLIS")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Camera Input ")
        self.nb.add(self.t2, text=" 2. Ultimate Solution ")
        self.nb.add(self.t3, text=" 3. HDD Price List ")

        # --- TAB 1: INPUT ---
        f = ttk.Frame(self.t1, padding=10); f.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f, width=10); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        
        btn_f = ttk.Frame(self.t1); btn_f.pack(fill="x", padx=10)
        ttk.Button(btn_f, text="Add/Update Row", command=self.save_camera).pack(side="left", padx=5)
        ttk.Button(btn_f, text="Clear All", command=self.clear_all_cams).pack(side="left", padx=5)

        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=10)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.load_camera)

        # --- TAB 2: CHEAPEST CALCULATOR ---
        f_b = ttk.Frame(self.t2, padding=15); f_b.pack(fill="x")
        ttk.Label(f_b, text="Select Mode:").grid(row=0, column=0, sticky="w")
        self.mode_var = tk.StringVar(value="JBOD")
        mode_cb = ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly")
        mode_cb.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(f_b, text="GENERATE CHEAPEST SOLUTION", command=self.find_cheapest).grid(row=1, column=0, columnspan=2, pady=10)
        
        self.res_txt = tk.Text(self.t2, bg="#0d0d0d", fg="#00ff44", font=("Consolas", 10))
        self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 3: PRICE LIST ---
        pf = ttk.Frame(self.t3, padding=20); pf.pack()
        self.p_ents = {}
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{cap}TB Price: $").grid(row=r, column=c*2, sticky="e", pady=2)
            e = ttk.Entry(pf, width=12); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1, padx=10, pady=2)
            self.p_ents[cap] = e
        ttk.Button(self.t3, text="SAVE HDD PRICES", command=self.save_prices).pack()

    def save_prices(self):
        for cap, entry in self.p_ents.items(): self.hdd_prices[cap] = float(entry.get())
        messagebox.showinfo("Success", "HDD Prices Updated.")

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

    def clear_all_cams(self):
        for i in self.tree.get_children(): self.tree.delete(i)

    def find_cheapest(self):
        # 1. Gather Totals & Camera Types
        cams_data = []
        t_mbps, t_tb, t_cams = 0, 0, 0
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            c_qty = int(v[1])
            cams_data.append({"name": v[0], "qty": c_qty, "mbps": float(v[2]), "tb": (float(v[3])/1024)})
            t_cams += c_qty; t_mbps += (float(v[2])*c_qty); t_tb += ((float(v[3])/1024)*c_qty)
        
        if t_cams == 0: return

        mode = self.mode_var.get()
        if mode == "Holis": hw_list, parity = HOLIS_DATA, 0
        elif mode == "RAID 5": hw_list, parity = RAID_DATA, 1
        elif mode == "RAID 6": hw_list, parity = RAID_DATA, 2
        else: hw_list, parity = JBOD_DATA, 0
        
        final_list = []
        for m in hw_list:
            n_qty = max(math.ceil(t_cams / m[2]), math.ceil(t_mbps / m[3]))
            h_cost, h_cfg = get_best_hdd(t_tb / n_qty, m[4], parity, self.hdd_prices)
            
            while not h_cfg and n_qty < 50: 
                n_qty += 1
                h_cost, h_cfg = get_best_hdd(t_tb / n_qty, m[4], parity, self.hdd_prices)

            if h_cfg:
                total_cost = (m[5] + h_cost) * n_qty
                final_list.append({"total": total_cost, "m": m, "n_qty": n_qty, "h": h_cfg})

        final_list.sort(key=lambda x: x['total'])
        self.res_txt.delete("1.0", tk.END)
        best = final_list[0] if final_list else None
        
        if not best:
            self.res_txt.insert(tk.END, "No valid solution found.")
            return

        self.res_txt.insert(tk.END, f"🏆 ULTIMATE CHEAPEST ({mode})\n{'='*50}\n")
        self.res_txt.insert(tk.END, f"GRAND TOTAL: ${best['total']:,.2f}\n")
        self.res_txt.insert(tk.END, f"HARDWARE:    {best['n_qty']} x {best['m'][0]} ({best['m'][1]})\n")
        self.res_txt.insert(tk.END, f"DRIVES:      {best['h']['qty']} x {best['h']['cap']}TB per unit\n\n")
        
        # Camera Division Breakdown
        self.res_txt.insert(tk.END, "CAMERA DIVISION PER NVR:\n" + "-"*30 + "\n")
        for cam in cams_data:
            div_qty = cam['qty'] / best['n_qty']
            div_mbps = (cam['mbps'] * cam['qty']) / best['n_qty']
            div_tb = (cam['tb'] * cam['qty']) / best['n_qty']
            self.res_txt.insert(tk.END, f" > {cam['name']}: {div_qty:.1f} units\n")
            self.res_txt.insert(tk.END, f"   (Load: {div_mbps:.1f} Mbps | {div_tb:.2f} TB)\n")
        
        self.res_txt.insert(tk.END, f"\nTOTAL LOAD PER NVR:\n")
        self.res_txt.insert(tk.END, f" > Total Mbps: {t_mbps/best['n_qty']:.1f} / {best['m'][3]} Max\n")
        self.res_txt.insert(tk.END, f" > Total TB:   {t_tb/best['n_qty']:.2f} TB needed\n")

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("900x850"); app = CCTVApp(r); r.mainloop()
