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
    ["2U Rack 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

JBOD_DATA = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50],
    ["2U 200 Ch (JBOD)", "ADVER02RDK", 200, 1500, 12, 12812.50],
]

HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 9999, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 9999, 1, 770.85],
]

DEFAULT_HDD_PRICES = {
    1: 93.75, 2: 122.95, 4: 218.75, 8: 395.85, 10: 416.7, 12: 687.50, 18: 1052.1
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
        self.root.title("CHEAPEST SOLUTION BY MODE")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Camera Input ")
        self.nb.add(self.t2, text=" 2. Build Solution ")
        self.nb.add(self.t3, text=" 3. HDD Prices ")

        # TAB 1: INPUT
        f = ttk.Frame(self.t1, padding=10); f.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f, width=10); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        ttk.Button(f, text="Add/Update", command=self.save_camera).grid(row=0, column=8, padx=5)
        ttk.Button(f, text="Delete", command=self.delete_camera).grid(row=0, column=9)
        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=10)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.load_camera)

        # TAB 2: BUILDER (Cheapest Logic)
        f_b = ttk.LabelFrame(self.t2, text=" Optimize Solution ", padding=15); f_b.pack(fill="x", padx=10, pady=5)
        ttk.Label(f_b, text="Select Mode:").grid(row=0, column=0, sticky="w")
        self.mode_var = tk.StringVar(value="RAID 5")
        mode_cb = ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly")
        mode_cb.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Button(f_b, text="FIND CHEAPEST NVR FOR THIS MODE", command=self.find_cheapest).grid(row=1, column=0, columnspan=2, pady=10)
        
        self.res_txt = tk.Text(self.t2, bg="#1a1a1a", fg="#00ff00", font=("Consolas", 10))
        self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)

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

    def delete_camera(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def find_cheapest(self):
        # 1. Get Totals
        t_mbps, t_tb, t_cams = 0, 0, 0
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            q = int(v[1]); t_cams += q; t_mbps += (float(v[2])*q); t_tb += ((float(v[3])/1024)*q)
        
        if t_cams == 0: return

        mode = self.mode_var.get()
        hw_list = RAID_DATA if "RAID" in mode else (JBOD_DATA if mode == "JBOD" else HOLIS_DATA)
        parity = 1 if mode == "RAID 5" else (2 if mode == "RAID 6" else 0)
        
        possible_solutions = []

        # 2. Iterate through all hardware in this mode
        for m_data in hw_list:
            # How many units needed?
            n_qty = max(math.ceil(t_cams / m_data[2]), math.ceil(t_mbps / m_data[3]))
            
            # Storage per unit
            tb_per_unit = t_tb / n_qty
            h_cost, h_cfg = get_best_hdd(tb_per_unit, m_data[4], parity, self.hdd_prices)
            
            if h_cfg:
                total_project_cost = (m_data[5] + h_cost) * n_qty
                possible_solutions.append({
                    "total": total_project_cost,
                    "model": m_data[0],
                    "part": m_data[1],
                    "n_qty": n_qty,
                    "h_qty": h_cfg['qty'],
                    "h_cap": h_cfg['cap'],
                    "cams_per": t_cams / n_qty,
                    "mbps_per": t_mbps / n_qty,
                    "tb_per": tb_per_unit
                })

        # 3. Sort and Display
        possible_solutions.sort(key=lambda x: x['total'])
        self.res_txt.delete("1.0", tk.END)
        self.res_txt.insert(tk.END, f"--- TOP SOLUTIONS FOR {mode} ---\n\n")

        if not possible_solutions:
            self.res_txt.insert(tk.END, "No hardware fits this load in this mode.")
            return

        for idx, s in enumerate(possible_solutions[:2]): # Top 2
            rank = "🏆 CHEAPEST" if idx == 0 else "🥈 RUNNER UP"
            self.res_txt.insert(tk.END, f"{rank}: ${s['total']:,.2f} Total\n")
            self.res_txt.insert(tk.END, f" > Hardware: {s['n_qty']} x {s['model']} ({s['part']})\n")
            self.res_txt.insert(tk.END, f" > Load per Unit: {s['cams_per']:.1f} Cams | {s['mbps_per']:.1f} Mbps | {s['tb_per']:.2f} TB\n")
            self.res_txt.insert(tk.END, f" > HDDs per Unit: {s['h_qty']} x {s['h_cap']}TB\n")
            self.res_txt.insert(tk.END, "-"*45 + "\n")

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("900x800"); app = CCTVApp(r); r.mainloop()
