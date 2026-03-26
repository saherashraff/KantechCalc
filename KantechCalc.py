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
# 2. CALCULATION ENGINE
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
        self.root.title("CCTV MASTER V15 - FINAL AUDIT TOOL")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root); self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Camera Management "); self.nb.add(self.t2, text=" 2. Final Audit Report "); self.nb.add(self.t3, text=" 3. HDD Settings ")

        # TAB 1: Cameras
        f_in = ttk.Frame(self.t1, padding=10); f_in.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=12); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        
        btn_f = ttk.Frame(self.t1, padding=5); btn_f.pack(fill="x", padx=10)
        ttk.Button(btn_f, text="Add/Update Row", command=self.save_camera).pack(side="left", padx=2)
        ttk.Button(btn_f, text="Delete Selected", command=self.delete_camera).pack(side="left", padx=2)
        ttk.Button(btn_f, text="Clear List", command=self.clear_all_cams).pack(side="left", padx=2)

        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=15)
        for c, h in zip(self.tree["columns"], ["Type Name","Qty","Mbps","GB/Cam"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # TAB 2: Report
        f_b = ttk.Frame(self.t2, padding=15); f_b.pack(fill="x")
        self.mode_var = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD", "Holis"], state="readonly").pack(side="left", padx=5)
        ttk.Button(f_b, text="GENERATE AUDIT", command=self.find_cheapest).pack(side="left", padx=5)
        
        self.res_txt = tk.Text(self.t2, bg="#ffffff", fg="#000000", font=("Consolas", 10), wrap="none")
        self.res_txt.pack(fill="both", expand=True, padx=10, pady=5)

        # TAB 3: HDDs
        pf = ttk.Frame(self.t3, padding=20); pf.pack(fill="both", expand=True)
        self.p_ents = {}
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2)
            ttk.Label(pf, text=f"{cap}TB Drive $:").grid(row=r, column=c*2, sticky="e", pady=5)
            e = ttk.Entry(pf, width=15); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1, padx=10, pady=5)
            self.p_ents[cap] = e
        ttk.Button(self.t3, text="SAVE HDD PRICES", command=self.update_prices).pack(pady=20)

    def update_prices(self):
        try:
            for cap, entry in self.p_ents.items(): self.hdd_prices[cap] = float(entry.get())
            messagebox.showinfo("Success", "HDD Prices Updated.")
        except: messagebox.showerror("Error", "Invalid Price Format.")

    def save_camera(self):
        try:
            n, q, m, g = self.ents["Name"].get(), self.ents["Qty"].get(), self.ents["Mbps"].get(), self.ents["GB"].get()
            if not n: return
            sel = self.tree.selection()
            if sel: self.tree.item(sel[0], values=(n, q, m, g))
            else: self.tree.insert("", "end", values=(n, q, m, g))
            for e in self.ents.values(): e.delete(0, tk.END)
        except: pass

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        v = self.tree.item(sel[0])['values']
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            self.ents[label].delete(0, tk.END); self.ents[label].insert(0, v[i])

    def delete_camera(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def clear_all_cams(self):
        if messagebox.askyesno("Confirm", "Clear everything?"):
            for i in self.tree.get_children(): self.tree.delete(i)

    def find_cheapest(self):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": str(v[0]), "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        
        if not cams: return
        t_c, t_m, t_t = sum(c['qty'] for c in cams), sum(c['qty']*c['mbps'] for c in cams), sum(c['qty']*c['tb'] for c in cams)
        mode = self.mode_var.get()
        hw_list, parity = (HOLIS_DATA, 0) if mode == "Holis" else (RAID_DATA, 1) if mode == "RAID 5" else (RAID_DATA, 2) if mode == "RAID 6" else (JBOD_DATA, 0)
        
        best_cost, best_cfg = float('inf'), None

        for m in hw_list:
            n_min = max(math.ceil(t_c/m[2]), math.ceil(t_m/m[3]))
            if n_min == 1:
                cost, h = get_best_hdd(t_t, m[4], parity, self.hdd_prices)
                if h and (m[5] + cost) < best_cost:
                    best_cost, best_cfg = m[5] + cost, {"m": m, "n_qty": 1, "units": [{"mb": t_m, "tb": t_t, "h": h, "ratio": 1.0}]}
            elif n_min <= 2:
                for i in range(1, t_c):
                    r = i / t_c
                    m1, t1, m2, t2 = t_m*r, t_t*r, t_m*(1-r), t_t*(1-r)
                    if i > m[2] or (t_c-i) > m[2] or m1 > m[3] or m2 > m[3]: continue
                    c1, h1 = get_best_hdd(t1, m[4], parity, self.hdd_prices)
                    c2, h2 = get_best_hdd(t2, m[4], parity, self.hdd_prices)
                    if h1 and h2 and (m[5]*2 + c1 + c2) < best_cost:
                        best_cost, best_cfg = m[5]*2 + c1 + c2, {"m": m, "n_qty": 2, "units": [{"h": h1, "mb": m1, "tb": t1, "ratio": r}, {"h": h2, "mb": m2, "tb": t2, "ratio": 1-r}]}

        self.res_txt.delete("1.0", tk.END)
        if not best_cfg: return
        
        self.res_txt.insert(tk.END, f"--- PERMUTATION AUDIT REPORT ({mode}) ---\n")
        self.res_txt.insert(tk.END, f"GRAND TOTAL: ${best_cost:,.2f} (Hardware + Optimized HDDs)\n")
        self.res_txt.insert(tk.END, "="*65 + "\n\n")

        for idx, u in enumerate(best_cfg['units']):
            self.res_txt.insert(tk.END, f"NVR UNIT #{idx+1} | {best_cfg['m'][1]} ({best_cfg['m'][0]})\n")
            self.res_txt.insert(tk.END, "-"*65 + "\n")
            self.res_txt.insert(tk.END, f"CAMERA ASSIGNMENT (Ratio: {u['ratio']:.2f}):\n")
            for c in cams:
                take = round(c['qty'] * u['ratio'])
                if take > 0: self.res_txt.insert(tk.END, f"  > {c['name']}: {take} units\n")
            
            self.res_txt.insert(tk.END, f"\nTHROUGHPUT:\n  Used: {u['mb']:.1f} Mbps | Capacity: {best_cfg['m'][3]} Mbps ({((u['mb']/best_cfg['m'][3])*100):.1f}% load)\n")
            self.res_txt.insert(tk.END, f"\nSTORAGE (Active RAID Partition):\n")
            self.res_txt.insert(tk.END, f"  Config:   {u['h']['qty']} x {u['h']['cap']}TB Drives\n")
            self.res_txt.insert(tk.END, f"  Required: {u['tb']:.2f} TB (Raw Data)\n")
            self.res_txt.insert(tk.END, f"  Usable:   {u['h']['total_tb']:.2f} TB (After RAID Overhead)\n")
            self.res_txt.insert(tk.END, "\n" + "="*65 + "\n\n")

if __name__ == "__main__":
    r = tk.Tk(); r.geometry("950x850"); app = CCTVApp(r); r.mainloop()
