import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import itertools
import json
import os
from datetime import datetime

DATA_FILE = "system_data.json"

# --- CONFIGURATION DATA ---
DEFAULT_HDD_PRICES = {
    1: 87.00, 2: 131.00, 3: 145.00, 4: 239.00, 6: 375.00, 
    8: 427.00, 10: 500.00, 12: 614.00, 14: 1114.00, 
    18: 1291.00, 22: 1226.00, 24: 1568.00, 26: 2600.00
}

DEFAULT_NVR_DATA = [
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00, "RAID"],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70, "RAID"],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70, "RAID"],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00, "RAID"],
    ["2U Rack 175 Ch", "ADVER00RN2K", 175, 1000, 12, 13854.20, "RAID"],
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
        min_d = 1 if parity == 0 else 2
        data_req = max(math.ceil(required_tb / cap), min_d)
        total_drives = data_req + parity
        if total_drives <= slots:
            cost = total_drives * price
            if cost < best_h_cost:
                best_h_cost, best_h_cfg = cost, {"qty": total_drives, "cap": cap, "cost": cost, "total_tb": (data_req * cap)}
    return (best_h_cost, best_h_cfg) if best_h_cfg else (None, None)

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER V34.1 - SMART MANUAL MODE")
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
        titles = ["1. Cameras", "2. Auto", "3. Manual", "4. HDDs", "5. NVRs", "6. Add NVR"]
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

        self.storage_buffer = tk.StringVar(value="0")

        # TAB 2: AUTO
        self.auto_mode = tk.StringVar(value="RAID 5")
        f_a = ttk.Frame(self.tabs[1], padding=10); f_a.pack(fill="x")
        ttk.Combobox(f_a, textvariable=self.auto_mode, values=["RAID 5", "RAID 6", "JBOD"], state="readonly", width=10).pack(side="left")
        ttk.Label(f_a, text=" Buffer %:").pack(side="left")
        ttk.Entry(f_a, textvariable=self.storage_buffer, width=5).pack(side="left", padx=5)
        ttk.Button(f_a, text="RUN AUTO", command=lambda: self.run_logic(True)).pack(side="left", padx=5)
        ttk.Button(f_a, text="EXPORT", command=self.export_to_file).pack(side="left")
        self.res_txt = tk.Text(self.tabs[1], font=("Consolas", 10)); self.res_txt.pack(fill="both", expand=True)

        # TAB 3: MANUAL
        f_m_top = ttk.Frame(self.tabs[2], padding=5); f_m_top.pack(fill="x")
        ttk.Label(f_m_top, text="Global Storage Buffer %:").pack(side="left")
        ttk.Entry(f_m_top, textvariable=self.storage_buffer, width=5).pack(side="left", padx=5)
        
        self.manual_slots = []
        for i in range(8):
            f = ttk.Frame(self.tabs[2], padding=2); f.pack(fill="x")
            nv, mv = tk.StringVar(value="None"), tk.StringVar(value="RAID 5")
            cb = ttk.Combobox(f, textvariable=nv, width=45, state="readonly"); cb.pack(side="left")
            ttk.Combobox(f, textvariable=mv, values=["RAID 5", "RAID 6", "JBOD"], width=10, state="readonly").pack(side="left", padx=5)
            self.manual_slots.append((nv, mv, cb))
        btn_m = ttk.Frame(self.tabs[2]); btn_m.pack(pady=5)
        ttk.Button(btn_m, text="CALCULATE MANUAL", command=lambda: self.run_logic(False)).pack(side="left", padx=5)
        ttk.Button(btn_m, text="EXPORT", command=self.export_to_file).pack(side="left")
        self.man_txt = tk.Text(self.tabs[2], font=("Consolas", 10), bg="#f4f4f4"); self.man_txt.pack(fill="both", expand=True)
        
        # TAB 5: NVRs
        self.nvr_canvas = tk.Canvas(self.tabs[4]); self.nvr_canvas.pack(side="left", fill="both", expand=True)
        self.nvr_scroll = ttk.Scrollbar(self.tabs[4], orient="vertical", command=self.nvr_canvas.yview)
        self.nvr_scroll.pack(side="right", fill="y")
        self.nvr_frame = ttk.Frame(self.nvr_canvas)
        self.nvr_canvas.create_window((0,0), window=self.nvr_frame, anchor="nw")
        self.nvr_frame.bind("<Configure>", lambda e: self.nvr_canvas.configure(scrollregion=self.nvr_canvas.bbox("all")))
        self.nvr_canvas.configure(yscrollcommand=self.nvr_scroll.set)

        # TAB 6: ADD NVR
        fn = ttk.Frame(self.tabs[5], padding=20); fn.pack()
        self.nf = {}
        fields = [("Model Name", "Name"), ("Model SKU", "SKU"), ("Channels", "CH"), ("Mbps Limit", "MB"), ("HDD Slots", "Slots"), ("Unit Price", "Price")]
        for i, (lab, key) in enumerate(fields):
            ttk.Label(fn, text=lab).grid(row=i, column=0, sticky="w"); e = ttk.Entry(fn); e.grid(row=i, column=1); self.nf[key] = e
        self.na = tk.StringVar(value="RAID"); ttk.Combobox(fn, textvariable=self.na, values=["RAID", "JBOD"], state="readonly").grid(row=6, column=1)
        ttk.Button(fn, text="ADD TO DATABASE", command=self.add_new_nvr).grid(row=7, columnspan=2, pady=10)

        self.refresh_nvr_dropdowns(); self.setup_hdds(); self.refresh_nvr_list_tab()

    def save_camera(self):
        v = [self.ents[k].get() for k in ["Name", "Qty", "Mbps", "GB"]]
        if all(v): 
            for item in self.tree.get_children():
                if str(self.tree.item(item)['values'][0]) == v[0]: self.tree.delete(item)
            self.tree.insert("", "end", values=v)

    def delete_camera(self): 
        for s in self.tree.selection(): self.tree.delete(s)

    def export_to_file(self):
        idx = self.nb.index("current")
        content = self.res_txt.get("1.0", tk.END) if idx == 1 else self.man_txt.get("1.0", tk.END)
        if len(content) < 50: messagebox.showwarning("Warning", "No report to export!"); return
        f = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"CCTV_Design_{datetime.now().strftime('%Y%m%d')}.txt")
        if f: 
            with open(f, "w") as file: file.write(content)
            messagebox.showinfo("Success", "Report saved.")

    def add_new_nvr(self):
        try:
            row = [self.nf["Name"].get(), self.nf["SKU"].get(), int(self.nf["CH"].get()), int(self.nf["MB"].get()), int(self.nf["Slots"].get()), float(self.nf["Price"].get()), self.na.get()]
            self.nvr_list.append(row); self.save_all_data(); self.refresh_nvr_dropdowns(); self.refresh_nvr_list_tab()
        except: messagebox.showerror("Error", "Check fields.")

    def refresh_nvr_list_tab(self):
        for w in self.nvr_frame.winfo_children(): w.destroy()
        self.nvr_price_entries = []
        for i, n in enumerate(self.nvr_list):
            ttk.Label(self.nvr_frame, text=f"{n[0]} ({n[1]})", width=40).grid(row=i, column=0, pady=2, sticky="w")
            e = ttk.Entry(self.nvr_frame, width=15); e.insert(0, f"{n[5]:.2f}"); e.grid(row=i, column=1, padx=5)
            self.nvr_price_entries.append(e)
            ttk.Button(self.nvr_frame, text="DEL", width=5, command=lambda idx=i: self.delete_nvr(idx)).grid(row=i, column=2)
        ttk.Button(self.nvr_frame, text="SAVE UPDATES", command=self.save_nvr_prices).grid(row=len(self.nvr_list), columnspan=3, pady=20)

    def save_nvr_prices(self):
        for i, e in enumerate(self.nvr_price_entries): self.nvr_list[i][5] = float(e.get())
        self.save_all_data(); messagebox.showinfo("Saved", "Prices Updated.")

    def delete_nvr(self, idx):
        self.nvr_list.pop(idx); self.save_all_data(); self.refresh_nvr_dropdowns(); self.refresh_nvr_list_tab()

    def setup_hdds(self):
        for w in self.tabs[3].winfo_children(): w.destroy()
        fh = ttk.Frame(self.tabs[3], padding=20); fh.pack()
        self.hdd_ents = {}
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2); ttk.Label(fh, text=f"{cap}TB: $").grid(row=r, column=c*2)
            e = ttk.Entry(fh, width=10); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1); self.hdd_ents[cap] = e
        ttk.Button(self.tabs[3], text="SAVE HDDS", command=self.save_hdds).pack()

    def save_hdds(self):
        for c, e in self.hdd_ents.items(): self.hdd_prices[c] = float(e.get())
        self.save_all_data(); messagebox.showinfo("Saved", "HDD Prices Updated.")

    def refresh_nvr_dropdowns(self):
        names = ["None"] + [f"{n[1]} ({n[2]} Ch)" for n in self.nvr_list]
        for _, _, cb in self.manual_slots: cb['values'] = names

    def generate_detailed_report(self, cfg, title):
        buf = self.storage_buffer.get()
        report = f"{'='*80}\n{title} DESIGN REPORT (Buffer: {buf}%)\n{'='*80}\n"
        report += f"SYSTEM TOTAL: ${cfg['total']:,.2f}\n\n"
        for i, u in enumerate(cfg['units']):
            report += f"UNIT #{i+1}: {u['m'][0]} ({u['m'][1]})\n{'-'*40}\n"
            report += f"  Mode: {u['mode']} | Load: {(u['mb']/u['m'][3])*100:.1f}%\n"
            report += f"  Cameras: {u['c_total']} ({', '.join([f'{k}:{v}' for k,v in u['cam_breakdown'].items() if v>0])})\n"
            report += f"  Storage: {u['h']['qty']}x{u['h']['cap']}TB ({u['h']['total_tb']:.1f}TB Usable)\n"
            report += f"  Subtotal: ${ (u['m'][5] + u['h']['cost']):,.2f}\n\n"
        self.last_report = report
        return report

    def calculate_engine(self, cams, hw_c, split_ratio=1.0, even=False):
        """Universal engine used by both Auto and Manual to find best HDD fit"""
        u_list, cur_c = [], [dict(c) for c in cams]
        num = len(hw_c)
        try: buf_mult = 1 + (float(self.storage_buffer.get()) / 100)
        except: buf_mult = 1.0

        for i in range(num):
            u_brk, u_mb, u_tb, u_c = {}, 0, 0, 0
            for c in cur_c:
                take = math.ceil(c['qty']/(num-i)) if even else math.floor(c['qty']*split_ratio) if i<num-1 else c['qty']
                take = min(c['qty'], take)
                # Ensure we don't exceed NVR channel limit
                take = min(take, hw_c[i]['m'][2] - u_c)
                
                u_brk[c['name']] = take; u_mb += take*c['mbps']; u_tb += take*c['tb']; u_c += take
                c['qty'] -= take
            
            u_tb_buffered = u_tb * buf_mult
            p = 0 if hw_c[i]['m'][6]=="JBOD" else (1 if hw_c[i]['mode']=="RAID 5" else 2 if hw_c[i]['mode']=="RAID 6" else 0)
            hc, hd = get_best_hdd(u_tb_buffered, hw_c[i]['m'][4], p, self.hdd_prices)
            
            if not hd and u_tb_buffered > 0.01: return None
            if u_mb > hw_c[i]['m'][3]: return None
            
            u_list.append({"m": hw_c[i]['m'], "c_total": u_c, "cam_breakdown": u_brk, "mb": u_mb, "tb": u_tb, "h": hd or {"qty":0, "cap":0, "cost":0, "total_tb":0}, "mode": "JBOD" if p==0 else hw_c[i]['mode']})
        
        if sum(c['qty'] for c in cur_c) > 0: return None
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
            pool = [n for n in self.nvr_list if n[6] == ("JBOD" if mode=="JBOD" else "RAID") and "Holis" not in n[0]]
            for n_u in range(1, 7):
                for combo in itertools.combinations_with_replacement(pool, n_u):
                    hw_c = [{"m": n, "mode": mode} for n in combo]
                    # Check splits to find cheapest
                    for r in [1.0] + [x/10.0 for x in range(1, 10)]:
                        res = self.calculate_engine(cams, hw_c, r, (r==1.0))
                        if res:
                            cost = sum(x['m'][5] + x['h']['cost'] for x in res)
                            if cost < best_cost: best_cost, best_cfg = cost, {"total": cost, "units": res}
        else:
            active_hw = []
            for nv, mv, _ in self.manual_slots:
                val = nv.get()
                if val != "None":
                    clean_sku = val.split(" (")[0]
                    match = next((n for n in self.nvr_list if n[1] == clean_sku), None)
                    if match: active_hw.append({"m": match, "mode": mv.get()})

            if active_hw:
                # Manual mode now uses the exact same split-search logic as Auto
                for r in [1.0] + [x/100.0 for x in range(1, 100)]:
                    res = self.calculate_engine(cams, active_hw, r, (r==1.0))
                    if res:
                        cost = sum(x['m'][5] + x['h']['cost'] for x in res)
                        if cost < best_cost: 
                            best_cost, best_cfg = cost, {"total": cost, "units": res}

        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if best_cfg: txt.insert("1.0", self.generate_detailed_report(best_cfg, "AUTO" if auto else "MANUAL"))
        else: txt.insert("1.0", "ERROR: Hardware limits exceeded (Check Channel Count or Bandwidth).")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("1100x950"); app = CCTVApp(root); root.mainloop()
