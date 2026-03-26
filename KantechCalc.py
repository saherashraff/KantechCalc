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
    ["Holis 8 Ch", "HRN-08013P", 8, 160, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 320, 2, 770.85],
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
    if required_tb <= 1e-6: return 0, {"qty": 0, "cap": 0, "cost": 0, "total_tb": 0}
    best_h_cost = float('inf')
    best_h_cfg = None
    for cap, price in sorted(price_dict.items()):
        if price <= 0: continue
        data_drives = max(math.ceil(required_tb / cap), 2 if parity > 0 else 1)
        total_drives = data_drives + parity
        if total_drives <= slots:
            total_price = total_drives * price
            if total_price < best_h_cost:
                best_h_cost = total_price
                best_h_cfg = {"qty": total_drives, "cap": cap, "cost": total_price, "total_tb": (data_drives * cap)}
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER V14 - DYNAMIC DATA EDITOR")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root); self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Camera Management "); self.nb.add(self.t2, text=" 2. Permutation Report "); self.nb.add(self.t3, text=" 3. HDD Price Editor ")

        # --- TAB 1: CAMERA INPUT & EDITING ---
        f_in = ttk.Frame(self.t1, padding=10); f_in.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=12); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        
        btn_f = ttk.Frame(self.t1, padding=5); btn_f.pack(fill="x", padx=10)
        ttk.Button(btn_f, text="Add/Update Row", command=self.save_camera).pack(side="left", padx=2)
        ttk.Button(btn_f, text="Delete Selected", command=self.delete_camera).pack(side="left", padx=2)
        ttk.Button(btn_f, text="Clear All", command=self.clear_all_cams).pack(side="left", padx=2)

        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=15)
        for c, h in zip(self.tree["columns"], ["Type Name","Qty","Mbps","GB/Cam"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # --- TAB 2: OPTIMIZED REPORT ---
        f_b = ttk.Frame(self.t2, padding=15); f_b.pack(fill="x")
        self.mode_var = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly").pack(side="left", padx=5)
        ttk.Button(f_b, text="CALCULATE BEST RATIO", command=self.find_cheapest).pack(side="left", padx=5)
        
        self.res_txt = tk.Text(self.t2, bg="#0d0d0d", fg="#00FF41", font=("Consolas", 10), wrap="none")
        self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 3: HDD PRICE EDITOR ---
        pf = ttk.Frame(self.t3, padding=20); pf.pack(fill="both", expand=True)
        ttk.Label(pf, text="Update HDD prices below and click Save.", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=4, pady=10)
        self.p_ents = {}
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{cap}TB Drive $:").grid(row=r+1, column=c*2, sticky="e", pady=5)
            e = ttk.Entry(pf, width=15); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r+1, column=c*2+1, padx=10, pady=5)
            self.p_ents[cap] = e
        
        ttk.Button(self.t3, text="SAVE HDD PRICES", command=self.update_prices_in_logic).pack(pady=20)

    def update_prices_in_logic(self):
        try:
            for cap, entry in self.p_ents.items():
                self.hdd_prices[cap] = float(entry.get())
            messagebox.showinfo("Success", "HDD Prices updated! Calculations will now use new rates.")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric prices (e.g. 150.00)")

    def save_camera(self):
        try:
            name, qty, mbps, gb = self.ents["Name"].get(), self.ents["Qty"].get(), self.ents["Mbps"].get(), self.ents["GB"].get()
            if not name: return
            # If a row is selected, update it; otherwise, add new
            selected = self.tree.selection()
            if selected:
                self.tree.item(selected[0], values=(name, qty, mbps, gb))
            else:
                self.tree.insert("", "end", values=(name, qty, mbps, gb))
            for e in self.ents.values(): e.delete(0, tk.END)
        except Exception as e: messagebox.showerror("Input Error", "Check your quantity/bandwidth numbers.")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        vals = self.tree.item(selected[0])['values']
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            self.ents[label].delete(0, tk.END)
            self.ents[label].insert(0, vals[i])

    def delete_camera(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def clear_all_cams(self):
        if messagebox.askyesno("Confirm", "Clear all camera data?"):
            for i in self.tree.get_children(): self.tree.delete(i)

    def find_cheapest(self):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": str(v[0]), "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        
        if not cams: return
        total_cams = sum(c['qty'] for c in cams); total_mbps = sum(c['qty'] * c['mbps'] for c in cams); total_tb = sum(c['qty'] * c['tb'] for c in cams)

        mode = self.mode_var.get()
        hw_list, parity = (HOLIS_DATA, 0) if mode == "Holis" else (RAID_DATA, 1) if mode == "RAID 5" else (RAID_DATA, 2) if mode == "RAID 6" else (JBOD_DATA, 0)
        
        best_overall_cost, best_overall_config = float('inf'), None

        for m in hw_list:
            n_qty_min = max(math.ceil(total_cams / m[2]), math.ceil(total_mbps / m[3]))
            
            if n_qty_min == 1:
                h_cost, h_cfg = get_best_hdd(total_tb, m[4], parity, self.hdd_prices)
                if h_cfg:
                    total_cost = m[5] + h_cost
                    if total_cost < best_overall_cost:
                        best_overall_cost, best_overall_config = total_cost, {"m": m, "n_qty": 1, "units": [{"mb": total_mbps, "tb_req": total_tb, "h": h_cfg, "cam_count": total_cams}]}
            
            elif n_qty_min <= 2:
                for i in range(1, total_cams):
                    ratio = i / total_cams
                    mb_1, tb_1 = total_mbps * ratio, total_tb * ratio
                    mb_2, tb_2 = total_mbps * (1 - ratio), total_tb * (1 - ratio)
                    if i > m[2] or (total_cams-i) > m[2] or mb_1 > m[3] or mb_2 > m[3]: continue
                    cost1, h1 = get_best_hdd(tb_1, m[4], parity, self.hdd_prices)
                    cost2, h2 = get_best_hdd(tb_2, m[4], parity, self.hdd_prices)
                    if h1 and h2:
                        total_cost = (m[5] * 2) + cost1 + cost2
                        if total_cost < best_overall_cost:
                            best_overall_cost, best_overall_config = total_cost, {"m": m, "n_qty": 2, "units": [{"h": h1, "mb": mb_1, "tb_req": tb_1, "cam_count": i}, {"h": h2, "mb": mb_2, "tb_req": tb_2, "cam_count": total_cams-i}]}
        
        self.res_txt.delete("1.0", tk.END)
        if not best_overall_config: 
            self.res_txt.insert(tk.END, "CRITICAL: No matching hardware solution found.")
            return
        
        self.res_txt.insert(tk.END, f"--- DYNAMIC PERMUTATION REPORT ({mode}) ---\n")
        self.res_txt.insert(tk.END, f"TOTAL PRICE: ${best_overall_cost:,.2f}\n")
        self.res_txt.insert(tk.END, "="*60 + "\n\n")

        for idx, u in enumerate(best_overall_config['units']):
            self.res_txt.insert(tk.END, f"UNIT #{idx+1} | {best_overall_config['m'][1]}\n")
            self.res_txt.insert(tk.END, f"  Cams: {u['cam_count']} | Mbps: {u['mb']:.1f}/{best_overall_config['m'][3]} | Drives: {u['h']['qty']} x {u['h']['cap']}TB\n")
            self.res_txt.insert(tk.END, f"  Usable RAID Capacity: {u['h']['total_tb']:.2f} TB (Required: {u['tb_req']:.2f} TB)\n")
            self.res_txt.insert(tk.END, "-"*60 + "\n")

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("950x850"); app = CCTVApp(r); r.mainloop()
