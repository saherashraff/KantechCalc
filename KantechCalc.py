import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import itertools
import json
import os
from datetime import datetime

DATA_FILE = "system_data.json"

# ... [Keep DEFAULT_HDD_PRICES and DEFAULT_NVR_DATA the same] ...

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
        self.root.title("CCTV MASTER V36.0 - PROFESSIONAL")
        self.load_all_data()
        self.setup_ui()
        # Storage for the last calculated result to enable exporting
        self.current_report_data = ""

    # ... [Keep load_all_data, save_all_data, save_camera, etc. the same] ...

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.tabs = [ttk.Frame(self.nb) for _ in range(6)]
        titles = ["1. Cameras", "2. Auto", "3. Manual", "4. HDDs", "5. NVRs", "6. Add NVR"]
        for tab, title in zip(self.tabs, titles): self.nb.add(tab, text=title)

        # TAB 1: CAMERAS (Simplified for space)
        # [Insert your existing Tab 1 code here]

        # TAB 2: AUTO
        self.auto_mode = tk.StringVar(value="RAID 5")
        self.storage_buffer = tk.StringVar(value="0")
        f_a = ttk.Frame(self.tabs[1], padding=10); f_a.pack(fill="x")
        ttk.Combobox(f_a, textvariable=self.auto_mode, values=["RAID 5", "RAID 6", "JBOD"], state="readonly", width=10).pack(side="left")
        ttk.Button(f_a, text="RUN AUTO", command=lambda: self.run_logic(True)).pack(side="left", padx=5)
        ttk.Button(f_a, text="EXPORT TO TXT", command=self.export_report).pack(side="left", padx=5)
        self.res_txt = tk.Text(self.tabs[1], font=("Consolas", 10)); self.res_txt.pack(fill="both", expand=True)

        # TAB 3: MANUAL
        f_m_top = ttk.Frame(self.tabs[2], padding=5); f_m_top.pack(fill="x")
        ttk.Button(f_m_top, text="CALC MANUAL (99% SWEEP)", command=lambda: self.run_logic(False)).pack(side="left")
        ttk.Button(f_m_top, text="EXPORT TO TXT", command=self.export_report).pack(side="left", padx=5)
        self.manual_slots = []
        for i in range(8):
            f = ttk.Frame(self.tabs[2], padding=2); f.pack(fill="x")
            nv, mv = tk.StringVar(value="None"), tk.StringVar(value="RAID 5")
            cb = ttk.Combobox(f, textvariable=nv, width=45, state="readonly"); cb.pack(side="left")
            ttk.Combobox(f, textvariable=mv, values=["RAID 5", "RAID 6", "JBOD"], width=10, state="readonly").pack(side="left", padx=5)
            self.manual_slots.append((nv, mv, cb))
        self.man_txt = tk.Text(self.tabs[2], font=("Consolas", 10), bg="#f4f4f4"); self.man_txt.pack(fill="both", expand=True)

        # [Initialize other tabs as per your original code]

    def generate_detailed_report(self, cfg, title):
        buf = self.storage_buffer.get()
        report = f"{'='*80}\n{title} DESIGN REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{'='*80}\n"
        report += f"SYSTEM TOTAL COST: ${cfg['total']:,.2f}\n"
        report += f"STORAGE BUFFER:    {buf}%\n"
        report += f"TOTAL UNITS:       {len(cfg['units'])}\n\n"

        for i, u in enumerate(cfg['units']):
            report += f"UNIT #{i+1}: {u['m'][0]} ({u['m'][1]})\n"
            report += f"{'-'*40}\n"
            report += f"  Hardware Specs:  {u['m'][2]} Ch | {u['m'][3]} Mbps Limit\n"
            report += f"  Configuration:   {u['mode']} | Load: {(u['mb']/u['m'][3])*100:.1f}%\n"
            
            # --- DETAILED CAMERA ASSIGNMENT ---
            report += f"  Camera Load:     {u['c_total']} Total\n"
            for cam_name, qty in u['cam_breakdown'].items():
                if qty > 0:
                    report += f"    > {cam_name}: {qty} units\n"
            
            report += f"  Storage Array:   {u['h']['qty']} x {u['h']['cap']}TB ({u['h']['total_tb']:.1f}TB Usable)\n"
            report += f"  Unit Cost:       ${ (u['m'][5] + u['h']['cost']):,.2f}\n\n"
        
        self.current_report_data = report
        return report

    def export_report(self):
        if not self.current_report_data:
            messagebox.showwarning("Export", "Please run a calculation first!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export CCTV Design Report"
        )
        
        if file_path:
            try:
                with open(file_path, "w") as f:
                    f.write(self.current_report_data)
                messagebox.showinfo("Success", f"Report saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")

    # ... [Keep run_logic and calc_sub_engine the same] ...
