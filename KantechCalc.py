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
        self.root.title("CCTV PROJECT BUILDER PRO")
        self.camera_types = [] 
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.t1 = ttk.Frame(self.nb) # Optimizer
        self.t_fixed = ttk.Frame(self.nb) # Fixed NVR Tab
        self.t2 = ttk.Frame(self.nb) # HDD Prices
        
        self.nb.add(self.t1, text=" Camera Input & Auto-Opt ")
        self.nb.add(self.t_fixed, text=" Fixed Unit Manual Build ")
        self.nb.add(self.t2, text=" HDD Price List ")
        
        # --- TAB 1: CAMERA INPUT & EDITING ---
        f_input = ttk.LabelFrame(self.t1, text=" Camera Entry ", padding=10)
        f_input.pack(fill="x", padx=10, pady=5)
        
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_input, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_input, width=10); e.grid(row=0, column=i*2+1, padx=5)
            self.ents[label] = e
            
        btn_f = ttk.Frame(f_input)
        btn_f.grid(row=0, column=8, padx=10)
        ttk.Button(btn_f, text="Add/Update", command=self.save_camera).pack(side="left", padx=2)
        ttk.Button(btn_f, text="Delete Selected", command=self.delete_camera).pack(side="left", padx=2)

        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=6)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB (Per Cam)"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="x", padx=10)
        self.tree.bind("<<TreeviewSelect>>", self.load_camera_to_edit)

        ttk.Button(self.t1, text="RUN AUTO-OPTIMIZE (Cheapest Total)", command=self.optimize).pack(pady=10)
        self.txt = tk.Text(self.t1, bg="#1a1a1a", fg="#00ff00", font=("Consolas", 10), height=15)
        self.txt.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 2: FIXED UNIT BUILDER ---
        f_fixed = ttk.Frame(self.t_fixed, padding=20)
        f_fixed.pack(fill="both")
        
        ttk.Label(f_fixed, text="Select NVR Model:").grid(row=0, column=0, sticky="w")
        self.fixed_nvr_choice = ttk.Combobox(f_fixed, values=[x[0] for x in RAID_DATA], width=30)
        self.fixed_nvr_choice.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(f_fixed, text="Quantity of Units:").grid(row=1, column=0, sticky="w")
        self.fixed_nvr_qty = ttk.Entry(f_fixed, width=10); self.fixed_nvr_qty.insert(0, "1")
        self.fixed_nvr_qty.grid(row=1, column=1, pady=5, padx=5, sticky="w")
        
        ttk.Button(f_fixed, text="CALCULATE FOR THIS MODEL", command=self.calc_fixed).grid(row=2, column=0, columnspan=2, pady=15)
        
        self.fixed_txt = tk.Text(self.t_fixed, bg="#1a1a1a", fg="#00ccff", font=("Consolas", 10))
        self.fixed_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 3: PRICE LIST ---
        pf = ttk.Frame(self.t2, padding=20)
        pf.pack()
        self.p_ents = {}
        for i, (s, p) in enumerate(sorted(self.hdd_prices.items())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{s}TB Price: $").grid(row=r, column=c*2)
            e = ttk.Entry(pf, width=10); e.insert(0, f"{p:.2f}"); e.grid(row=r, column=c*2+1, pady=3, padx=5)
            self.p_ents[s] = e
        ttk.Button(self.t2, text="Save HDD Prices", command=self.save_p).pack()

    # --- LOGIC FUNCTIONS ---
    def save_camera(self):
        try:
            name, qty, mbps, gb = self.ents["Name"].get(), int(self.ents["Qty"].get()), float(self.ents["Mbps"].get()), float(self.ents["GB"].get())
            selected = self.tree.selection()
            if selected: # Update existing
                self.tree.item(selected, values=(name, qty, mbps, gb))
            else: # Add new
                self.tree.insert("", "end", values=(name, qty, mbps, gb))
            for k in self.ents: self.ents[k].delete(0, tk.END)
        except: messagebox.showerror("Error", "Check your numbers!")

    def load_camera_to_edit(self, event):
        selected = self.tree.selection()
        if selected:
            v = self.tree.item(selected)['values']
            for k, val in zip(["Name", "Qty", "Mbps", "GB"], v):
                self.ents[k].delete(0, tk.END)
                self.ents[k].insert(0, val)

    def delete_camera(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def save_p(self):
        for s, e in self.p_ents.items(): self.hdd_prices[s] = float(e.get())
        messagebox.showinfo("Saved", "Prices updated.")

    def get_totals(self):
        total_mbps, total_tb = 0, 0
        total_cams = 0
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            qty = int(v[1])
            total_cams += qty
            total_mbps += (float(v[2]) * qty)
            total_tb += ((float(v[3]) / 1024) * qty)
        return total_cams, total_mbps, total_tb

    def optimize(self):
        c_count, t_mbps, t_tb = self.get_totals()
        if c_count == 0: return
        
        best_total = float('inf')
        best_sol = None

        for m in RAID_DATA:
            if c_count <= m[2] and t_mbps <= m[3]:
                h_cost, h_cfg = get_best_hdd(t_tb, m[4], 1, self.hdd_prices)
                if h_cfg and (m[5] + h_cost) < best_total:
                    best_total = m[5] + h_cost
                    best_sol = {"m": m, "h": h_cfg, "tt": t_tb, "tm": t_mbps}
        
        self.txt.delete("1.0", tk.END)
        if best_sol:
            res = f"--- CHEAPEST AUTO-PICK: ${best_total:,.2f} ---\n"
            res += f"Model: {best_sol['m'][0]} ({best_sol['m'][1]})\n"
            res += f"Drive Config: {best_sol['h']['qty']} x {best_sol['h']['cap']}TB\n"
            self.txt.insert("1.0", res)
        else: self.txt.insert("1.0", "No single unit matches these specs.")

    def calc_fixed(self):
        c_count, t_mbps, t_tb = self.get_totals()
        model_name = self.fixed_nvr_choice.get()
        try: nvr_qty = int(self.fixed_nvr_qty.get())
        except: nvr_qty = 1
        
        # Find model data
        m_data = next((x for x in RAID_DATA if x[0] == model_name), None)
        if not m_data: return

        # Split load across requested quantity
        tb_per_unit = t_tb / nvr_qty
        mbps_per_unit = t_mbps / nvr_qty
        cams_per_unit = c_count / nvr_qty

        self.fixed_txt.delete("1.0", tk.END)
        self.fixed_txt.insert(tk.END, f"--- MANUAL BUILD: {nvr_qty} x {model_name} ---\n\n")
        
        if cams_per_unit > m_data[2] or mbps_per_unit > m_data[3]:
            self.fixed_txt.insert(tk.END, "⚠️ WARNING: Requirements exceed hardware limits per unit!\n\n")

        h_cost, h_cfg = get_best_hdd(tb_per_unit, m_data[4], 1, self.hdd_prices)
        
        if h_cfg:
            unit_price = m_data[5] + h_cost
            grand_total = unit_price * nvr_qty
            self.fixed_txt.insert(tk.END, f"Per Unit Specs:\n - Load: {mbps_per_unit:.2f} Mbps\n - Storage: {tb_per_unit:.2f} TB\n")
            self.fixed_txt.insert(tk.END, f" - HDDs: {h_cfg['qty']} x {h_cfg['cap']}TB\n")
            self.fixed_txt.insert(tk.END, f" - Unit Total: ${unit_price:,.2f}\n")
            self.fixed_txt.insert(tk.END, "-"*30 + "\n")
            self.fixed_txt.insert(tk.END, f"GRAND TOTAL PROJECT: ${grand_total:,.2f}")
        else:
            self.fixed_txt.insert(tk.END, "HDD Error: Cannot fit storage requirements in this model's slots.")

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("950x850"); app = CCTVApp(r); r.mainloop()
