import tkinter as tk
from tkinter import ttk, messagebox
import math
import itertools
import json
import os

# --- FILE SETTINGS ---
PRICE_FILE = "hdd_prices.json"

# --- STRICT DATA SETS ---
RAID_ONLY = [
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
    ["2U Rack 175 Ch", "ADVER02RDK", 175, 1000, 12, 13854.20],
    ["2U Rack 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.50],
]
JBOD_ONLY = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50],
]
HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 160, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 320, 2, 770.85],
]
ALL_MODELS = RAID_ONLY + JBOD_ONLY + HOLIS_DATA

# Default prices if no file exists
DEFAULT_HDD_PRICES = {1: 93.75, 2: 122.95, 4: 218.75, 6: 281.25, 8: 395.85, 10: 416.7, 12: 687.50, 14: 1041.7, 18: 1052.1, 22: 1145.85, 24: 1447.95, 26: 1700.00}

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 1e-6: return 0, {"qty": 0, "cap": 0, "cost": 0, "total_tb": 0}
    best_h_cost, best_h_cfg = float('inf'), None
    for cap, price in sorted(price_dict.items()):
        min_d = 1 if parity == 0 else 2
        data_drives = max(math.ceil(required_tb / cap), min_d)
        total_drives = data_drives + parity
        if total_drives <= slots:
            curr_cost = total_drives * price
            if curr_cost < best_h_cost:
                best_h_cost, best_h_cfg = curr_cost, {"qty": total_drives, "cap": cap, "cost": curr_cost, "total_tb": (data_drives * cap)}
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER V28.0 - PERSISTENT PRICES")
        self.hdd_prices = self.load_prices()
        self.setup_ui()

    def load_prices(self):
        """Loads prices from JSON file or returns defaults."""
        if os.path.exists(PRICE_FILE):
            try:
                with open(PRICE_FILE, "r") as f:
                    # Convert keys back to integers since JSON stores them as strings
                    loaded = json.load(f)
                    return {int(k): float(v) for k, v in loaded.items()}
            except:
                return DEFAULT_HDD_PRICES.copy()
        return DEFAULT_HDD_PRICES.copy()

    def save_prices_to_file(self):
        """Saves current memory prices to the JSON file."""
        try:
            for cap, ent in self.hdd_entries.items():
                self.hdd_prices[cap] = float(ent.get())
            with open(PRICE_FILE, "w") as f:
                json.dump(self.hdd_prices, f)
            messagebox.showinfo("Success", f"Prices saved to {PRICE_FILE}")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for prices.")

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root); self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t4, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Cameras "); self.nb.add(self.t2, text=" 2. Auto Audit ")
        self.nb.add(self.t4, text=" 3. Manual Split "); self.nb.add(self.t3, text=" 4. HDD Settings ")

        # --- TAB 1 (CAMERAS) ---
        f_in = ttk.Frame(self.t1, padding=10); f_in.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=10); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        btn_f = ttk.Frame(self.t1); btn_f.pack(fill="x", padx=10)
        ttk.Button(btn_f, text="Add Camera", command=self.save_camera).pack(side="left", padx=5)
        ttk.Button(btn_f, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=5)
        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=15)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 2 (AUTO) ---
        f_b = ttk.Frame(self.t2, padding=10); f_b.pack(fill="x")
        self.mode_var = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD"], state="readonly").pack(side="left")
        ttk.Button(f_b, text="RUN BRUTE-FORCE AUTO", command=lambda: self.run_logic(True)).pack(side="left", padx=10)
        self.res_txt = tk.Text(self.t2, font=("Consolas", 10)); self.res_txt.pack(fill="both", expand=True, padx=5)

        # --- TAB 3 (MANUAL) ---
        f_m = ttk.Frame(self.t4, padding=10); f_m.pack(fill="x")
        self.manual_slots = []
        for i, char in enumerate(["A", "B", "C", "D"]):
            ttk.Label(f_m, text=f"NVR {char}:").grid(row=i, column=0, pady=2)
            n_v, m_v = tk.StringVar(value="None"), tk.StringVar(value="RAID 5")
            cb = ttk.Combobox(f_m, textvariable=n_v, values=["None"]+[m[1] for m in ALL_MODELS], width=35, state="readonly")
            cb.grid(row=i, column=1, padx=5); ttk.Combobox(f_m, textvariable=m_v, values=["RAID 5", "RAID 6", "JBOD"], width=10, state="readonly").grid(row=i, column=2)
            self.manual_slots.append({"nvr": n_v, "mode": m_v})
        ttk.Button(f_m, text="CALCULATE MANUAL SPLIT", command=lambda: self.run_logic(False)).grid(row=5, column=1, pady=10)
        self.man_txt = tk.Text(self.t4, font=("Consolas", 10), bg="#f4f4f4"); self.man_txt.pack(fill="both", expand=True, padx=5)

        # --- TAB 4 (HDD SETTINGS) ---
        f_hdd = ttk.Frame(self.t3, padding=20); f_hdd.pack(fill="both", expand=True)
        self.hdd_entries = {}
        # Display sorted by capacity
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            row, col = divmod(i, 2)
            ttk.Label(f_hdd, text=f"{cap}TB: $").grid(row=row, column=col*2, sticky="e", pady=2)
            ent = ttk.Entry(f_hdd, width=10)
            ent.insert(0, f"{self.hdd_prices[cap]:.2f}")
            ent.grid(row=row, column=col*2+1, padx=5)
            self.hdd_entries[cap] = ent
        
        ttk.Button(self.t3, text="SAVE PRICES PERMANENTLY", command=self.save_prices_to_file).pack(pady=10)

    # --- LOGIC & HELPERS ---
    def save_camera(self):
        v = [self.ents[k].get() for k in ["Name", "Qty", "Mbps", "GB"]]
        if all(v): self.tree.insert("", "end", values=v); [self.ents[k].delete(0, tk.END) for k in self.ents]

    def delete_selected(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def on_double_click(self, event):
        item = self.tree.selection()[0]; v = self.tree.item(item, "values")
        for i, k in enumerate(["Name", "Qty", "Mbps", "GB"]): self.ents[k].delete(0, tk.END); self.ents[k].insert(0, v[i])
        self.tree.delete(item)

    def generate_detailed_report(self, cfg, title):
        report = f"--- {title} SOLUTION REPORT ---\nFINAL TOTAL SYSTEM COST: ${cfg['total']:,.2f}\n" + "="*75 + "\n\n"
        for i, u in enumerate(cfg['units']):
            report += f"UNIT #{i+1}: {u['m'][0]} [{u['m'][1]}]\nCONFIGURATION MODE: {u['mode']}\n" + "-"*50 + "\n"
            report += f"CAMERAS ASSIGNED: {u['c_total']} total\n"
            for cam_name, cam_qty in u['cam_breakdown'].items():
                if cam_qty > 0: report += f"  > {cam_name}: {cam_qty} units\n"
            load_pct = (u['mb'] / u['m'][3]) * 100 if u['m'][3] > 0 else 0
            report += f"\nTHROUGHPUT ANALYTICS:\n  - Max Capacity:  {u['m'][3]:>10} Mbps\n  - Needed/Used:   {u['mb']:>10.2f} Mbps\n"
            report += f"  - Headroom:      {(u['m'][3] - u['mb']):>10.2f} Mbps ({load_pct:.1f}% Load)\n"
            report += f"\nSTORAGE ANALYTICS:\n  - Physical Drive: {u['h']['qty']}x {u['h']['cap']}TB\n  - Max Slots:      {u['m'][4]:>10} slots available\n"
            report += f"  - Storage Needed: {u['tb']:>10.2f} TB\n  - Usable Storage: {u['h']['total_tb']:>10.2f} TB\n"
            report += f"  - Storage Margin: {(u['h']['total_tb'] - u['tb']):>10.2f} TB Over-provisioned\n\n" + "="*75 + "\n\n"
        return report

    def run_logic(self, auto):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": v[0], "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        if not cams: return
        t_c = sum(c['qty'] for c in cams)
        t_m = sum(c['qty']*c['mbps'] for c in cams)
        t_t = sum(c['qty']*c['tb'] for c in cams)
        
        best_cfg, best_total_cost = None, float('inf')

        if auto:
            mode = self.mode_var.get()
            parity = 1 if mode == "RAID 5" else 2 if mode == "RAID 6" else 0
            search_list = RAID_ONLY if parity > 0 else (RAID_ONLY + JBOD_ONLY + HOLIS_DATA)

            for num_units in range(1, 3):
                for combo in itertools.combinations_with_replacement(search_list, num_units):
                    splits = [1.0] if num_units == 1 else [x/10.0 for x in range(1, 10)]
                    for r1 in splits:
                        u_list, running_cams = [], [dict(c) for c in cams]
                        u1_breakdown, u1_mb, u1_tb, u1_c = {}, 0, 0, 0
                        for c in running_cams:
                            take = math.floor(c['qty'] * r1) if num_units > 1 else c['qty']
                            u1_breakdown[c['name']] = take
                            u1_mb += take * c['mbps']; u1_tb += take * c['tb']; u1_c += take
                            c['qty'] -= take
                        
                        hc1, hd1 = get_best_hdd(u1_tb, combo[0][4], parity, self.hdd_prices)
                        if not (hd1 and u1_c <= combo[0][2] and u1_mb <= combo[0][3]): continue
                        u_list.append({"m": combo[0], "c_total": u1_c, "cam_breakdown": u1_breakdown, "mb": u1_mb, "tb": u1_tb, "h": hd1, "mode": mode})

                        if num_units == 2:
                            u2_breakdown, u2_mb, u2_tb, u2_c = {}, 0, 0, 0
                            for c in running_cams:
                                take = c['qty']
                                u2_breakdown[c['name']] = take
                                u2_mb += take * c['mbps']; u2_tb += take * c['tb']; u2_c += take
                            
                            hc2, hd2 = get_best_hdd(u2_tb, combo[1][4], parity, self.hdd_prices)
                            if not (hd2 and u2_c <= combo[1][2] and u2_mb <= combo[1][3]): continue
                            u_list.append({"m": combo[1], "c_total": u2_c, "cam_breakdown": u2_breakdown, "mb": u2_mb, "tb": u2_tb, "h": hd2, "mode": mode})

                        total_cost = sum((u['m'][5] + u['h']['cost']) for u in u_list)
                        if total_cost < best_total_cost:
                            best_total_cost = total_cost
                            best_cfg = {"total": total_cost, "units": u_list}
        else:
            active = []
            for s in self.manual_slots:
                if s['nvr'].get() != "None":
                    hw = [m for m in ALL_MODELS if m[1] == s['nvr'].get()][0]
                    p = 1 if s['mode'].get()=="RAID 5" else 2 if s['mode'].get()=="RAID 6" else 0
                    active.append({"hw": hw, "mode": s['mode'].get(), "parity": p})
            if active:
                num, running_cams, res_units, running_cost = len(active), [dict(c) for c in cams], [], 0
                for i, u in enumerate(active):
                    u_breakdown, u_mb, u_tb, u_c = {}, 0, 0, 0
                    for c in running_cams:
                        take = math.floor(c['qty']/num) if i < num-1 else c['qty']
                        u_breakdown[c['name']] = take
                        u_mb += take * c['mbps']; u_tb += take * c['tb']; u_c += take
                        c['qty'] -= take
                    hc, hd = get_best_hdd(u_tb, u['hw'][4], u['parity'], self.hdd_prices)
                    if hd and u_c <= u['hw'][2] and u_mb <= u['hw'][3]:
                        running_cost += (u['hw'][5] + hc)
                        res_units.append({"m": u['hw'], "c_total": u_c, "cam_breakdown": u_breakdown, "mb": u_mb, "tb": u_tb, "h": hd, "mode": u['mode']})
                if len(res_units) == num: best_cfg = {"total": running_cost, "units": res_units}

        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if best_cfg: txt.insert("1.0", self.generate_detailed_report(best_cfg, "AUTO" if auto else "MANUAL"))
        else: txt.insert("1.0", "NO VALID CONFIG FOUND")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("950x850"); app = CCTVApp(root); root.mainloop()
