import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import json
import os


@dataclass
class DCDevice:
    """Represents devices on a single DC line"""
    dc_number: int
    smart_card: int = 0
    smart_card_reader: int = 0  
    fingerprint: int = 0  # Biometric
    door_sensor: int = 0
    magnetic_lock: int = 0
    electric_lock: int = 0
    rex_button: int = 0
    push_button: int = 0
    break_glass: int = 0
    buzzer: int = 0
    double_door_lock: int = 0  
    ddl_sensors: int = 0
    unmonitored_single_magnetic_lock: int = 0  
    unmonitored_double_magnetic_lock: int = 0  
    
    def calculate_totals(self):
        """Calculate readers, inputs, outputs for this DC line"""
        # Normal Readers = Card Reader + Biometric Reader
        # Smart Card Readers use independent specialized slots
        readers = self.smart_card + self.fingerprint + self.smart_card_reader
        
        inputs = (self.door_sensor + self.rex_button + self.push_button + 
                 self.break_glass + self.magnetic_lock + 
                 self.ddl_sensors + self.double_door_lock)
        
        outputs = (self.magnetic_lock + self.electric_lock + self.double_door_lock +
                  self.unmonitored_single_magnetic_lock + 
                  self.unmonitored_double_magnetic_lock +
                  self.buzzer)
        
        return {
            'readers': readers,
            'inputs': inputs,
            'outputs': outputs,
            'smart_cards': self.smart_card,
            'smart_card_readers': self.smart_card_reader,
            'fingerprints': self.fingerprint
        }
    
    def add_configuration(self, other_config):
        """Add another configuration to this DC line"""
        self.smart_card += other_config.smart_card
        self.smart_card_reader += other_config.smart_card_reader
        self.fingerprint += other_config.fingerprint
        self.door_sensor += other_config.door_sensor
        self.magnetic_lock += other_config.magnetic_lock
        self.electric_lock += other_config.electric_lock
        self.rex_button += other_config.rex_button
        self.push_button += other_config.push_button
        self.break_glass += other_config.break_glass
        self.buzzer += other_config.buzzer
        self.double_door_lock += other_config.double_door_lock
        self.ddl_sensors += other_config.ddl_sensors
        self.unmonitored_single_magnetic_lock += other_config.unmonitored_single_magnetic_lock
        self.unmonitored_double_magnetic_lock += other_config.unmonitored_double_magnetic_lock


