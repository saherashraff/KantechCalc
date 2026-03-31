import tkinter as tk
from tkinter import ttk, messagebox
import math

# --- DATA ---
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
DEFAULT_HDD_PRICES = {1: 93.75, 2: 122.95, 4: 218.75, 6: 281.25, 8: 395.85, 10: 416.7, 12: 687.50, 14: 1041.7, 18: 1052.1, 22: 1145.85, 24: 1447.95, 26: 1700.00}

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 1e-6: return 0, {"qty": 0, "cap": 0, "cost": 0, "total_tb": 0}
    best_h_cost, best_h_cfg = float('inf'), None
    for cap, price in sorted(price_dict.items()):
        min_d = 2 if parity > 0 else 1
        data_drives = max(math.ceil(required_tb / cap), min_d)
        total_drives = data_drives + parity
        if total_drives <= slots:
            current_total = total_drives * price
            if current_total < best_h_cost:
                best_h_cost = current_total
                best_h_cfg = {"qty": total_drives, "cap": cap, "cost": best_h_cost, "total_tb": (data_drives * cap)}
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER V22.7 - FIXED HDD ENGINE")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t4, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Cameras ")
        self.nb.add(self.t2, text=" 2. Auto Audit ")
        self.nb.add(self.t4, text=" 3. Manual Split ")
        self.nb.add(self.t3, text=" 4. HDD Settings ")

        # --- TAB 1: CAMERAS ---
        f_in = ttk.Frame(self.t1, padding=10); f_in.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=10); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        btn_f = ttk.Frame(self.t1); btn_f.pack(fill="x", padx=10)
        ttk.Button(btn_f, text="Add Camera Type", command=self.save_camera).pack(side="left", padx=5)
        ttk.Button(btn_f, text="Clear List", command=self.clear_cams).pack(side="left")
        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=15)
        for c, h in zip(self.tree["columns"], ["Type","Qty","Mbps/ea","GB/Day"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 2: AUTO ---
        f_b = ttk.Frame(self.t2, padding=10); f_b.pack(fill="x")
        self.mode_var = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD"], state="readonly").pack(side="left")
        ttk.Button(f_b, text="RUN AUTO AUDIT", command=lambda: self.run_logic(True)).pack(side="left", padx=10)
        self.res_txt = tk.Text(self.t2, font=("Consolas", 10)); self.res_txt.pack(fill="both", expand=True, padx=5, pady=5)

        # --- TAB 3: MANUAL ---
        f_m = ttk.Frame(self.t4, padding=10); f_m.pack(fill="x")
        self.manual_slots = []
        for i, char in enumerate(["A", "B", "C", "D"]):
            ttk.Label(f_m, text=f"NVR {char}:").grid(row=i, column=0, pady=2)
            n_v, m_v = tk.StringVar(value="None"), tk.StringVar(value="RAID 5")
            cb = ttk.Combobox(f_m, textvariable=n_v, values=["None"]+[m[1] for m in ALL_MODELS], width=35, state="readonly")
            cb.grid(row=i, column=1, padx=5); ttk.Combobox(f_m, textvariable=m_v, values=["RAID 5", "RAID 6", "JBOD"], width=10, state="readonly").grid(row=i, column=2)
            self.manual_slots.append({"nvr": n_v, "mode": m_v})
        ttk.Button(f_m, text="CALCULATE MANUAL SPLIT", command=lambda: self.run_logic(False)).grid(row=5, column=1, pady=10)
        self.man_txt = tk.Text(self.t4, font=("Consolas", 10), bg="#f4f4f4"); self.man_txt.pack(fill="both", expand=True, padx=5, pady=5)

        # --- TAB 4: HDD SETTINGS (FIXED) ---
        f_hdd = ttk.Frame(self.t3, padding=20); f_hdd.pack(fill="both", expand=True)
        self.hdd_entries = {}
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            row, col = divmod(i, 2)
            ttk.Label(f_hdd, text=f"{cap}TB Price: $").grid(row=row, column=col*2, sticky="e", pady=5)
            ent = ttk.Entry(f_hdd, width=12)
            ent.insert(0, f"{self.hdd_prices[cap]:.2f}")
            ent.grid(row=row, column=col*2+1, padx=10, sticky="w")
            self.hdd_entries[cap] = ent
        
        ttk.Button(self.t3, text="SAVE HDD PRICES", command=self.update_hdd_prices).pack(pady=10)

    def update_hdd_prices(self):
        try:
            for cap, ent in self.hdd_entries.items():
                self.hdd_prices[cap] = float(ent.get())
            messagebox.showinfo("Success", "HDD Pricing updated for calculations!")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for HDD prices.")

    def save_camera(self):
        v = [self.ents[k].get() for k in ["Name", "Qty", "Mbps", "GB"]]
        if all(v): self.tree.insert("", "end", values=v)
    def clear_cams(self):
        for i in self.tree.get_children(): self.tree.delete(i)

    def generate_detailed_report(self, cfg, cams, t_c, t_m, t_t, title):
        report = f"--- {title} SOLUTION REPORT ---\n"
        report += f"TOTAL SYSTEM COST: ${cfg['total']:,.2f}\n"
        report += "="*75 + "\n\n"
        for i, u in enumerate(cfg['units']):
            report += f"UNIT #{i+1}: {u['m'][0]} [{u['m'][1]}] | MODE: {u['mode']}\n"
            report += f"CAMERAS: {u['c']} units total\n"
            report += f"THROUGHPUT: {u['mb']:.2f} / {u['m'][3]} Mbps Used\n"
            report += f"STORAGE: {u['tb']:.2f} TB Needed | {u['h']['total_tb']:.2f} TB Usable\n"
            report += f"DRIVES: {u['h']['qty']} x {u['h']['cap']}TB (Cost: ${u['h']['cost']:,.2f})\n"
            report += "-"*75 + "\n"
        return report

    def run_logic(self, auto):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": v[0], "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        if not cams: return messagebox.showwarning("Error", "Add cameras first")

        t_c, t_m, t_t = sum(c['qty'] for c in cams), sum(c['qty']*c['mbps'] for c in cams), sum(c['qty']*c['tb'] for c in cams)
        best_cost, best_cfg = float('inf'), None

        if auto:
            mode = self.mode_var.get()
            parity = 1 if mode == "RAID 5" else 2 if mode == "RAID 6" else 0
            for m in ALL_MODELS:
                if t_c <= m[2] and t_m <= m[3]:
                    hc, hd = get_best_hdd(t_t, m[4], parity, self.hdd_prices)
                    if hd and (m[5] + hc) < best_cost:
                        best_cost = m[5] + hc
                        best_cfg = {"total": best_cost, "units": [{"m": m, "c": t_c, "mb": t_m, "tb": t_t, "h": hd, "mode": mode}]}
        else:
            active = []
            for s in self.manual_slots:
                if s['nvr'].get() != "None":
                    hw = [m for m in ALL_MODELS if m[1] == s['nvr'].get()][0]
                    p = 1 if s['mode'].get()=="RAID 5" else 2 if s['mode'].get()=="RAID 6" else 0
                    active.append({"hw": hw, "mode": s['mode'].get(), "parity": p})
            if not active: return messagebox.showerror("Error", "Select at least NVR A")

            for r in range(1, 101):
                ratio = r / 100.0
                c1, m1, t1 = round(t_c * ratio), t_m * ratio, t_t * ratio
                if c1 == 0 or c1 > active[0]['hw'][2] or m1 > active[0]['hw'][3]: continue
                h1_c, h1_d = get_best_hdd(t1, active[0]['hw'][4], active[0]['parity'], self.hdd_prices)
                if not h1_d: continue

                rem_c, rem_ratio = t_c - c1, (1-ratio)
                if rem_c == 0:
                    cost = active[0]['hw'][5] + h1_c
                    if cost < best_cost:
                        best_cost = cost
                        best_cfg = {"total": cost, "units": [{"m": active[0]['hw'], "c": c1, "mb": m1, "tb": t1, "h": h1_d, "mode": active[0]['mode']}]}
                elif len(active) > 1:
                    others = active[1:]; sub_cfg, sub_h_cost, valid = [], 0, True
                    for i, u in enumerate(others):
                        o_ratio = rem_ratio / len(others)
                        cu = rem_c // len(others) + (1 if i < (rem_c % len(others)) else 0)
                        mu, tu = t_m * o_ratio, t_t * o_ratio
                        if cu > u['hw'][2] or mu > u['hw'][3]: valid = False; break
                        hc, hd = get_best_hdd(tu, u['hw'][4], u['parity'], self.hdd_prices)
                        if not hd: valid = False; break
                        sub_h_cost += hc
                        sub_cfg.append({"m": u['hw'], "c": cu, "mb": mu, "tb": tu, "h": hd, "mode": u['mode']})
                    if valid:
                        total = active[0]['hw'][5] + h1_c + sum(x['m'][5] for x in sub_cfg) + sub_h_cost
                        if total < best_cost:
                            best_cost = total
                            best_cfg = {"total": total, "units": [{"m": active[0]['hw'], "c": c1, "mb": m1, "tb": t1, "h": h1_d, "mode": active[0]['mode']}] + sub_cfg}

        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if best_cfg:
            txt.insert("1.0", self.generate_detailed_report(best_cfg, cams, t_c, t_m, t_t, "RESULT"))
        else:
            txt.insert("1.0", "NO VALID CONFIG FOUND")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("950x850")
    app = CCTVApp(root)
    root.mainloop()
