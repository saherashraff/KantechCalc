import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import itertools
import json
import os
from datetime import datetime

# --- DATA PERSISTENCE ---
DATA_FILE = "system_data.json"

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
DEFAULT_HDD_PRICES = {1: 87,3: 145 , 2: 131, 4: 239, 6: 375, 8: 427, 10: 500, 12: 614, 14: 1114, 18: 1291, 22: 1226, 24: 1568, 26: 2600}

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
        self.root.title("CCTV MASTER V33.3 - FAIL-SAFE BALANCING")
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
        titles = ["1. Cameras", "2. Auto Audit", "3. Manual Split", "4. HDD Prices", "5. NVR Prices", "6. Add NVR"]
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
        self.tree = ttk.Treeview(self.tabs[0], columns=("N","Q","M","G"), show="headings", selectmode="browse"); self.tree.pack(fill="both", expand=True)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.bind("<Double-1>", self.load_camera_to_edit)

        # TAB 2 & 3: LOGIC & TEXT
        self.mode_var = tk.StringVar(value="RAID 5")
        f_a = ttk.Frame(self.tabs[1], padding=10); f_a.pack(fill="x")
        ttk.Combobox(f_a, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD"], state="readonly").pack(side="left")
        ttk.Button(f_a, text="RUN AUTO", command=lambda: self.run_logic(True)).pack(side="left", padx=10)
        self.res_txt = tk.Text(self.tabs[1], font=("Consolas", 10)); self.res_txt.pack(fill="both", expand=True)

        self.manual_slots = []
        for i in range(5):
            f = ttk.Frame(self.tabs[2], padding=5); f.pack(fill="x")
            nv, mv = tk.StringVar(value="None"), tk.StringVar(value="RAID 5")
            cb = ttk.Combobox(f, textvariable=nv, width=35, state="readonly"); cb.pack(side="left")
            ttk.Combobox(f, textvariable=mv, values=["RAID 5", "RAID 6", "JBOD"], width=10, state="readonly").pack(side="left", padx=5)
            self.manual_slots.append((nv, mv, cb))
        ttk.Button(self.tabs[2], text="CALCULATE MANUAL", command=lambda: self.run_logic(False)).pack(pady=5)
        ttk.Button(self.tabs[2], text="Export to File", command=self.export_to_file).pack(pady=2)
        self.man_txt = tk.Text(self.tabs[2], font=("Consolas", 10), bg="#f4f4f4"); self.man_txt.pack(fill="both", expand=True)
        
        self.refresh_nvr_dropdowns(); self.setup_mgt()

    def load_camera_to_edit(self, event):
        item = self.tree.selection()[0]; vals = self.tree.item(item)['values']
        for k, v in zip(["Name", "Qty", "Mbps", "GB"], vals): self.ents[k].delete(0, tk.END); self.ents[k].insert(0, v)

    def save_camera(self):
        v = [self.ents[k].get() for k in ["Name", "Qty", "Mbps", "GB"]]
        if all(v): 
            for item in self.tree.get_children():
                if str(self.tree.item(item)['values'][0]) == v[0]: self.tree.delete(item)
            self.tree.insert("", "end", values=v)

    def delete_camera(self): 
        for s in self.tree.selection(): self.tree.delete(s)

    def refresh_nvr_dropdowns(self):
        names = ["None"] + [n[1] for n in self.nvr_list]
        for nv, _, cb in self.manual_slots: cb['values'] = names

    def generate_detailed_report(self, cfg, title):
        report = f"{'='*80}\n"
        report += f"{title} SYSTEM DESIGN SPECIFICATION\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"{'='*80}\n\n"
        report += f"TOTAL SYSTEM ESTIMATE: ${cfg['total']:,.2f}\n"
        report += f"TOTAL HARDWARE UNITS:  {len(cfg['units'])}\n\n"
        
        for i, u in enumerate(cfg['units']):
            report += f"UNIT #{i+1} [SKU: {u['m'][1]}]\n"
            report += f"{'-'*40}\n"
            report += f"  Hardware:      {u['m'][0]}\n"
            report += f"  Storage Mode:  {u['mode']}\n"
            report += f"  Unit Cost:     ${u['m'][5]:,.2f}\n\n"
            
            report += f"  ASSIGNED CAMERAS ({u['c_total']}):\n"
            for c_n, c_q in u['cam_breakdown'].items():
                if c_q > 0: report += f"    - {c_n:<20} : {c_q} Units\n"
            
            report += f"\n  PERFORMANCE METRICS:\n"
            mb_pct = (u['mb'] / u['m'][3]) * 100
            report += f"    Throughput:  {u['mb']:>7.2f} / {u['m'][3]:>4} Mbps ({mb_pct:3.1f}% Load)\n"
            report += f"    Channels:    {u['c_total']:>7} / {u['m'][2]:>4} Ports Used\n"
            
            report += f"\n  STORAGE CONFIGURATION:\n"
            report += f"    Disk Array:  {u['h']['qty']}x {u['h']['cap']}TB Enterprise HDD\n"
            report += f"    Slots Used:  {u['h']['qty']} / {u['m'][4]} Available Slots\n"
            report += f"    Usable TB:   {u['h']['total_tb']:>7.2f} TB\n"
            report += f"    Required TB: {u['tb']:>7.2f} TB\n"
            report += f"    Disk Margin: {(u['h']['total_tb'] - u['tb']):>7.2f} TB Spare\n"
            report += f"    HDD Cost:    ${u['h']['cost']:,.2f}\n"
            report += f"\n{'='*80}\n\n"

        self.last_report = report
        return report

    def setup_mgt(self):
        # HDD/NVR Mgt tabs setup (kept same for brevity)
        self.hdd_entries = {}
        fh = ttk.Frame(self.tabs[3], padding=20); fh.pack()
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2); ttk.Label(fh, text=f"{cap}TB: $").grid(row=r, column=c*2)
            e = ttk.Entry(fh, width=10); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1); self.hdd_entries[cap] = e
        ttk.Button(self.tabs[3], text="Save HDDs", command=self.save_hdd_ui).pack()
        self.nvr_container = ttk.Frame(self.tabs[4]); self.nvr_container.pack(fill="both", expand=True)
        self.refresh_nvr_price_tab()
        fn = ttk.Frame(self.tabs[5], padding=20); fn.pack()
        self.nf = {}
        for i, lab in enumerate(["Name", "SKU", "CH", "MB", "Slots", "Price"]):
            ttk.Label(fn, text=lab).grid(row=i, column=0); e = ttk.Entry(fn); e.grid(row=i, column=1); self.nf[lab] = e
        self.na = tk.StringVar(value="RAID"); ttk.Combobox(fn, textvariable=self.na, values=["RAID", "JBOD"]).grid(row=6, column=1)
        ttk.Button(fn, text="ADD NVR", command=self.add_new_nvr).grid(row=7, columnspan=2)

    def delete_nvr(self, idx): self.nvr_list.pop(idx); self.save_all_data(); self.refresh_nvr_price_tab(); self.refresh_nvr_dropdowns()
    def save_nvr_prices_ui(self):
        for i, e in enumerate(self.npe): self.nvr_list[i][5] = float(e.get())
        self.save_all_data(); messagebox.showinfo("Saved", "NVR Database Updated")
    def save_hdd_ui(self):
        for c, e in self.hdd_entries.items(): self.hdd_prices[c] = float(e.get())
        self.save_all_data(); messagebox.showinfo("Saved", "HDD Prices Updated")
    def add_new_nvr(self):
        try:
            row = [self.nf[k].get() for k in ["Name", "SKU"]] + [int(self.nf["CH"].get()), int(self.nf["MB"].get()), int(self.nf["Slots"].get()), float(self.nf["Price"].get()), self.na.get()]
            self.nvr_list.append(row); self.save_all_data(); self.refresh_nvr_dropdowns(); self.refresh_nvr_price_tab()
        except: pass
    def refresh_nvr_price_tab(self):
        for w in self.nvr_container.winfo_children(): w.destroy()
        self.npe = []
        for i, n in enumerate(self.nvr_list):
            ttk.Label(self.nvr_container, text=f"{n[0]}").grid(row=i, column=0); e = ttk.Entry(self.nvr_container, width=12)
            e.insert(0, f"{n[5]:.2f}"); e.grid(row=i, column=1); self.npe.append(e)
            ttk.Button(self.nvr_container, text="X", command=lambda idx=i: self.delete_nvr(idx)).grid(row=i, column=2)
        ttk.Button(self.nvr_container, text="Update", command=self.save_nvr_prices_ui).grid(row=len(self.nvr_list), columnspan=3)
    def export_to_file(self):
        if self.last_report:
            f = filedialog.asksaveasfilename(defaultextension=".txt"); 
            if f: 
                with open(f, "w") as file: file.write(self.last_report)

    def calculate_units(self, cam_list, hw_config, use_even_split=False):
        """Core math engine for a specific combination of NVRs"""
        u_list, cur_cams = [], [dict(c) for c in cam_list]
        num = len(hw_config)
        
        for i in range(num):
            u_brk, u_mb, u_tb, u_c = {}, 0, 0, 0
            for c in cur_cams:
                if use_even_split:
                    # Forced Balance: Take fair share of remaining qty
                    take = math.ceil(c['qty'] / (num - i))
                else:
                    # Original Split: Take what's left
                    take = c['qty']
                
                take = min(c['qty'], take)
                u_brk[c['name']] = take
                u_mb += take * c['mbps']
                u_tb += take * c['tb']
                u_c += take
                c['qty'] -= take
            
            hc, hd = get_best_hdd(u_tb, hw_config[i]['m'][4], hw_config[i]['p'], self.hdd_prices)
            
            # Validation
            fails = []
            if u_c > hw_config[i]['m'][2]: fails.append(f"Ports({u_c}/{hw_config[i]['m'][2]})")
            if u_mb > hw_config[i]['m'][3]: fails.append(f"Mbps({u_mb}/{hw_config[i]['m'][3]})")
            if not hd: fails.append("HDD Slots Full")
            
            if fails: return None, fails # Return failure details
            u_list.append({"m": hw_config[i]['m'], "c_total": u_c, "cam_breakdown": u_brk, "mb": u_mb, "tb": u_tb, "h": hd, "mode": hw_config[i]['mode']})
        
        return u_list, None

    def run_logic(self, auto):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": v[0], "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        if not cams: return
        
        best_cfg, best_total_cost, debug_info = None, float('inf'), []

        if auto:
            # Auto Logic (Stays in Stage 1/2 internally)
            mode = self.mode_var.get(); parity = 1 if mode == "RAID 5" else 2 if mode == "RAID 6" else 0
            search_list = [n for n in self.nvr_list if n[6] == "RAID"] if parity > 0 else self.nvr_list
            for num_units in range(1, 3):
                for combo in itertools.combinations_with_replacement(search_list, num_units):
                    hw_c = [{"m": n, "mode": mode, "p": parity} for n in combo]
                    # Try Balanced First in Auto for stability
                    res, err = self.calculate_units(cams, hw_c, use_even_split=True)
                    if res:
                        cost = sum(x['m'][5] + x['h']['cost'] for x in res)
                        if cost < best_total_cost: best_total_cost, best_cfg = cost, {"total": cost, "units": res}
        else:
            # MANUAL MODE: TRIGGER STAGE 1 (Optimized) -> STAGE 2 (Balanced Fail-safe)
            active_hw = []
            for nv, mv, cb in self.manual_slots:
                if nv.get() != "None":
                    hw = next(n for n in self.nvr_list if n[1] == nv.get())
                    active_hw.append({"m": hw, "mode": mv.get(), "p": (1 if mv.get() == "RAID 5" else 2 if mv.get() == "RAID 6" else 0)})
            
            if active_hw:
                # STAGE 1: Trying Optimized Imbalance
                res, err = self.calculate_units(cams, active_hw, use_even_split=False)
                if res:
                    best_cfg = {"total": sum(x['m'][5] + x['h']['cost'] for x in res), "units": res}
                else:
                    # STAGE 2: Optimized failed, trigger Balanced Fail-safe
                    res, err_b = self.calculate_units(cams, active_hw, use_even_split=True)
                    if res:
                        best_cfg = {"total": sum(x['m'][5] + x['h']['cost'] for x in res), "units": res}
                    else:
                        debug_info = err_b # Report why even a balanced split failed

        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if best_cfg: txt.insert("1.0", self.generate_detailed_report(best_cfg, "AUTO" if auto else "MANUAL"))
        else:
            txt.insert("1.0", "--- SYSTEM CRITICAL: SPLIT FAILED ---\n\n")
            txt.insert(tk.END, f"FAIL REASON: {debug_info}\n\n")
            txt.insert(tk.END, "The 84 cameras cannot be split across these NVRs without exceeding throughput or channel limits.\n")
            txt.insert(tk.END, "SOLUTION: Add one more unit or upgrade to a 64-Ch NVR.")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("1100x950"); app = CCTVApp(root); root.mainloop()