class AccessDoorType:
    """Represents an Access Door Type configuration"""
    def __init__(self, type_id: int, name: str):
        self.type_id = type_id
        self.name = name
        self.config = DCDevice(dc_number=type_id)
    
    def update_config(self, **kwargs):
        """Update the configuration of this door type"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def get_totals(self):
        """Get totals for this door type"""
        return self.config.calculate_totals()
    
    def __str__(self):
        totals = self.get_totals()
        return f"Door Type {self.type_id} ({self.name}): {totals['readers']} readers, {totals['inputs']} inputs, {totals['outputs']} outputs"


class GSTARController:
    def __init__(self, name, readers, inputs, outputs, price, number_of_acm):
        self.name = name
        self.readers = readers
        self.inputs = inputs
        self.outputs = outputs
        self.price = price
        self.number_of_acm = number_of_acm
    
    def can_handle_readers(self, required_readers):
        return self.readers >= required_readers


class SWHControllerCalculator:
    def __init__(self):
        self.gstar_controllers = [
            GSTARController("GSTAR004 (4 readers)", 4, 8, 4, 1395, 0),
            GSTARController("GSTAR004 (8 readers)", 8, 16, 12, 2123, 0),
            GSTARController("GSTAR008", 8, 24, 8, 3125, 1),
            GSTARController("GSTAR016", 16, 48, 16, 4166, 2),
            GSTARController("GSTAR016 (24 readers)", 24, 72, 24, 5166, 3),
            GSTARController("GSTAR016 (32 readers)", 32, 96, 32, 6166, 4)
        ]
        
        self.swh_licenses = [
            {"name": "CC9000-SL", "max_readers": 16, "cost": 0},
            {"name": "CC9000-SM", "max_readers": 32, "cost": 0},
            {"name": "CC9000-SN", "max_readers": 64, "cost": 0},
            {"name": "CC9000-SP", "max_readers": 128, "cost": 0},
            {"name": "CC9000-SQ", "max_readers": 256, "cost": 0},
            {"name": "CC9000-SR", "max_readers": 512, "cost": 0},
            {"name": "CC9000-SRP", "max_readers": 1000, "cost": 0},
            {"name": "CC9000-SS", "max_readers": 2500, "cost": 0},
            {"name": "CC9000-SSP", "max_readers": 3500, "cost": 0},
            {"name": "CC9000-ST", "max_readers": 5000, "cost": 0}
        ]
        
    def select_controller_for_readers(self, required_readers):
        suitable_controllers = [c for c in self.gstar_controllers if c.can_handle_readers(required_readers)]
        if not suitable_controllers:
            return None
        suitable_controllers.sort(key=lambda x: x.price)
        return suitable_controllers[0]
    
    def calculate_expansion_for_swh(self, dc_inputs: int, dc_outputs: int, controller_inputs: int, controller_outputs: int) -> Dict:
        input_shortage = max(0, dc_inputs - controller_inputs)
        output_shortage = max(0, dc_outputs - controller_outputs)
        
        result = f"\nI/O Analysis:\n"
        result += f"  Required: {dc_inputs} inputs, {dc_outputs} outputs\n"
        result += f"  Controller provides: {controller_inputs} inputs, {controller_outputs} outputs\n"
        result += f"  Shortage: {input_shortage} inputs, {output_shortage} outputs\n"
        
        if input_shortage == 0 and output_shortage == 0:
            result += "  ✅ No expansion modules needed\n"
            return {'modules': [], 'cost': 0, 'result': result}
        
        expansion_modules = []
        expansion_cost = 0
        
        if input_shortage > 0:
            as0073_needed = int(np.ceil(input_shortage / 8))
            expansion_modules.append(f"AS0073-000 (x{as0073_needed})")
            expansion_cost += 333 * as0073_needed
        
        if output_shortage > 0:
            as0074_needed = int(np.ceil(output_shortage / 8))
            expansion_modules.append(f"AS0074-000 (x{as0074_needed})")
            expansion_cost += 395 * as0074_needed
        
        result += f"  Expansion solution: {expansion_modules}\n"
        result += f"  Expansion cost: ${expansion_cost}\n"
        
        return {'modules': expansion_modules, 'cost': expansion_cost, 'result': result}


class KantechDCCalculatorGUI:
    def __init__(self):
        self.dc_lines: List[DCDevice] = []
        self.access_door_types: List[AccessDoorType] = []
        self.swh_calculator = SWHControllerCalculator()
        
        self.controllers = [
            {'name': 'kt-1', 'readers': 1, 'smart_card_readers': 1, 'cost': 450, 'inputs': 4, 'outputs': 2},
            {'name': 'kt-2', 'readers': 2, 'smart_card_readers': 2, 'cost': 750, 'inputs': 8, 'outputs': 2},
            {'name': 'kt-4', 'readers': 4, 'smart_card_readers': 4, 'cost': 2395, 'inputs': 16, 'outputs': 4}
        ]
        
        self.expansion_modules = [
            {'name': 'inout16 (16/0)', 'inputs': 16, 'outputs': 0, 'cost': 447},
            {'name': 'inout16 (12/4)', 'inputs': 12, 'outputs': 4, 'cost': 447},
            {'name': 'inout16 (8/8)', 'inputs': 8, 'outputs': 8, 'cost': 447},
            {'name': 'inout16 (4/12)', 'inputs': 4, 'outputs': 12, 'cost': 447},
            {'name': 'inout16 (0/16)', 'inputs': 0, 'outputs': 16, 'cost': 447},
            {'name': 'in16', 'inputs': 16, 'outputs': 0, 'cost': 470},
            {'name': 'r8', 'inputs': 0, 'outputs': 8, 'cost': 470}
        ]
        
        self.license_info = {
            'special': {'name': 'Kantech Special License', 'max_controllers': 32, 'cost': 0},
            'corporate': {'name': 'Kantech Corporate License', 'min_controllers': 33, 'cost': 0},
            'global': {'name': 'Global License', 'cost': 0},
            'gateway': {'name': 'Gateway License', 'cost': 500},
            'redundancy': {'name': 'Redundancy License', 'cost': 750}
        }
        
        self.kantech_all_results = None
        self.kantech_grand_total = 0
        self.gstar_results = None
        
        self.root = tk.Tk()
        self.root.title("Access Control System Calculator")
        self.root.geometry("1200x800")
        
        self.selected_dc_line_var = tk.StringVar()
        self.selected_door_type_var = tk.StringVar()
        self.redundancy_var = tk.BooleanVar(value=False)
        
        self.setup_styles()
        self.create_ui()
        
    def setup_styles(self):
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        
    def create_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_main_tab()
        self.create_dc_lines_tab()
        self.create_door_types_tab()
        self.create_calculation_tab()
        self.create_license_tab()
        self.create_export_tab()
        
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_main_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Main")
        
        ttk.Label(tab, text="ACCESS CONTROL SYSTEM CALCULATOR", style='Title.TLabel').pack(pady=20)
        
        info_frame = ttk.LabelFrame(tab, text="System Information", padding=10)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        self.system_info_text = tk.Text(info_frame, height=8, width=80, state=tk.DISABLED)
        self.system_info_text.pack(fill=tk.BOTH, expand=True)
        
        actions_frame = ttk.LabelFrame(tab, text="Quick Actions", padding=10)
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Button(actions_frame, text="Add DC Line", command=lambda: self.notebook.select(1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Manage Door Types", command=lambda: self.notebook.select(2)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Calculate Kantech", command=lambda: self.notebook.select(3)).pack(side=tk.LEFT, padx=5)
        
        overview_frame = ttk.LabelFrame(tab, text="System Overview", padding=10)
        overview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.overview_text = scrolledtext.ScrolledText(overview_frame, height=15, state=tk.DISABLED)
        self.overview_text.pack(fill=tk.BOTH, expand=True)
    
    def create_dc_lines_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="DC Lines")
        
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(top_frame, text="DC Line Management", style='Title.TLabel').pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Add DC Line", command=self.show_add_dc_line_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_dc_line).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected_dc_line).pack(side=tk.LEFT, padx=5)
        
        list_frame = ttk.LabelFrame(tab, text="DC Lines List", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('DC', 'Card Reader', 'Smart Card Reader', 'Biometric', 'Door Sensor', 'Mag Lock', 'Elec Lock', 
                  'REX', 'Push Button', 'Break Glass', 'Buzzer', 'DDL', 'DDL Sensors',
                  'Unmon Single', 'Unmon Double', 'Readers', 'Inputs', 'Outputs')
        
        self.dc_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        for col in columns:
            self.dc_tree.heading(col, text=col)
            self.dc_tree.column(col, width=70, minwidth=40)
            
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.dc_tree.yview)
        self.dc_tree.configure(yscrollcommand=scrollbar.set)
        self.dc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_door_types_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Door Types")
        
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(top_frame, text="Access Door Types Management", style='Title.TLabel').pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Add Door Type", command=self.show_add_door_type_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_door_type).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected_door_type).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Apply to DC Line", command=self.apply_door_type_to_dc).pack(side=tk.LEFT, padx=5)
        
        list_frame = ttk.LabelFrame(tab, text="Door Types List", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('ID', 'Name', 'Card Reader', 'Smart Card Reader', 'Biometric', 'Door Sensor', 'Readers', 'Inputs', 'Outputs')
        self.door_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        for col in columns:
            self.door_tree.heading(col, text=col)
            self.door_tree.column(col, width=100, minwidth=50)
            
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.door_tree.yview)
        self.door_tree.configure(yscrollcommand=scrollbar.set)
        self.door_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_calculation_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Calculations")
        
        calc_notebook = ttk.Notebook(tab)
        calc_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        kantech_calc_tab = ttk.Frame(calc_notebook)
        calc_notebook.add(kantech_calc_tab, text="Kantech System")
        
        swh_calc_tab = ttk.Frame(calc_notebook)
        calc_notebook.add(swh_calc_tab, text="SWH/GSTAR System")
        
        self.create_kantech_calculation_frame(kantech_calc_tab)
        self.create_swh_calculation_frame(swh_calc_tab)
        
    def create_kantech_calculation_frame(self, parent):
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(top_frame, text="Kantech System Calculation", style='Title.TLabel').pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Calculate All DC Lines", command=self.calculate_all_kantech).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Calculate Selected", command=self.calculate_selected_kantech).pack(side=tk.LEFT, padx=5)
        
        select_frame = ttk.LabelFrame(parent, text="Select DC Line", padding=10)
        select_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(select_frame, text="DC Line:").pack(side=tk.LEFT, padx=5)
        self.dc_line_combo = ttk.Combobox(select_frame, textvariable=self.selected_dc_line_var, state='readonly', width=20)
        self.dc_line_combo.pack(side=tk.LEFT, padx=5)
        
        results_frame = ttk.LabelFrame(parent, text="Calculation Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.kantech_results_text = scrolledtext.ScrolledText(results_frame, height=20)
        self.kantech_results_text.pack(fill=tk.BOTH, expand=True)
        
    def create_swh_calculation_frame(self, parent):
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(top_frame, text="SWH/GSTAR System Calculation", style='Title.TLabel').pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Calculate All DC Lines", command=self.calculate_all_gstar).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Calculate Selected", command=self.calculate_selected_gstar).pack(side=tk.LEFT, padx=5)
        
        select_frame = ttk.LabelFrame(parent, text="Select DC Line", padding=10)
        select_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(select_frame, text="DC Line:").pack(side=tk.LEFT, padx=5)
        self.swh_dc_line_combo = ttk.Combobox(select_frame, textvariable=self.selected_dc_line_var, state='readonly', width=20)
        self.swh_dc_line_combo.pack(side=tk.LEFT, padx=5)
        
        results_frame = ttk.LabelFrame(parent, text="Calculation Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.swh_results_text = scrolledtext.ScrolledText(results_frame, height=20)
        self.swh_results_text.pack(fill=tk.BOTH, expand=True)

    def create_license_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Licenses")
        
        redundancy_frame = ttk.LabelFrame(tab, text="System Configuration", padding=10)
        redundancy_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Checkbutton(redundancy_frame, text="Use Redundancy Configuration", variable=self.redundancy_var).pack(anchor=tk.W)
        
        ttk.Button(tab, text="Calculate Kantech License Requirements", command=self.calculate_kantech_license).pack(pady=10)
        
        results_frame = ttk.LabelFrame(tab, text="License Layer Overhead Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.kantech_license_results_text = scrolledtext.ScrolledText(results_frame, height=20)
        self.kantech_license_results_text.pack(fill=tk.BOTH, expand=True)
        
    def create_export_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Export")
        ttk.Label(tab, text="Export Results", style='Title.TLabel').pack(pady=20)
        options_frame = ttk.LabelFrame(tab, text="Export Options", padding=20)
        options_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        ttk.Button(options_frame, text="Export Kantech Results to CSV", command=self.export_kantech_results).pack(pady=10, fill=tk.X)
        self.export_status = ttk.Label(tab, text="")
        self.export_status.pack(pady=10)

    def update_system_info(self):
        self.system_info_text.config(state=tk.NORMAL)
        self.system_info_text.delete(1.0, tk.END)
        info = f"Current System Status:\n• DC Lines: {len(self.dc_lines)}\n• Access Door Types: {len(self.access_door_types)}\n"
        if self.dc_lines:
            total_readers = sum(dc.calculate_totals()['readers'] for dc in self.dc_lines)
            total_inputs = sum(dc.calculate_totals()['inputs'] for dc in self.dc_lines)
            total_outputs = sum(dc.calculate_totals()['outputs'] for dc in self.dc_lines)
            info += f"\nTotal Requirements:\n• Readers: {total_readers}\n• Inputs: {total_inputs}\n• Outputs: {total_outputs}\n"
        self.system_info_text.insert(1.0, info)
        self.system_info_text.config(state=tk.DISABLED)
        
    def update_overview(self):
        self.overview_text.config(state=tk.NORMAL)
        self.overview_text.delete(1.0, tk.END)
        overview = "SYSTEM OVERVIEW\n" + "=" * 50 + "\n\nDC LINES:\n"
        if self.dc_lines:
            for dc in self.dc_lines:
                totals = dc.calculate_totals()
                overview += f"DC Line {dc.dc_number}: {totals['readers']} readers, {totals['inputs']} inputs, {totals['outputs']} outputs\n"
        else:
            overview += "No DC lines configured\n"
        self.overview_text.insert(1.0, overview)
        self.overview_text.config(state=tk.DISABLED)
        
    def update_dc_lines_list(self):
        for item in self.dc_tree.get_children():
            self.dc_tree.delete(item)
        for dc in self.dc_lines:
            totals = dc.calculate_totals()
            values = (dc.dc_number, dc.smart_card, dc.smart_card_reader, dc.fingerprint, dc.door_sensor, dc.magnetic_lock,
                      dc.electric_lock, dc.rex_button, dc.push_button, dc.break_glass, dc.buzzer, dc.double_door_lock,
                      dc.ddl_sensors, dc.unmonitored_single_magnetic_lock, dc.unmonitored_double_magnetic_lock,
                      totals['readers'], totals['inputs'], totals['outputs'])
            self.dc_tree.insert('', tk.END, values=values)
            
        dc_line_options = [f"DC Line {dc.dc_number}" for dc in self.dc_lines]
        self.dc_line_combo['values'] = dc_line_options
        self.swh_dc_line_combo['values'] = dc_line_options
        if dc_line_options:
            self.selected_dc_line_var.set(dc_line_options[0])
        self.update_system_info()
        self.update_overview()
        
    def update_door_types_list(self):
        for item in self.door_tree.get_children():
            self.door_tree.delete(item)
        for dt in self.access_door_types:
            totals = dt.get_totals()
            values = (dt.type_id, dt.name, dt.config.smart_card, dt.config.smart_card_reader, dt.config.fingerprint,
                      dt.config.door_sensor, totals['readers'], totals['inputs'], totals['outputs'])
            self.door_tree.insert('', tk.END, values=values)

    def show_add_dc_line_dialog(self):
        self._show_dc_device_dialog("Add DC Line", None)

    def edit_selected_dc_line(self):
        selected = self.dc_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a DC line to edit")
            return
        item_values = self.dc_tree.item(selected[0])['values']
        dc_num = int(item_values[0])
        dc_device = next((x for x in self.dc_lines if x.dc_number == dc_num), None)
        if dc_device:
            self._show_dc_device_dialog("Edit DC Line", dc_device)

    def delete_selected_dc_line(self):
        selected = self.dc_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a DC line to delete")
            return
        item_values = self.dc_tree.item(selected[0])['values']
        dc_num = int(item_values[0])
        self.dc_lines = [x for x in self.dc_lines if x.dc_number != dc_num]
        self.update_dc_lines_list()

    def show_add_door_type_dialog(self):
        self._show_door_type_dialog("Add Door Type", None)

    def edit_selected_door_type(self):
        selected = self.door_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a Door Type to edit")
            return
        item_values = self.door_tree.item(selected[0])['values']
        dt_id = int(item_values[0])
        dt = next((x for x in self.access_door_types if x.type_id == dt_id), None)
        if dt:
            self._show_door_type_dialog("Edit Door Type", dt)

    def delete_selected_door_type(self):
        selected = self.door_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a Door Type to delete")
            return
        item_values = self.door_tree.item(selected[0])['values']
        dt_id = int(item_values[0])
        self.access_door_types = [x for x in self.access_door_types if x.type_id != dt_id]
        self.update_door_types_list()

    def apply_door_type_to_dc(self):
        selected_dc = self.dc_tree.selection()
        selected_door = self.door_tree.selection()
        if not selected_dc or not selected_door:
            messagebox.showwarning("Warning", "Please select both a DC line and a Door Type")
            return
        dc_num = int(self.dc_tree.item(selected_dc[0])['values'][0])
        dt_id = int(self.door_tree.item(selected_door[0])['values'][0])
        dc_device = next((x for x in self.dc_lines if x.dc_number == dc_num), None)
        dt = next((x for x in self.access_door_types if x.type_id == dt_id), None)
        if dc_device and dt:
            dc_device.add_configuration(dt.config)
            self.update_dc_lines_list()

    def _show_dc_device_dialog(self, title: str, device: Optional[DCDevice]):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("450x600")
        win.grab_set()

        # Combine Door Type Dropdown Frame
        dt_frame = ttk.Frame(win)
        dt_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='ew')
        ttk.Label(dt_frame, text="Combine Door Type:").pack(side=tk.LEFT, padx=5)
        
        door_type_options = ["None"] + [f"{dt.type_id}: {dt.name}" for dt in self.access_door_types]
        dt_combo = ttk.Combobox(dt_frame, values=door_type_options, state='readonly', width=30)
        dt_combo.set("None")
        dt_combo.pack(side=tk.LEFT, padx=5)

        fields = [
            ('dc_number', 'DC Line Number'), ('smart_card', 'Smart Card'),
            ('smart_card_reader', 'Smart Card Reader'), ('fingerprint', 'Biometric'),
            ('door_sensor', 'Door Sensor'), ('magnetic_lock', 'Magnetic Lock'),
            ('electric_lock', 'Electric Lock'), ('rex_button', 'REX Button'),
            ('push_button', 'Push Button'), ('break_glass', 'Break Glass'),
            ('buzzer', 'Buzzer'), ('double_door_lock', 'Double Door Lock'),
            ('ddl_sensors', 'DDL Sensors'), ('unmonitored_single_magnetic_lock', 'Unmon Single Mag Lock'),
            ('unmonitored_double_magnetic_lock', 'Unmon Double Mag Lock')
        ]

        entries = {}
        for idx, (field, name) in enumerate(fields):
            lbl = ttk.Label(win, text=name)
            lbl.grid(row=idx+1, column=0, padx=10, pady=4, sticky='w')
            ent = ttk.Entry(win)
            ent.grid(row=idx+1, column=1, padx=10, pady=4, sticky='ew')
            
            val = getattr(device, field) if device else 0
            ent.insert(0, str(val))
            if field == 'dc_number' and device:
                ent.config(state='disabled')
            entries[field] = ent

        def on_door_type_selected(event):
            sel = dt_combo.get()
            if sel != "None":
                dt_id = int(sel.split(":")[0])
                selected_dt = next((x for x in self.access_door_types if x.type_id == dt_id), None)
                if selected_dt:
                    for field, _ in fields:
                        if field != 'dc_number':
                            try:
                                current_val = int(entries[field].get())
                            except ValueError:
                                current_val = 0
                                
                            dt_val = getattr(selected_dt.config, field)
                            # Combine/Add the values together
                            entries[field].delete(0, tk.END)
                            entries[field].insert(0, str(current_val + dt_val))

        dt_combo.bind("<<ComboboxSelected>>", on_door_type_selected)

        def save():
            try:
                data = {f: int(entries[f].get()) for f, _ in fields}
                if device:
                    for f, _ in fields:
                        setattr(device, f, data[f])
                else:
                    if any(x.dc_number == data['dc_number'] for x in self.dc_lines):
                        messagebox.showerror("Error", "DC line number already exists")
                        return
                    self.dc_lines.append(DCDevice(**data))
                self.update_dc_lines_list()
                win.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid integers.")

        btn = ttk.Button(win, text="Save", command=save)
        btn.grid(row=len(fields)+1, column=0, columnspan=2, pady=15)

    def _show_door_type_dialog(self, title: str, dt: Optional[AccessDoorType]):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("400x550")
        win.grab_set()

        lbl1 = ttk.Label(win, text="Door Type ID")
        lbl1.grid(row=0, column=0, padx=10, pady=5, sticky='w')
        ent_id = ttk.Entry(win)
        ent_id.grid(row=0, column=1, padx=10, pady=5, sticky='ew')
        if dt:
            ent_id.insert(0, str(dt.type_id))
            ent_id.config(state='disabled')
        else:
            ent_id.insert(0, "1")

        lbl2 = ttk.Label(win, text="Door Type Name")
        lbl2.grid(row=1, column=0, padx=10, pady=5, sticky='w')
        ent_name = ttk.Entry(win)
        ent_name.grid(row=1, column=1, padx=10, pady=5, sticky='ew')
        if dt:
            ent_name.insert(0, dt.name)

        fields = [
            ('smart_card', 'Smart Card'), ('smart_card_reader', 'Smart Card Reader'),
            ('fingerprint', 'Biometric'), ('door_sensor', 'Door Sensor'),
            ('magnetic_lock', 'Magnetic Lock'), ('electric_lock', 'Electric Lock'),
            ('rex_button', 'REX Button'), ('push_button', 'Push Button'),
            ('break_glass', 'Break Glass'), ('buzzer', 'Buzzer'),
            ('double_door_lock', 'Double Door Lock'), ('ddl_sensors', 'DDL Sensors'),
            ('unmonitored_single_magnetic_lock', 'Unmon Single Mag Lock'),
            ('unmonitored_double_magnetic_lock', 'Unmon Double Mag Lock')
        ]

        entries = {}
        for idx, (field, name) in enumerate(fields):
            lbl = ttk.Label(win, text=name)
            lbl.grid(row=idx+2, column=0, padx=10, pady=5, sticky='w')
            ent = ttk.Entry(win)
            ent.grid(row=idx+2, column=1, padx=10, pady=5, sticky='ew')
            val = getattr(dt.config, field) if dt else 0
            ent.insert(0, str(val))
            entries[field] = ent

        def save():
            try:
                dt_id = int(ent_id.get())
                name = ent_name.get()
                if not name:
                    return
                data = {f: int(entries[f].get()) for f, _ in fields}
                if dt:
                    dt.name = name
                    dt.update_config(**data)
                else:
                    if any(x.type_id == dt_id for x in self.access_door_types):
                        return
                    new_dt = AccessDoorType(dt_id, name)
                    new_dt.update_config(**data)
                    self.access_door_types.append(new_dt)
                self.update_door_types_list()
                win.destroy()
            except ValueError:
                pass

        btn = ttk.Button(win, text="Save", command=save)
        btn.grid(row=len(fields)+2, column=0, columnspan=2, pady=15)

    def _calculate_kantech_for_line(self, dc: DCDevice) -> Tuple[str, dict]:
        totals = dc.calculate_totals()
        
        req_smart_readers = totals['smart_card_readers']
        req_normal_readers = totals['smart_cards'] + totals['fingerprints']

        chosen_ctrl = None
        for ctrl in self.controllers:
            if ctrl['smart_card_readers'] >= req_smart_readers and ctrl['readers'] >= req_normal_readers:
                chosen_ctrl = ctrl
                break
        if not chosen_ctrl:
            chosen_ctrl = self.controllers[-1]

        input_shortage = max(0, totals['inputs'] - chosen_ctrl['inputs'])
        output_shortage = max(0, totals['outputs'] - chosen_ctrl['outputs'])

        modules_needed = []
        modules_cost = 0

        while input_shortage > 0 or output_shortage > 0:
            best_mod = None
            best_score = -1
            for mod in self.expansion_modules:
                inputs_covered = min(input_shortage, mod['inputs']) if input_shortage > 0 else 0
                outputs_covered = min(output_shortage, mod['outputs']) if output_shortage > 0 else 0
                score = inputs_covered + outputs_covered
                if score > best_score:
                    best_score = score
                    best_mod = mod
            if not best_mod:
                break
            modules_needed.append(best_mod['name'])
            modules_cost += best_mod['cost']
            input_shortage = max(0, input_shortage - best_mod['inputs'])
            output_shortage = max(0, output_shortage - best_mod['outputs'])

        total_cost = chosen_ctrl['cost'] + modules_cost
        
        # RESTORED: Detailed Output Log Breakdown
        summary = f"========================================\n"
        summary += f"DC Line {dc.dc_number} Analysis\n"
        summary += f"========================================\n"
        summary += f"Demanded Assets:\n"
        summary += f"  - Normal Reader Slots Needed : {req_normal_readers} (Cards: {totals['smart_cards']}, Biometric: {totals['fingerprints']})\n"
        summary += f"  - Smart Card Reader Slots    : {req_smart_readers}\n"
        summary += f"  - Total Core Inputs Required : {totals['inputs']}\n"
        summary += f"  - Total Core Outputs Required: {totals['outputs']}\n\n"
        summary += f"Hardware Assignment:\n"
        summary += f"  - Chosen Base Controller     : {chosen_ctrl['name'].upper()} (${chosen_ctrl['cost']})\n"
        summary += f"    Provides: {chosen_ctrl['readers']} normal readers, {chosen_ctrl['smart_card_readers']} smart slots, {chosen_ctrl['inputs']} inputs, {chosen_ctrl['outputs']} outputs\n"
        summary += f"  - Target Modules Expanded    : {modules_needed if modules_needed else 'None Required'}\n"
        summary += f"  - Total Modules Cost         : ${modules_cost}\n"
        summary += f"----------------------------------------\n"
        summary += f"Net Total Line Valuation       : ${total_cost}\n\n"
        
        return summary, {'controller': chosen_ctrl['name'], 'modules': modules_needed, 'cost': total_cost}

    def calculate_all_kantech(self):
        if not self.dc_lines:
            return
        self.kantech_results_text.delete(1.0, tk.END)
        self.kantech_all_results = []
        self.kantech_grand_total = 0
        
        full_text = "--- COMPLETE DETAILED KANTECH SYSTEM ANALYSIS ---\n\n"
        for dc in self.dc_lines:
            txt, res = self._calculate_kantech_for_line(dc)
            full_text += txt
            self.kantech_grand_total += res['cost']
            self.kantech_all_results.append({'dc_number': dc.dc_number, **res})
            
        full_text += f"\nGRAND TOTAL KANTECH SYSTEMS INVESTMENT: ${self.kantech_grand_total}\n"
        self.kantech_results_text.insert(tk.END, full_text)

    def calculate_selected_kantech(self):
        sel_str = self.selected_dc_line_var.get()
        if not sel_str:
            return
        dc_num = int(sel_str.split()[-1])
        dc = next((x for x in self.dc_lines if x.dc_number == dc_num), None)
        if dc:
            self.kantech_results_text.delete(1.0, tk.END)
            txt, _ = self._calculate_kantech_for_line(dc)
            self.kantech_results_text.insert(tk.END, txt)

    def _calculate_gstar_for_line(self, dc: DCDevice) -> Tuple[str, dict]:
        totals = dc.calculate_totals()
        ctrl = self.swh_calculator.select_controller_for_readers(totals['readers'])
        if not ctrl:
            return "", {}
        exp = self.swh_calculator.calculate_expansion_for_swh(totals['inputs'], totals['outputs'], ctrl.inputs, ctrl.outputs)
        line_cost = ctrl.price + exp['cost']
        return f"DC Line {dc.dc_number} SWH: {ctrl.name} - Total: ${line_cost}\n", {'cost': line_cost}

    def calculate_all_gstar(self):
        if not self.dc_lines:
            return
        self.swh_results_text.delete(1.0, tk.END)
        gstar_total = 0
        for dc in self.dc_lines:
            txt, res = self._calculate_gstar_for_line(dc)
            self.swh_results_text.insert(tk.END, txt)
            if res:
                gstar_total += res['cost']
        self.swh_results_text.insert(tk.END, f"\nTotal SWH: ${gstar_total}")

    def calculate_selected_gstar(self):
        sel_str = self.selected_dc_line_var.get()
        if not sel_str:
            return
        dc_num = int(sel_str.split()[-1])
        dc = next((x for x in self.dc_lines if x.dc_number == dc_num), None)
        if dc:
            self.swh_results_text.delete(1.0, tk.END)
            txt, _ = self._calculate_gstar_for_line(dc)
            self.swh_results_text.insert(tk.END, txt)

    def calculate_kantech_license(self):
        num_controllers = len(self.dc_lines)
        cost = 500 if self.redundancy_var.get() else 0
        self.kantech_license_results_text.delete(1.0, tk.END)
        self.kantech_license_results_text.insert(tk.END, f"Total Controllers: {num_controllers}\nLicense cost: ${cost}")

    def export_kantech_results(self):
        if not self.kantech_all_results:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            pd.DataFrame(self.kantech_all_results).to_csv(path, index=False)


if __name__ == "__main__":
    app = KantechDCCalculatorGUI()
    
    # Prepopulating template items
    app.access_door_types.append(AccessDoorType(1, "Standard Secure Profile"))
    app.access_door_types[0].update_config(smart_card=1, door_sensor=1, magnetic_lock=1, rex_button=1)
    
    app.access_door_types.append(AccessDoorType(2, "Biometric Secure Entry"))
    app.access_door_types[1].update_config(fingerprint=1, door_sensor=1, electric_lock=1, rex_button=1)
    
    for i in range(1, 3):
        mock_dc = DCDevice(dc_number=i, smart_card=2, door_sensor=2, magnetic_lock=1, rex_button=2)
        app.dc_lines.append(mock_dc)
        
    app.update_dc_lines_list()
    app.update_door_types_list()
    app.root.mainloop()
