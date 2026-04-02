import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import itertools
import json
import os
from datetime import datetime

DATA_FILE = "system_data.json"

# UPDATED HDD PRICES
DEFAULT_HDD_PRICES = {
    1: 87.00, 2: 131.00, 3: 145.00, 4: 239.00, 6: 375.00, 
    8: 427.00, 10: 500.00, 12: 614.00, 14: 1114.00, 
    18: 1291.00, 22: 1226.00, 24: 1568.00, 26: 2600.00
}

# DATABASE: Note the 7th column (RAID vs JBOD)
DEFAULT_NVR_DATA = [
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00, "RAID"],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70, "RAID"],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70, "RAID"],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00, "RAID"],
    ["2U Rack 175 Ch", "ADVER02RDK", 175, 1000, 12, 13854.20, "RAID"],
    ["2U Rack 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.50, "RAID"],
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00, "JBOD"],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70, "JBOD"],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50, "JBOD"],
    ["Holis 8 Ch", "HRN-08013P", 8, 160, 1, 520.85, "JBOD"],
    ["Holis 16 Ch", "HRN-16023P", 16, 320, 2, 770.85, "JBOD"]
]

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 0.01: return 0, {"qty": 0, "cap": 0, "cost": 0, "total_tb": 0}
    best_h_cost, best_h_cfg = float('inf'), None
    for cap in sorted(price_dict.keys()):
        price = price_dict[cap]
        # For JBOD, parity is 0. For RAID 5, parity is 1.
        min_data_drives = 1 if parity == 0 else 2
        data_req = max(math.ceil(required_tb / cap), min_data_drives)
        total_drives = data_req + parity
        if total_drives <= slots:
            cost = total_drives * price
            if cost < best_h_cost:
                best_h_cost, best_h_cfg = cost, {"qty": total_drives, "cap": cap, "cost": cost, "total_tb": (data_req * cap)}
    return (best_h_cost, best_h_cfg) if best_h_cfg else (None, None)

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER V33.5 - MIX & MATCH AUTO")
        self.last_report = ""
        self.load_all_data()
        self.setup_ui()

    def load_all_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    self.hdd_prices = {int(k): float(v) for k, v in data.get("hdd", DEFAULT_HDD_PRICES).items()}
                    self.nvr_list = data.get("nvr", DEFAULT_NVR_DATA)
            except: self.hdd_prices, self.nvr_list = DEFAULT_HDD_PRICES.copy(), [list(x) for x in DEFAULT_NVR_DATA]
        else: self.hdd_prices, self.nvr_list = DEFAULT_HDD_PRICES.copy(), [list(x) for x in DEFAULT_NVR_DATA]

    def save_all_data(self):
        with open(DATA_FILE, "w") as f: json.dump({"hdd": self.hdd_prices, "nvr": self.nvr_list}, f)

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root); self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.tabs = [ttk.Frame(self.nb) for _ in range(6)]
        titles = ["1. Cameras", "2. Auto (Mix & Match)", "3. Manual", "4. HDDs", "5. NVRs", "6. Add NVR"]
        for tab, title in zip(self.tabs, titles): self.nb.add(tab, text=title)

        # TAB 1: CAMERAS
        f_in = ttk.Frame(self.tabs[0], padding=10); f_in.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=12); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        btn_f = ttk.Frame(self.tabs[0]); btn_f.pack(pady=5)
        ttk.Button(btn_f, text="Add/Update", command=self.save_camera).pack(side="left", padx=5)
        ttk.Button(btn_f, text="Delete", command=self.delete_camera).pack(side="left", padx=5)
        self.tree = ttk.Treeview(self.tabs[0], columns=("N","Q","M","G"), show="headings"); self.tree.pack(fill="both", expand=True)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)

        # TAB 2: AUTO
        self.auto_mode = tk.StringVar(value="RAID 5")
        f_a = ttk.Frame(self.tabs[1], padding=10); f_a.pack(fill="x")
        ttk.Label(f_a, text="System Standard:").pack(side="left")
        ttk.Combobox(f_a, textvariable=self.auto_mode, values=["RAID 5", "RAID 6", "JBOD"], state="readonly").pack(side="left", padx=5)
        ttk.Button(f_a, text="FIND BEST MIXED SOLUTION", command=lambda: self.run_logic(True)).pack(side="left", padx=10)
        self.res_txt = tk.Text(self.tabs[1], font=("Consolas", 10)); self.res_txt.pack(fill="both", expand=True)

        # TAB 3: MANUAL
        self.manual_slots = []
        for i in range(5):
            f = ttk.Frame(self.tabs[2], padding=5); f.pack(fill="x")
            nv, mv = tk.StringVar(value="None"), tk.StringVar(value="RAID 5")
            cb = ttk.Combobox(f, textvariable=nv, width=35, state="readonly"); cb.pack(side="left")
            # Set callback to auto-switch mode if hardware is JBOD
            cb.bind("<<ComboboxSelected>>", lambda e, var=nv, m_var=mv: self.auto_switch_mode(var, m_var))
            ttk.Combobox(f, textvariable=mv, values=["RAID 5", "RAID 6", "JBOD"], width=10, state="readonly").pack(side="left", padx=5)
            self.manual_slots.append((nv, mv, cb))
        ttk.Button(self.tabs[2], text="CALCULATE MANUAL", command=lambda: self.run_logic(False)).pack(pady=5)
        self.man_txt = tk.Text(self.tabs[2], font=("Consolas", 10), bg="#f4f4f4"); self.man_txt.pack(fill="both", expand=True)
        
        # TAB 6: ADD NVR (FIXED)
        fn = ttk.Frame(self.tabs[5], padding=20); fn.pack()
        self.nf = {}
        fields = [("Model Name", "Name"), ("Model SKU", "SKU"), ("Channels", "CH"), ("Mbps Limit", "MB"), ("HDD Slots", "Slots"), ("Unit Price", "Price")]
        for i, (lab, key) in enumerate(fields):
            ttk.Label(fn, text=lab).grid(row=i, column=0, sticky="w", pady=2)
            e = ttk.Entry(fn); e.grid(row=i, column=1, pady=2); self.nf[key] = e
        ttk.Label(fn, text="Default Mode").grid(row=6, column=0, sticky="w")
        self.na = tk.StringVar(value="RAID"); ttk.Combobox(fn, textvariable=self.na, values=["RAID", "JBOD"], state="readonly").grid(row=6, column=1)
        ttk.Button(fn, text="SAVE NEW NVR TO DATABASE", command=self.add_new_nvr).grid(row=7, columnspan=2, pady=10)

        self.refresh_nvr_dropdowns(); self.setup_mgt()

    def auto_switch_mode(self, hw_var, mode_var):
        sku = hw_var.get()
        if sku == "None": return
        hw = next(n for n in self.nvr_list if n[1] == sku)
        if hw[6] == "JBOD": mode_var.set("JBOD")
        else: mode_var.set("RAID 5")

    def save_camera(self):
        v = [self.ents[k].get() for k in ["Name", "Qty", "Mbps", "GB"]]
        if all(v): 
            for item in self.tree.get_children():
                if str(self.tree.item(item)['values'][0]) == v[0]: self.tree.delete(item)
            self.tree.insert("", "end", values=v)

    def delete_camera(self): 
        for s in self.tree.selection(): self.tree.delete(s)

    def add_new_nvr(self):
        try:
            new_row = [
                self.nf["Name"].get(), self.nf["SKU"].get(),
                int(self.nf["CH"].get()), int(self.nf["MB"].get()),
                int(self.nf["Slots"].get()), float(self.nf["Price"].get()),
                self.na.get()
            ]
            self.nvr_list.append(new_row); self.save_all_data()
            self.refresh_nvr_dropdowns(); messagebox.showinfo("Success", "NVR Added to Database")
        except Exception as e: messagebox.showerror("Error", f"Invalid Data: {e}")

    def refresh_nvr_dropdowns(self):
        names = ["None"] + [n[1] for n in self.nvr_list]
        for _, _, cb in self.manual_slots: cb['values'] = names

    def setup_mgt(self):
        self.hdd_entries = {}
        fh = ttk.Frame(self.tabs[3], padding=20); fh.pack()
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2); ttk.Label(fh, text=f"{cap}TB: $").grid(row=r, column=c*2)
            e = ttk.Entry(fh, width=10); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1); self.hdd_entries[cap] = e
        ttk.Button(self.tabs[3], text="Update HDD Prices", command=self.save_hdd_ui).pack()

    def save_hdd_ui(self):
        for c, e in self.hdd_entries.items(): self.hdd_prices[c] = float(e.get())
        self.save_all_data(); messagebox.showinfo("Saved", "HDD Prices Updated")

    def generate_detailed_report(self, cfg, title):
        report = f"{'='*80}\n{title} DESIGN REPORT\n{'='*80}\n"
        report += f"TOTAL ESTIMATED COST: ${cfg['total']:,.2f}\n\n"
        for i, u in enumerate(cfg['units']):
            report += f"UNIT #{i+1}: {u['m'][0]} ({u['m'][1]})\n"
            report += f"{'-'*40}\n"
            report += f"  Configuration: {u['mode']}\n"
            report += f"  Total Cameras: {u['c_total']}\n"
            for c_n, c_q in u['cam_breakdown'].items():
                if c_q > 0: report += f"    - {c_n}: {c_q} units\n"
            mb_p = (u['mb'] / u['m'][3]) * 100
            report += f"  Performance:   {u['mb']:.1f}/{u['m'][3]} Mbps ({mb_p:.1f}% Load)\n"
            report += f"  HDD Setup:     {u['h']['qty']}x {u['h']['cap']}TB Drives\n"
            report += f"  Storage Cap:   {u['h']['total_tb']:.2f} TB Usable (Needs {u['tb']:.2f} TB)\n"
            report += f"  Unit Subtotal: ${ (u['m'][5] + u['h']['cost']):,.2f}\n\n"
        self.last_report = report
        return report

    def calculate_split(self, cam_list, hw_config, ratio=1.0, use_even=False):
        u_list, cur_cams = [], [dict(c) for c in cam_list]
        num = len(hw_config)
        for i in range(num):
            u_brk, u_mb, u_tb, u_c = {}, 0, 0, 0
            for c in cur_cams:
                if use_even: take = math.ceil(c['qty'] / (num - i))
                else: take = math.floor(c['qty'] * ratio) if i < num-1 else c['qty']
                
                take = min(c['qty'], take)
                u_brk[c['name']] = take; u_mb += take*c['mbps']; u_tb += take*c['tb']; u_c += take
                c['qty'] -= take
            
            # Correct Parity logic for SKU
            parity = 0 if hw_config[i]['mode'] == "JBOD" else (1 if hw_config[i]['mode'] == "RAID 5" else 2)
            # Override parity if hardware is physically JBOD only
            if hw_config[i]['m'][6] == "JBOD": parity = 0
            
            hc, hd = get_best_hdd(u_tb, hw_config[i]['m'][4], parity, self.hdd_prices)
            if not hd or u_c > hw_config[i]['m'][2] or u_mb > hw_config[i]['m'][3]: return None
            u_list.append({"m": hw_config[i]['m'], "c_total": u_c, "cam_breakdown": u_brk, "mb": u_mb, "tb": u_tb, "h": hd, "mode": hw_config[i]['mode'] if parity > 0 else "JBOD"})
        return u_list

    def run_logic(self, auto):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": str(v[0]), "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        if not cams: return
        
        best_cfg, best_cost = None, float('inf')

        if auto:
            mode = self.auto_mode.get()
            # MIX & MATCH: Try combinations of ALL RAID NVRs or ALL JBOD NVRs
            search_pool = [n for n in self.nvr_list if n[6] == ("JBOD" if mode == "JBOD" else "RAID")]
            
            for n_u in range(1, 4): # Try up to 3 units mixed
                for combo in itertools.combinations_with_replacement(search_pool, n_u):
                    hw_c = [{"m": n, "mode": mode} for n in combo]
                    # Try 1% incremental split AND even split
                    for r in [x/100.0 for x in range(10, 91)] + [0.5]:
                        res = self.calculate_split(cams, hw_c, r, False)
                        if not res: res = self.calculate_split(cams, hw_c, 1.0, True)
                        if res:
                            cost = sum(x['m'][5] + x['h']['cost'] for x in res)
                            if cost < best_cost: best_cost, best_cfg = cost, {"total": cost, "units": res}
        else:
            active_hw = []
            for nv, mv, _ in self.manual_slots:
                if nv.get() != "None":
                    hw = next(n for n in self.nvr_list if n[1] == nv.get())
                    active_hw.append({"m": hw, "mode": mv.get()})
            if active_hw:
                # Manual tries 1% increments then Even Split
                for r in [x/100.0 for x in range(1, 100)]:
                    res = self.calculate_split(cams, active_hw, r, False)
                    if res:
                        cost = sum(x['m'][5] + x['h']['cost'] for x in res)
                        if cost < best_cost: best_cost, best_cfg = cost, {"total": cost, "units": res}
                if not best_cfg: # Last resort even split
                    res = self.calculate_split(cams, active_hw, 1.0, True)
                    if res: best_cfg = {"total": sum(x['m'][5] + x['h']['cost'] for x in res), "units": res}

        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if best_cfg: txt.insert("1.0", self.generate_detailed_report(best_cfg, "AUTO" if auto else "MANUAL"))
        else: txt.insert("1.0", "ERROR: Could not find a valid split. Try adding more NVR units or upgrading models.")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("1100x950"); app = CCTVApp(root); root.mainloop()
