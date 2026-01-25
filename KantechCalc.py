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
    fingerprint: int = 0
    door_sensor: int = 0
    magnetic_lock: int = 0
    electric_lock: int = 0
    rex_button: int = 0
    push_button: int = 0
    break_glass: int = 0
    buzzer: int = 0
    double_door_lock: int = 0  # Counts as BOTH 1 input AND 1 output
    ddl_sensors: int = 0
    
    def calculate_totals(self):
        """Calculate readers, inputs, outputs for this DC line"""
        # Readers = Smart Card + Fingerprint (Excel Column M)
        readers = self.smart_card + self.fingerprint
        
        # Inputs = Door Sensor + REX Button + Push Button + Break Glass + Buzzer + Magnetic Lock + DDL Sensors + Double Door Lock
        # NOTE: Double Door Lock counts as 1 input
        inputs = (self.door_sensor + self.rex_button + self.push_button + 
                 self.break_glass + self.buzzer + self.magnetic_lock + 
                 self.ddl_sensors + self.double_door_lock)
        
        # Outputs = Magnetic Lock + Electric Lock + DDL Sensors + Double Door Lock
        # NOTE: Double Door Lock counts as 1 output
        outputs = (self.magnetic_lock + self.electric_lock + 
                  self.ddl_sensors + self.double_door_lock)
        
        return {'readers': readers, 'inputs': inputs, 'outputs': outputs}
    
    def add_configuration(self, other_config):
        """Add another configuration to this DC line"""
        self.smart_card += other_config.smart_card
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
    """GSTAR controller information from SWH Access.xlsx"""
    def __init__(self, name, readers, inputs, outputs, price, number_of_acm):
        self.name = name
        self.readers = readers
        self.inputs = inputs
        self.outputs = outputs
        self.price = price
        self.number_of_acm = number_of_acm
    
    def can_handle_readers(self, required_readers):
        """Check if this controller can handle the reader requirements"""
        return self.readers >= required_readers


class SWHControllerCalculator:
    """Calculator for SWH GSTAR controllers (one controller per DC line)"""
    def __init__(self):
        # GSTAR controllers from the Excel sheet
        self.gstar_controllers = [
            GSTARController("GSTAR004 (4 readers)", 4, 8, 4, 1395, 0),
            GSTARController("GSTAR004 (8 readers)", 8, 16, 12, 2123, 0),
            GSTARController("GSTAR008", 8, 24, 8, 3125, 1),
            GSTARController("GSTAR016", 16, 48, 16, 4166, 2),
            GSTARController("GSTAR016 (24 readers)", 24, 72, 24, 5166, 3),
            GSTARController("GSTAR016 (32 readers)", 32, 96, 32, 6166, 4)
        ]
        
        # SWH License tiers
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
        
        # SWH Expansion modules from the table
        self.swh_expansion_modules = [
            {'name': 'AS0073-000', 'inputs': 8, 'outputs': 0, 'cost': 333},
            {'name': 'AS0074-000', 'inputs': 0, 'outputs': 8, 'cost': 395}
        ]
    
    def select_controller_for_readers(self, required_readers):
        """Select the cheapest GSTAR controller that meets or exceeds reader requirements"""
        suitable_controllers = []
        for controller in self.gstar_controllers:
            if controller.can_handle_readers(required_readers):
                suitable_controllers.append(controller)
        
        if not suitable_controllers:
            return None
        
        # Sort by price (cheapest first)
        suitable_controllers.sort(key=lambda x: x.price)
        
        # Return the cheapest suitable controller
        return suitable_controllers[0]
    
    def calculate_expansion_for_swh(self, dc_inputs: int, dc_outputs: int, 
                                  controller_inputs: int, controller_outputs: int) -> Dict:
        """Calculate SWH expansion modules needed for a DC line"""
        # Calculate shortages
        input_shortage = max(0, dc_inputs - controller_inputs)
        output_shortage = max(0, dc_outputs - controller_outputs)
        
        result = ""
        result += f"\nI/O Analysis:\n"
        result += f"  Required: {dc_inputs} inputs, {dc_outputs} outputs\n"
        result += f"  Controller provides: {controller_inputs} inputs, {controller_outputs} outputs\n"
        result += f"  Shortage: {input_shortage} inputs, {output_shortage} outputs\n"
        
        if input_shortage == 0 and output_shortage == 0:
            result += "  ✅ No expansion modules needed\n"
            return {'modules': [], 'cost': 0, 'input_modules': 0, 'output_modules': 0, 'result': result}
        
        # Calculate expansion modules needed
        expansion_modules = []
        expansion_cost = 0
        
        input_modules = 0
        output_modules = 0
        
        # Add input modules if needed
        if input_shortage > 0:
            # Use AS0073-000 modules (8 inputs each)
            as0073_needed = int(np.ceil(input_shortage / 8))
            expansion_modules.append(f"AS0073-000 (x{as0073_needed})")
            expansion_cost += 333 * as0073_needed
            input_modules = as0073_needed
        
        # Add output modules if needed
        if output_shortage > 0:
            # Use AS0074-000 modules (8 outputs each)
            as0074_needed = int(np.ceil(output_shortage / 8))
            expansion_modules.append(f"AS0074-000 (x{as0074_needed})")
            expansion_cost += 395 * as0074_needed
            output_modules = as0074_needed
        
        result += f"  Expansion solution: {expansion_modules}\n"
        result += f"  Expansion cost: ${expansion_cost}\n"
        
        return {
            'modules': expansion_modules,
            'cost': expansion_cost,
            'input_modules': input_modules,
            'output_modules': output_modules,
            'result': result
        }


class KantechDCCalculatorGUI:
    def __init__(self):
        self.dc_lines: List[DCDevice] = []
        self.access_door_types: List[AccessDoorType] = []
        self.swh_calculator = SWHControllerCalculator()
        
        # Controller models
        self.controllers = [
            {'name': 'kt-1', 'readers': 1, 'cost': 450, 'inputs': 4, 'outputs': 2},
            {'name': 'kt-2', 'readers': 2, 'cost': 750, 'inputs': 8, 'outputs': 2},
            {'name': 'kt-400', 'readers': 4, 'cost': 1400, 'inputs': 16, 'outputs': 4}
        ]
        
        # All available expansion modules
        self.expansion_modules = [
            {'name': 'inout16 (16/0)', 'inputs': 16, 'outputs': 0, 'cost': 447},
            {'name': 'inout16 (12/4)', 'inputs': 12, 'outputs': 4, 'cost': 447},
            {'name': 'inout16 (8/8)', 'inputs': 8, 'outputs': 8, 'cost': 447},
            {'name': 'inout16 (4/12)', 'inputs': 4, 'outputs': 12, 'cost': 447},
            {'name': 'inout16 (0/16)', 'inputs': 0, 'outputs': 16, 'cost': 447},
            {'name': 'in16', 'inputs': 16, 'outputs': 0, 'cost': 470},
            {'name': 'r8', 'inputs': 0, 'outputs': 8, 'cost': 470}
        ]
        
        # License information
        self.license_info = {
            'special': {
                'name': 'Kantech Special License',
                'max_controllers': 32,
                'description': 'For systems with 32 or fewer controllers (non-redundant)',
                'cost': 0
            },
            'corporate': {
                'name': 'Kantech Corporate License',
                'min_controllers': 33,
                'description': 'For systems with more than 32 controllers (non-redundant)',
                'cost': 0
            },
            'global': {
                'name': 'Global License',
                'description': 'Required for ANY redundancy configuration (replaces Special/Corporate)',
                'cost': 0
            },
            'gateway': {
                'name': 'Gateway License',
                'description': 'Required for gateway/server communication in redundant systems',
                'cost': 500
            },
            'redundancy': {
                'name': 'Redundancy License',
                'description': 'Additional license for failover/redundancy capability',
                'cost': 750
            }
        }
        
        # Create main window FIRST
        self.root = tk.Tk()
        self.root.title("Access Control System Calculator")
        self.root.geometry("1200x800")
        
        # Now create tkinter variables AFTER root window is created
        self.selected_dc_line_var = tk.StringVar()
        self.selected_door_type_var = tk.StringVar()
        self.redundancy_var = tk.BooleanVar(value=False)
        
        # Configure styles
        self.setup_styles()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_main_tab()
        self.create_dc_lines_tab()
        self.create_door_types_tab()
        self.create_calculation_tab()
        self.create_license_tab()
        self.create_export_tab()
        
        # Status bar
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Subheading.TLabel', font=('Arial', 10, 'bold'))
        
    def create_main_tab(self):
        """Create the main/home tab"""
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Main")
        
        # Title
        title_label = ttk.Label(self.main_tab, text="ACCESS CONTROL SYSTEM CALCULATOR", 
                               style='Title.TLabel')
        title_label.pack(pady=20)
        
        # System info frame
        info_frame = ttk.LabelFrame(self.main_tab, text="System Information", padding=10)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Current system status
        self.system_info_text = tk.Text(info_frame, height=8, width=80)
        self.system_info_text.pack(fill=tk.BOTH, expand=True)
        self.update_system_info()
        
        # Quick actions frame
        actions_frame = ttk.LabelFrame(self.main_tab, text="Quick Actions", padding=10)
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Quick action buttons
        ttk.Button(actions_frame, text="Add DC Line", 
                  command=lambda: self.notebook.select(self.dc_lines_tab)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Manage Door Types", 
                  command=lambda: self.notebook.select(self.door_types_tab)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Calculate Kantech", 
                  command=lambda: self.notebook.select(self.calculation_tab)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Calculate SWH/GSTAR", 
                  command=lambda: self.show_gstar_calculation()).pack(side=tk.LEFT, padx=5)
        
        # System overview frame
        overview_frame = ttk.LabelFrame(self.main_tab, text="System Overview", padding=10)
        overview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Overview text
        self.overview_text = scrolledtext.ScrolledText(overview_frame, height=15)
        self.overview_text.pack(fill=tk.BOTH, expand=True)
        self.update_overview()
        
    def create_dc_lines_tab(self):
        """Create DC lines management tab"""
        self.dc_lines_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dc_lines_tab, text="DC Lines")
        
        # Top frame for controls
        top_frame = ttk.Frame(self.dc_lines_tab)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="DC Line Management", style='Title.TLabel').pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="Add DC Line", command=self.show_add_dc_line_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_dc_line).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected_dc_line).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh", command=self.update_dc_lines_list).pack(side=tk.LEFT, padx=5)
        
        # DC lines list
        list_frame = ttk.LabelFrame(self.dc_lines_tab, text="DC Lines List", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview for DC lines
        columns = ('DC', 'Smart Card', 'Fingerprint', 'Door Sensor', 'Mag Lock', 'Elec Lock', 
                  'REX', 'Push Button', 'Break Glass', 'Buzzer', 'DDL', 'DDL Sensors',
                  'Readers', 'Inputs', 'Outputs')
        
        self.dc_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.dc_tree.heading(col, text=col)
            self.dc_tree.column(col, width=80, minwidth=50)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.dc_tree.yview)
        self.dc_tree.configure(yscrollcommand=scrollbar.set)
        
        self.dc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection
        self.dc_tree.bind('<<TreeviewSelect>>', self.on_dc_line_selected)
        
    def create_door_types_tab(self):
        """Create door types management tab"""
        self.door_types_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.door_types_tab, text="Door Types")
        
        # Top frame for controls
        top_frame = ttk.Frame(self.door_types_tab)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Access Door Types Management", style='Title.TLabel').pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="Add Door Type", command=self.show_add_door_type_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_door_type).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected_door_type).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Apply to DC Line", command=self.apply_door_type_to_dc).pack(side=tk.LEFT, padx=5)
        
        # Door types list
        list_frame = ttk.LabelFrame(self.door_types_tab, text="Door Types List", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview for door types
        columns = ('ID', 'Name', 'Smart Card', 'Fingerprint', 'Door Sensor', 'Readers', 'Inputs', 'Outputs')
        
        self.door_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.door_tree.heading(col, text=col)
            self.door_tree.column(col, width=100, minwidth=50)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.door_tree.yview)
        self.door_tree.configure(yscrollcommand=scrollbar.set)
        
        self.door_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection
        self.door_tree.bind('<<TreeviewSelect>>', self.on_door_type_selected)
        
    def create_calculation_tab(self):
        """Create calculation tab"""
        self.calculation_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.calculation_tab, text="Calculations")
        
        # Notebook for calculation types
        calc_notebook = ttk.Notebook(self.calculation_tab)
        calc_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Kantech calculation tab
        self.kantech_calc_tab = ttk.Frame(calc_notebook)
        calc_notebook.add(self.kantech_calc_tab, text="Kantech System")
        
        # SWH/GSTAR calculation tab
        self.swh_calc_tab = ttk.Frame(calc_notebook)
        calc_notebook.add(self.swh_calc_tab, text="SWH/GSTAR System")
        
        self.create_kantech_calculation_frame()
        self.create_swh_calculation_frame()
        
    def create_kantech_calculation_frame(self):
        """Create Kantech calculation frame"""
        # Top frame for controls
        top_frame = ttk.Frame(self.kantech_calc_tab)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Kantech System Calculation", style='Title.TLabel').pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="Calculate All DC Lines", 
                  command=self.calculate_all_kantech).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Calculate Selected", 
                  command=self.calculate_selected_kantech).pack(side=tk.LEFT, padx=5)
        
        # DC line selection
        select_frame = ttk.LabelFrame(self.kantech_calc_tab, text="Select DC Line", padding=10)
        select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(select_frame, text="DC Line:").pack(side=tk.LEFT, padx=5)
        
        self.dc_line_combo = ttk.Combobox(select_frame, textvariable=self.selected_dc_line_var, 
                                         state='readonly', width=20)
        self.dc_line_combo.pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.kantech_calc_tab, text="Calculation Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.kantech_results_text = scrolledtext.ScrolledText(results_frame, height=20)
        self.kantech_results_text.pack(fill=tk.BOTH, expand=True)
        
    def create_swh_calculation_frame(self):
        """Create SWH/GSTAR calculation frame"""
        # Top frame for controls
        top_frame = ttk.Frame(self.swh_calc_tab)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="SWH/GSTAR System Calculation", style='Title.TLabel').pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="Calculate All DC Lines", 
                  command=self.calculate_all_gstar).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Calculate Selected", 
                  command=self.calculate_selected_gstar).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Calculate License", 
                  command=self.calculate_swh_license).pack(side=tk.LEFT, padx=5)
        
        # DC line selection
        select_frame = ttk.LabelFrame(self.swh_calc_tab, text="Select DC Line", padding=10)
        select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(select_frame, text="DC Line:").pack(side=tk.LEFT, padx=5)
        
        self.swh_dc_line_combo = ttk.Combobox(select_frame, textvariable=self.selected_dc_line_var, 
                                             state='readonly', width=20)
        self.swh_dc_line_combo.pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.swh_calc_tab, text="Calculation Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.swh_results_text = scrolledtext.ScrolledText(results_frame, height=20)
        self.swh_results_text.pack(fill=tk.BOTH, expand=True)
        
    def create_license_tab(self):
        """Create license calculation tab"""
        self.license_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.license_tab, text="Licenses")
        
        # Create notebook for license types
        license_notebook = ttk.Notebook(self.license_tab)
        license_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Kantech license tab
        self.kantech_license_tab = ttk.Frame(license_notebook)
        license_notebook.add(self.kantech_license_tab, text="Kantech Licenses")
        
        # SWH license tab
        self.swh_license_tab = ttk.Frame(license_notebook)
        license_notebook.add(self.swh_license_tab, text="SWH Licenses")
        
        self.create_kantech_license_frame()
        self.create_swh_license_frame()
        
    def create_kantech_license_frame(self):
        """Create Kantech license frame"""
        # Title
        ttk.Label(self.kantech_license_tab, text="Kantech License Calculation", style='Title.TLabel').pack(pady=20)
        
        # Redundancy selection
        redundancy_frame = ttk.LabelFrame(self.kantech_license_tab, text="System Configuration", padding=10)
        redundancy_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Checkbutton(redundancy_frame, text="Use Redundancy Configuration", 
                       variable=self.redundancy_var).pack(anchor=tk.W)
        
        ttk.Label(redundancy_frame, text="Redundancy provides backup/failover capability", 
                 font=('Arial', 9, 'italic')).pack(anchor=tk.W, pady=5)
        
        # Calculate button
        ttk.Button(self.kantech_license_tab, text="Calculate Kantech License Requirements", 
                  command=self.calculate_kantech_license).pack(pady=10)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.kantech_license_tab, text="Kantech License Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.kantech_license_results_text = scrolledtext.ScrolledText(results_frame, height=20)
        self.kantech_license_results_text.pack(fill=tk.BOTH, expand=True)
        
    def create_swh_license_frame(self):
        """Create SWH license frame"""
        # Title
        ttk.Label(self.swh_license_tab, text="SWH License Calculation", style='Title.TLabel').pack(pady=20)
        
        # Calculate button
        ttk.Button(self.swh_license_tab, text="Calculate SWH License Requirements", 
                  command=self.calculate_swh_license_gui).pack(pady=10)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.swh_license_tab, text="SWH License Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.swh_license_results_text = scrolledtext.ScrolledText(results_frame, height=20)
        self.swh_license_results_text.pack(fill=tk.BOTH, expand=True)
        
    def create_export_tab(self):
        """Create export tab"""
        self.export_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.export_tab, text="Export")
        
        # Title
        ttk.Label(self.export_tab, text="Export Results", style='Title.TLabel').pack(pady=20)
        
        # Export options frame
        options_frame = ttk.LabelFrame(self.export_tab, text="Export Options", padding=20)
        options_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        ttk.Button(options_frame, text="Export Kantech Results to CSV", 
                  command=self.export_kantech_results).pack(pady=10, fill=tk.X)
        
        ttk.Button(options_frame, text="Export SWH/GSTAR Results to CSV", 
                  command=self.export_gstar_results).pack(pady=10, fill=tk.X)
        
        ttk.Button(options_frame, text="Export System Summary to CSV", 
                  command=self.export_system_summary).pack(pady=10, fill=tk.X)
        
        # Export status
        self.export_status = ttk.Label(self.export_tab, text="")
        self.export_status.pack(pady=10)
        
    def update_system_info(self):
        """Update system information display"""
        self.system_info_text.delete(1.0, tk.END)
        
        info = f"Current System Status:\n"
        info += f"• DC Lines: {len(self.dc_lines)}\n"
        info += f"• Access Door Types: {len(self.access_door_types)}\n"
        
        if self.dc_lines:
            total_readers = sum(dc.calculate_totals()['readers'] for dc in self.dc_lines)
            total_inputs = sum(dc.calculate_totals()['inputs'] for dc in self.dc_lines)
            total_outputs = sum(dc.calculate_totals()['outputs'] for dc in self.dc_lines)
            
            info += f"\nTotal Requirements:\n"
            info += f"• Readers: {total_readers}\n"
            info += f"• Inputs: {total_inputs}\n"
            info += f"• Outputs: {total_outputs}\n"
        
        self.system_info_text.insert(1.0, info)
        self.system_info_text.config(state=tk.DISABLED)
        
    def update_overview(self):
        """Update system overview"""
        self.overview_text.delete(1.0, tk.END)
        
        overview = "SYSTEM OVERVIEW\n"
        overview += "=" * 50 + "\n\n"
        
        # DC Lines overview
        overview += "DC LINES:\n"
        overview += "-" * 20 + "\n"
        
        if self.dc_lines:
            for dc in self.dc_lines:
                totals = dc.calculate_totals()
                overview += f"DC Line {dc.dc_number}: {totals['readers']} readers, "
                overview += f"{totals['inputs']} inputs, {totals['outputs']} outputs\n"
                overview += f"  Smart Card: {dc.smart_card}, Fingerprint: {dc.fingerprint}, "
                overview += f"Door Sensor: {dc.door_sensor}\n"
        else:
            overview += "No DC lines configured\n"
        
        overview += "\nDOOR TYPES:\n"
        overview += "-" * 20 + "\n"
        
        if self.access_door_types:
            for dt in self.access_door_types:
                overview += f"{dt}\n"
        else:
            overview += "No door types defined\n"
        
        self.overview_text.insert(1.0, overview)
        self.overview_text.config(state=tk.DISABLED)
        
    def update_dc_lines_list(self):
        """Update DC lines treeview"""
        # Clear existing items
        for item in self.dc_tree.get_children():
            self.dc_tree.delete(item)
        
        # Add DC lines
        for dc in self.dc_lines:
            totals = dc.calculate_totals()
            values = (
                dc.dc_number,
                dc.smart_card,
                dc.fingerprint,
                dc.door_sensor,
                dc.magnetic_lock,
                dc.electric_lock,
                dc.rex_button,
                dc.push_button,
                dc.break_glass,
                dc.buzzer,
                dc.double_door_lock,
                dc.ddl_sensors,
                totals['readers'],
                totals['inputs'],
                totals['outputs']
            )
            self.dc_tree.insert('', tk.END, values=values)
        
        # Update combobox
        dc_line_options = [f"DC Line {dc.dc_number}" for dc in self.dc_lines]
        self.dc_line_combo['values'] = dc_line_options
        self.swh_dc_line_combo['values'] = dc_line_options
        
        if dc_line_options:
            self.selected_dc_line_var.set(dc_line_options[0])
        
        # Update system info and overview
        self.update_system_info()
        self.update_overview()
        
    def update_door_types_list(self):
        """Update door types treeview"""
        # Clear existing items
        for item in self.door_tree.get_children():
            self.door_tree.delete(item)
        
        # Add door types
        for dt in self.access_door_types:
            totals = dt.get_totals()
            values = (
                dt.type_id,
                dt.name,
                dt.config.smart_card,
                dt.config.fingerprint,
                dt.config.door_sensor,
                totals['readers'],
                totals['inputs'],
                totals['outputs']
            )
            self.door_tree.insert('', tk.END, values=values)
        
        # Update system info and overview
        self.update_system_info()
        self.update_overview()
        
    def on_dc_line_selected(self, event):
        """Handle DC line selection"""
        selection = self.dc_tree.selection()
        if selection:
            item = self.dc_tree.item(selection[0])
            dc_num = item['values'][0]
            self.selected_dc_line_var.set(f"DC Line {dc_num}")
            
    def on_door_type_selected(self, event):
        """Handle door type selection"""
        selection = self.door_tree.selection()
        if selection:
            item = self.door_tree.item(selection[0])
            type_id = item['values'][0]
            self.selected_door_type_var.set(f"Door Type {type_id}")
            
    def show_add_dc_line_dialog(self):
        """Show dialog to add DC line"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add DC Line")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Method selection
        method_frame = ttk.LabelFrame(dialog, text="Add Method", padding=10)
        method_frame.pack(fill=tk.X, padx=10, pady=10)
        
        method_var = tk.StringVar(value="manual")
        
        ttk.Radiobutton(method_frame, text="Manual Entry", 
                       variable=method_var, value="manual").pack(anchor=tk.W, pady=5)
        ttk.Radiobutton(method_frame, text="Combine Door Types", 
                       variable=method_var, value="combine").pack(anchor=tk.W, pady=5)
        
        # Manual entry frame
        manual_frame = ttk.LabelFrame(dialog, text="Manual Configuration", padding=10)
        
        devices = [
            ("INDOOR Smart Card Reader", 'smart_card'),
            ("Finger Print Reader", 'fingerprint'),
            ("Door Sensor", 'door_sensor'),
            ("Magnetic Door Lock", 'magnetic_lock'),
            ("Electric Door Lock", 'electric_lock'),
            ("REX Button", 'rex_button'),
            ("Push Button w/ Indicator", 'push_button'),
            ("Break Glass", 'break_glass'),
            ("Buzzer", 'buzzer'),
            ("Double Door Lock", 'double_door_lock'),
            ("DDL Sensors", 'ddl_sensors')
        ]
        
        entries = {}
        for i, (label, key) in enumerate(devices):
            ttk.Label(manual_frame, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(manual_frame, width=10)
            entry.insert(0, "0")
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[key] = entry
        
        # Door types selection frame - SIMPLIFIED VERSION WITH QUANTITY FOR EACH DOOR TYPE
        combine_frame = ttk.LabelFrame(dialog, text="Select Door Types and Quantities", padding=10)
        
        # Create a scrollable frame for door types
        canvas = tk.Canvas(combine_frame)
        scrollbar = ttk.Scrollbar(combine_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Dictionary to store quantity entries for each door type
        quantity_entries = {}
        
        # Create quantity entries for each door type
        if self.access_door_types:
            for i, dt in enumerate(self.access_door_types):
                frame = ttk.Frame(scrollable_frame)
                frame.pack(fill=tk.X, pady=2, padx=5)
                
                ttk.Label(frame, text=f"{dt.name}:", width=30).pack(side=tk.LEFT)
                entry = ttk.Entry(frame, width=10)
                entry.insert(0, "0")
                entry.pack(side=tk.RIGHT, padx=5)
                quantity_entries[dt.type_id] = entry
        else:
            ttk.Label(scrollable_frame, text="No door types defined yet!", 
                     font=('Arial', 10, 'italic')).pack(pady=20)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def add_selected_door_types():
            # Create DC line by combining door types with quantities
            dc_number = len(self.dc_lines) + 1
            new_dc_line = DCDevice(dc_number=dc_number)
            
            total_quantity = 0
            
            # Get quantities for each door type
            for dt in self.access_door_types:
                try:
                    quantity = int(quantity_entries[dt.type_id].get())
                    if quantity < 0:
                        messagebox.showerror("Error", f"Quantity for '{dt.name}' cannot be negative")
                        return
                    
                    # Add the door type configuration multiple times based on quantity
                    for _ in range(quantity):
                        new_dc_line.add_configuration(dt.config)
                    
                    total_quantity += quantity
                        
                except ValueError:
                    messagebox.showerror("Error", f"Invalid quantity for '{dt.name}'. Please enter a number.")
                    return
            
            # Check if at least one door type was added
            if total_quantity == 0:
                messagebox.showwarning("Warning", "Please enter quantity > 0 for at least one door type")
                return
            
            self.dc_lines.append(new_dc_line)
            self.update_dc_lines_list()
            dialog.destroy()
            messagebox.showinfo("Success", f"DC Line {dc_number} created successfully with {total_quantity} door type(s)!")
        
        def show_selected_frame():
            if method_var.get() == "manual":
                manual_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                combine_frame.pack_forget()
                add_button.config(command=add_manual_dc_line)
            else:
                combine_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                manual_frame.pack_forget()
                add_button.config(command=add_selected_door_types)
        
        method_var.trace('w', lambda *args: show_selected_frame())
        
        def add_manual_dc_line():
            try:
                dc_number = len(self.dc_lines) + 1
                config = {}
                
                for key, entry in entries.items():
                    value = int(entry.get())
                    if value < 0:
                        raise ValueError(f"{key} cannot be negative")
                    config[key] = value
                
                new_dc_line = DCDevice(dc_number=dc_number, **config)
                self.dc_lines.append(new_dc_line)
                self.update_dc_lines_list()
                dialog.destroy()
                messagebox.showinfo("Success", f"DC Line {dc_number} added successfully!")
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        add_button = ttk.Button(button_frame, text="Add DC Line")
        add_button.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Show initial frame
        show_selected_frame()
        
    def show_add_door_type_dialog(self):
        """Show dialog to add door type"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Access Door Type")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Name entry
        ttk.Label(dialog, text="Door Type Name:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(dialog, text="Device Configuration", padding=10)
        config_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        devices = [
            ("INDOOR Smart Card Reader", 'smart_card'),
            ("Finger Print Reader", 'fingerprint'),
            ("Door Sensor", 'door_sensor'),
            ("Magnetic Door Lock", 'magnetic_lock'),
            ("Electric Door Lock", 'electric_lock'),
            ("REX Button", 'rex_button'),
            ("Push Button w/ Indicator", 'push_button'),
            ("Break Glass", 'break_glass'),
            ("Buzzer", 'buzzer'),
            ("Double Door Lock", 'double_door_lock'),
            ("DDL Sensors", 'ddl_sensors')
        ]
        
        entries = {}
        for i, (label, key) in enumerate(devices):
            frame = ttk.Frame(config_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, "0")
            entry.pack(side=tk.RIGHT, padx=5)
            entries[key] = entry
        
        def add_door_type():
            try:
                name = name_entry.get().strip()
                if not name:
                    messagebox.showerror("Error", "Please enter a door type name")
                    return
                
                type_id = len(self.access_door_types) + 1
                config = {}
                
                for key, entry in entries.items():
                    value = int(entry.get())
                    if value < 0:
                        raise ValueError(f"{key} cannot be negative")
                    config[key] = value
                
                door_type = AccessDoorType(type_id=type_id, name=name)
                door_type.update_config(**config)
                self.access_door_types.append(door_type)
                
                self.update_door_types_list()
                dialog.destroy()
                messagebox.showinfo("Success", f"Door Type '{name}' added successfully!")
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Add", command=add_door_type).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
    def edit_selected_dc_line(self):
        """Edit selected DC line"""
        selection = self.dc_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a DC line to edit")
            return
        
        item = self.dc_tree.item(selection[0])
        values = item['values']
        dc_num = values[0]
        
        # Find DC line
        dc_line = next((dc for dc in self.dc_lines if dc.dc_number == dc_num), None)
        if not dc_line:
            messagebox.showerror("Error", "DC line not found")
            return
        
        # Show edit dialog
        self.show_edit_dc_line_dialog(dc_line)
        
    def show_edit_dc_line_dialog(self, dc_line):
        """Show dialog to edit DC line"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit DC Line {dc_line.dc_number}")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Edit DC Line {dc_line.dc_number}", 
                 style='Title.TLabel').pack(pady=10)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(dialog, text="Device Configuration", padding=10)
        config_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        devices = [
            ("INDOOR Smart Card Reader", 'smart_card'),
            ("Finger Print Reader", 'fingerprint'),
            ("Door Sensor", 'door_sensor'),
            ("Magnetic Door Lock", 'magnetic_lock'),
            ("Electric Door Lock", 'electric_lock'),
            ("REX Button", 'rex_button'),
            ("Push Button w/ Indicator", 'push_button'),
            ("Break Glass", 'break_glass'),
            ("Buzzer", 'buzzer'),
            ("Double Door Lock", 'double_door_lock'),
            ("DDL Sensors", 'ddl_sensors')
        ]
        
        entries = {}
        for i, (label, key) in enumerate(devices):
            frame = ttk.Frame(config_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, str(getattr(dc_line, key)))
            entry.pack(side=tk.RIGHT, padx=5)
            entries[key] = entry
        
        def save_changes():
            try:
                config = {}
                for key, entry in entries.items():
                    value = int(entry.get())
                    if value < 0:
                        raise ValueError(f"{key} cannot be negative")
                    config[key] = value
                
                for key, value in config.items():
                    setattr(dc_line, key, value)
                
                self.update_dc_lines_list()
                dialog.destroy()
                messagebox.showinfo("Success", f"DC Line {dc_line.dc_number} updated successfully!")
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save", command=save_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
    def delete_selected_dc_line(self):
        """Delete selected DC line"""
        selection = self.dc_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a DC line to delete")
            return
        
        item = self.dc_tree.item(selection[0])
        dc_num = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Delete DC Line {dc_num}?"):
            self.dc_lines = [dc for dc in self.dc_lines if dc.dc_number != dc_num]
            self.update_dc_lines_list()
            messagebox.showinfo("Success", f"DC Line {dc_num} deleted")
            
    def edit_selected_door_type(self):
        """Edit selected door type"""
        selection = self.door_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a door type to edit")
            return
        
        item = self.door_tree.item(selection[0])
        type_id = item['values'][0]
        
        # Find door type
        door_type = next((dt for dt in self.access_door_types if dt.type_id == type_id), None)
        if not door_type:
            messagebox.showerror("Error", "Door type not found")
            return
        
        # Show edit dialog
        self.show_edit_door_type_dialog(door_type)
        
    def show_edit_door_type_dialog(self, door_type):
        """Show dialog to edit door type"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Door Type: {door_type.name}")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Name entry
        ttk.Label(dialog, text="Door Type Name:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.insert(0, door_type.name)
        name_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(dialog, text="Device Configuration", padding=10)
        config_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        devices = [
            ("INDOOR Smart Card Reader", 'smart_card'),
            ("Finger Print Reader", 'fingerprint'),
            ("Door Sensor", 'door_sensor'),
            ("Magnetic Door Lock", 'magnetic_lock'),
            ("Electric Door Lock", 'electric_lock'),
            ("REX Button", 'rex_button'),
            ("Push Button w/ Indicator", 'push_button'),
            ("Break Glass", 'break_glass'),
            ("Buzzer", 'buzzer'),
            ("Double Door Lock", 'double_door_lock'),
            ("DDL Sensors", 'ddl_sensors')
        ]
        
        entries = {}
        for i, (label, key) in enumerate(devices):
            frame = ttk.Frame(config_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, str(getattr(door_type.config, key)))
            entry.pack(side=tk.RIGHT, padx=5)
            entries[key] = entry
        
        def save_changes():
            try:
                name = name_entry.get().strip()
                if not name:
                    messagebox.showerror("Error", "Please enter a door type name")
                    return
                
                config = {}
                for key, entry in entries.items():
                    value = int(entry.get())
                    if value < 0:
                        raise ValueError(f"{key} cannot be negative")
                    config[key] = value
                
                door_type.name = name
                door_type.update_config(**config)
                
                self.update_door_types_list()
                dialog.destroy()
                messagebox.showinfo("Success", f"Door Type '{name}' updated successfully!")
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save", command=save_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
    def delete_selected_door_type(self):
        """Delete selected door type"""
        selection = self.door_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a door type to delete")
            return
        
        item = self.door_tree.item(selection[0])
        type_id = item['values'][0]
        name = item['values'][1]
        
        if messagebox.askyesno("Confirm", f"Delete Door Type '{name}'?"):
            self.access_door_types = [dt for dt in self.access_door_types if dt.type_id != type_id]
            
            # Reassign IDs
            for i, dt in enumerate(self.access_door_types, 1):
                dt.type_id = i
            
            self.update_door_types_list()
            messagebox.showinfo("Success", f"Door Type '{name}' deleted")
            
    def apply_door_type_to_dc(self):
        """Apply selected door type to create new DC line"""
        selection = self.door_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a door type to apply")
            return
        
        item = self.door_tree.item(selection[0])
        type_id = item['values'][0]
        
        # Find door type
        door_type = next((dt for dt in self.access_door_types if dt.type_id == type_id), None)
        if not door_type:
            messagebox.showerror("Error", "Door type not found")
            return
        
        # Create new DC line
        dc_number = len(self.dc_lines) + 1
        new_dc_line = DCDevice(
            dc_number=dc_number,
            smart_card=door_type.config.smart_card,
            fingerprint=door_type.config.fingerprint,
            door_sensor=door_type.config.door_sensor,
            magnetic_lock=door_type.config.magnetic_lock,
            electric_lock=door_type.config.electric_lock,
            rex_button=door_type.config.rex_button,
            push_button=door_type.config.push_button,
            break_glass=door_type.config.break_glass,
            buzzer=door_type.config.buzzer,
            double_door_lock=door_type.config.double_door_lock,
            ddl_sensors=door_type.config.ddl_sensors
        )
        
        self.dc_lines.append(new_dc_line)
        self.update_dc_lines_list()
        
        messagebox.showinfo("Success", f"DC Line {dc_number} created using '{door_type.name}' configuration!")
        
    def select_controllers_for_dc(self, dc_requirements: Dict) -> Dict:
        """Select controllers for a SINGLE DC line based ONLY on reader count"""
        total_readers = dc_requirements['readers']
        
        # Find optimal controller combination for readers only
        best_solution = None
        best_cost = float('inf')
        
        # Maximum possible of each controller type
        max_kt400 = max(1, total_readers // 4 + 2)
        max_kt2 = max(1, total_readers // 2 + 2)
        max_kt1 = max(1, total_readers + 2)
        
        for kt400 in range(max_kt400 + 1):
            for kt2 in range(max_kt2 + 1):
                for kt1 in range(max_kt1 + 1):
                    readers_provided = (kt400 * 4 + kt2 * 2 + kt1 * 1)
                    cost = (kt400 * 1400 + kt2 * 750 + kt1 * 450)
                    
                    # Must meet or exceed reader requirements
                    if readers_provided >= total_readers:
                        if cost < best_cost:
                            best_cost = cost
                            best_solution = {
                                'kt-400': kt400,
                                'kt-2': kt2,
                                'kt-1': kt1,
                                'readers_provided': readers_provided,
                                'cost': cost,
                                'extra_readers': readers_provided - total_readers
                            }
        
        if best_solution:
            # Calculate inputs/outputs provided by these controllers
            inputs_provided = (best_solution['kt-400'] * 16 + 
                             best_solution['kt-2'] * 8 + 
                             best_solution['kt-1'] * 4)
            
            outputs_provided = (best_solution['kt-400'] * 4 + 
                              best_solution['kt-2'] * 2 + 
                              best_solution['kt-1'] * 2)
            
            return {
                **best_solution,
                'inputs_provided': inputs_provided,
                'outputs_provided': outputs_provided
            }
        
        return None
        
    def calculate_expansion_for_dc(self, dc_inputs: int, dc_outputs: int, 
                                 controller_inputs: int, controller_outputs: int) -> Dict:
        """Calculate expansion modules needed for a SINGLE DC line"""
        # Calculate shortages
        input_shortage = max(0, dc_inputs - controller_inputs)
        output_shortage = max(0, dc_outputs - controller_outputs)
        
        result = ""
        result += f"\nI/O Analysis:\n"
        result += f"  Required: {dc_inputs} inputs, {dc_outputs} outputs\n"
        result += f"  Controllers provide: {controller_inputs} inputs, {controller_outputs} outputs\n"
        result += f"  Shortage: {input_shortage} inputs, {output_shortage} outputs\n"
        
        if input_shortage == 0 and output_shortage == 0:
            result += "  ✅ No expansion modules needed\n"
            return {'modules': [], 'cost': 0, 'result': result}
        
        # Try different module combinations to find the cheapest
        best_solution = {'modules': [], 'cost': float('inf'), 'result': result}
        
        # Try single module that covers both needs
        for module in self.expansion_modules:
            if module['inputs'] >= input_shortage and module['outputs'] >= output_shortage:
                solution = {
                    'modules': [module['name']],
                    'cost': module['cost'],
                    'result': result
                }
                if solution['cost'] < best_solution['cost']:
                    best_solution = solution
        
        # Try combinations of two modules
        for module1 in self.expansion_modules:
            for module2 in self.expansion_modules:
                total_inputs = module1['inputs'] + module2['inputs']
                total_outputs = module1['outputs'] + module2['outputs']
                total_cost = module1['cost'] + module2['cost']
                
                if total_inputs >= input_shortage and total_outputs >= output_shortage:
                    solution = {
                        'modules': [module1['name'], module2['name']],
                        'cost': total_cost,
                        'result': result
                    }
                    if solution['cost'] < best_solution['cost']:
                        best_solution = solution
        
        # If no solution found with up to 2 modules, use specialized modules
        if best_solution['cost'] == float('inf'):
            expansion_modules = []
            expansion_cost = 0
            
            # Add input modules if needed
            if input_shortage > 0:
                # Use in16 modules (16 inputs each)
                in16_needed = int(np.ceil(input_shortage / 16))
                expansion_modules.append(f"in16 (x{in16_needed})")
                expansion_cost += 470 * in16_needed
            
            # Add output modules if needed
            if output_shortage > 0:
                # Use r8 modules (8 outputs each)
                r8_needed = int(np.ceil(output_shortage / 8))
                expansion_modules.append(f"r8 (x{r8_needed})")
                expansion_cost += 470 * r8_needed
            
            best_solution = {
                'modules': expansion_modules,
                'cost': expansion_cost,
                'result': result
            }
        
        best_solution['result'] += f"  Expansion solution: {best_solution['modules']}\n"
        best_solution['result'] += f"  Expansion cost: ${best_solution['cost']}\n"
        
        return best_solution
        
    def calculate_all_kantech(self):
        """Calculate Kantech system for all DC lines"""
        if not self.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured!")
            return
        
        self.kantech_results_text.delete(1.0, tk.END)
        
        all_results = []
        grand_total_cost = 0
        total_kt400 = 0
        total_kt2 = 0
        total_kt1 = 0
        total_expansion_cost = 0
        
        for dc_line in self.dc_lines:
            # Get DC line requirements
            dc_totals = dc_line.calculate_totals()
            
            # Select controllers
            controller_info = self.select_controllers_for_dc(dc_totals)
            
            if not controller_info:
                self.kantech_results_text.insert(tk.END, f"❌ No controller combination found for DC Line {dc_line.dc_number}!\n\n")
                continue
            
            # Calculate expansion
            expansion = self.calculate_expansion_for_dc(
                dc_totals['inputs'],
                dc_totals['outputs'],
                controller_info['inputs_provided'],
                controller_info['outputs_provided']
            )
            
            total_cost = controller_info['cost'] + expansion['cost']
            
            # Add to results
            all_results.append({
                'dc_number': dc_line.dc_number,
                'requirements': dc_totals,
                'controllers': controller_info,
                'expansion': expansion,
                'total_cost': total_cost
            })
            
            # Accumulate totals
            grand_total_cost += total_cost
            total_kt400 += controller_info['kt-400']
            total_kt2 += controller_info['kt-2']
            total_kt1 += controller_info['kt-1']
            total_expansion_cost += expansion['cost']
        
        # Display results
        result_text = "KANTECH SYSTEM CALCULATION - ALL DC LINES\n"
        result_text += "=" * 60 + "\n\n"
        
        for result in all_results:
            req = result['requirements']
            controllers = result['controllers']
            expansion = result['expansion']
            
            result_text += f"DC Line {result['dc_number']}:\n"
            result_text += f"  Requirements: {req['readers']} readers, {req['inputs']} inputs, {req['outputs']} outputs\n"
            result_text += f"  Controllers: kt-400({controllers['kt-400']}), kt-2({controllers['kt-2']}), kt-1({controllers['kt-1']})\n"
            result_text += f"  Controller Cost: ${controllers['cost']}\n"
            result_text += expansion['result']
            result_text += f"  Total Cost for this line: ${result['total_cost']}\n"
            result_text += "-" * 40 + "\n\n"
        
        # Summary
        result_text += "SUMMARY:\n"
        result_text += "=" * 60 + "\n"
        result_text += f"Total Controllers Needed:\n"
        result_text += f"  kt-400: {total_kt400} units  (${total_kt400 * 1400})\n"
        result_text += f"  kt-2:   {total_kt2} units  (${total_kt2 * 750})\n"
        result_text += f"  kt-1:   {total_kt1} units  (${total_kt1 * 450})\n"
        result_text += f"Total controller cost: ${total_kt400 * 1400 + total_kt2 * 750 + total_kt1 * 450}\n"
        result_text += f"Total expansion cost:  ${total_expansion_cost}\n"
        result_text += f"GRAND TOTAL:           ${grand_total_cost}\n"
        
        total_controllers = total_kt400 + total_kt2 + total_kt1
        result_text += f"\nLicense Reference:\n"
        if total_controllers <= 32:
            result_text += f"Total Controllers: {total_controllers} → Kantech Special License\n"
        else:
            result_text += f"Total Controllers: {total_controllers} → Kantech Corporate License\n"
        result_text += f"Note: For redundancy, migrate to Global License + Gateway + Redundancy licenses\n"
        
        self.kantech_results_text.insert(1.0, result_text)
        
        # Store results for export
        self.kantech_all_results = all_results
        self.kantech_grand_total = grand_total_cost
        
    def calculate_selected_kantech(self):
        """Calculate Kantech system for selected DC line"""
        selected = self.selected_dc_line_var.get()
        if not selected or selected == "":
            messagebox.showwarning("Warning", "Please select a DC line")
            return
        
        # Extract DC line number
        try:
            dc_num = int(selected.split(" ")[2])
        except:
            messagebox.showerror("Error", "Invalid DC line selection")
            return
        
        # Find DC line
        dc_line = next((dc for dc in self.dc_lines if dc.dc_number == dc_num), None)
        if not dc_line:
            messagebox.showerror("Error", "DC line not found")
            return
        
        self.kantech_results_text.delete(1.0, tk.END)
        
        # Get DC line requirements
        dc_totals = dc_line.calculate_totals()
        
        result_text = f"KANTECH SYSTEM CALCULATION - DC LINE {dc_num}\n"
        result_text += "=" * 60 + "\n\n"
        result_text += f"Requirements:\n"
        result_text += f"  Readers: {dc_totals['readers']}\n"
        result_text += f"  Inputs:  {dc_totals['inputs']}\n"
        result_text += f"  Outputs: {dc_totals['outputs']}\n\n"
        
        # Select controllers
        controller_info = self.select_controllers_for_dc(dc_totals)
        
        if not controller_info:
            result_text += "❌ No controller combination found for this DC line!\n"
            self.kantech_results_text.insert(1.0, result_text)
            return
        
        result_text += "STEP 1: SELECT CONTROLLERS (Based on readers only)\n"
        result_text += "-" * 40 + "\n"
        result_text += f"Selected Controllers for DC Line {dc_line.dc_number}:\n"
        result_text += f"  kt-400: {controller_info['kt-400']} units\n"
        result_text += f"  kt-2:   {controller_info['kt-2']} units\n"
        result_text += f"  kt-1:   {controller_info['kt-1']} units\n"
        result_text += f"  Controller Cost: ${controller_info['cost']}\n\n"
        
        result_text += f"Controller Capabilities:\n"
        result_text += f"  Readers provided: {controller_info['readers_provided']} ({controller_info['extra_readers']} extra)\n"
        result_text += f"  Inputs provided:  {controller_info['inputs_provided']}\n"
        result_text += f"  Outputs provided: {controller_info['outputs_provided']}\n\n"
        
        # Calculate expansion
        expansion = self.calculate_expansion_for_dc(
            dc_totals['inputs'],
            dc_totals['outputs'],
            controller_info['inputs_provided'],
            controller_info['outputs_provided']
        )
        
        result_text += expansion['result'] + "\n"
        
        total_cost = controller_info['cost'] + expansion['cost']
        
        result_text += "FINAL COST BREAKDOWN:\n"
        result_text += "-" * 40 + "\n"
        result_text += f"  Controllers: ${controller_info['cost']}\n"
        result_text += f"  Expansion:   ${expansion['cost']}\n"
        result_text += f"  TOTAL:       ${total_cost}\n"
        
        self.kantech_results_text.insert(1.0, result_text)
        
        # Store for export
        if not hasattr(self, 'kantech_single_result'):
            self.kantech_single_result = []
        self.kantech_single_result.append({
            'dc_number': dc_line.dc_number,
            'requirements': dc_totals,
            'controllers': controller_info,
            'expansion': expansion,
            'total_cost': total_cost
        })
        
    def calculate_all_gstar(self):
        """Calculate SWH/GSTAR system for all DC lines"""
        if not self.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured!")
            return
        
        self.swh_results_text.delete(1.0, tk.END)
        
        all_results = []
        total_system_readers = 0
        grand_total_cost = 0
        total_controllers = 0
        total_expansion_cost = 0
        total_as0073 = 0
        total_as0074 = 0
        
        controller_counts = {}
        
        for dc_line in self.dc_lines:
            # Get DC line requirements
            dc_totals = dc_line.calculate_totals()
            
            # Select controller
            controller = self.swh_calculator.select_controller_for_readers(dc_totals['readers'])
            
            if not controller:
                self.swh_results_text.insert(tk.END, f"❌ No suitable GSTAR controller found for DC Line {dc_line.dc_number}!\n\n")
                continue
            
            # Calculate expansion
            expansion = self.swh_calculator.calculate_expansion_for_swh(
                dc_totals['inputs'],
                dc_totals['outputs'],
                controller.inputs,
                controller.outputs
            )
            
            total_cost = controller.price + expansion['cost']
            
            # Add to results
            all_results.append({
                'dc_number': dc_line.dc_number,
                'requirements': dc_totals,
                'controller': controller,
                'expansion': expansion,
                'total_cost': total_cost
            })
            
            # Accumulate totals
            total_system_readers += dc_totals['readers']
            grand_total_cost += total_cost
            total_controllers += 1
            total_expansion_cost += expansion['cost']
            total_as0073 += expansion.get('input_modules', 0)
            total_as0074 += expansion.get('output_modules', 0)
            
            # Count controller types
            controller_name = controller.name
            controller_counts[controller_name] = controller_counts.get(controller_name, 0) + 1
        
        # Display results
        result_text = "SWH/GSTAR SYSTEM CALCULATION - ALL DC LINES\n"
        result_text += "=" * 60 + "\n\n"
        
        for result in all_results:
            req = result['requirements']
            controller = result['controller']
            expansion = result['expansion']
            
            result_text += f"DC Line {result['dc_number']}:\n"
            result_text += f"  Requirements: {req['readers']} readers, {req['inputs']} inputs, {req['outputs']} outputs\n"
            result_text += f"  Selected Controller: {controller.name}\n"
            result_text += f"  Controller Price: ${controller.price}\n"
            result_text += f"  ACM Modules included: {controller.number_of_acm}\n"
            result_text += expansion['result']
            result_text += f"  Total Cost for this line: ${result['total_cost']}\n"
            result_text += "-" * 40 + "\n\n"
        
        # Summary
        result_text += "SUMMARY:\n"
        result_text += "=" * 60 + "\n"
        result_text += f"Total GSTAR Controllers: {total_controllers}\n"
        
        # Show detailed controller breakdown
        result_text += f"Controller Breakdown:\n"
        for controller_name, count in controller_counts.items():
            result_text += f"  {controller_name}: {count} units\n"
        
        result_text += f"\nTotal Expansion Modules:\n"
        result_text += f"  AS0073-000 (8-input): {total_as0073} units  (${total_as0073 * 333})\n"
        result_text += f"  AS0074-000 (8-output): {total_as0074} units  (${total_as0074 * 395})\n"
        
        total_controller_cost = sum(r['controller'].price for r in all_results if r['controller'])
        result_text += f"Total controller cost: ${total_controller_cost}\n"
        result_text += f"Total expansion cost:  ${total_expansion_cost}\n"
        result_text += f"GRAND TOTAL HARDWARE:  ${grand_total_cost}\n\n"
        
        result_text += f"SYSTEM SUMMARY:\n"
        result_text += f"  Total DC Lines: {len(self.dc_lines)}\n"
        result_text += f"  Total Controllers Needed: {total_controllers}\n"
        result_text += f"  Controller Types: {', '.join([f'{name}({count})' for name, count in controller_counts.items()])}\n"
        result_text += f"  Total Readers in System: {total_system_readers}\n"
        result_text += f"  Total System Cost: ${grand_total_cost}\n"
        
        self.swh_results_text.insert(1.0, result_text)
        
        # Store results
        self.gstar_results = {
            'all_results': all_results,
            'total_controllers': total_controllers,
            'controller_counts': controller_counts,
            'total_cost': grand_total_cost,
            'total_readers': total_system_readers,
            'total_input_modules': total_as0073,
            'total_output_modules': total_as0074,
            'total_expansion_cost': total_expansion_cost
        }
        
    def calculate_selected_gstar(self):
        """Calculate SWH/GSTAR system for selected DC line"""
        selected = self.selected_dc_line_var.get()
        if not selected or selected == "":
            messagebox.showwarning("Warning", "Please select a DC line")
            return
        
        # Extract DC line number
        try:
            dc_num = int(selected.split(" ")[2])
        except:
            messagebox.showerror("Error", "Invalid DC line selection")
            return
        
        # Find DC line
        dc_line = next((dc for dc in self.dc_lines if dc.dc_number == dc_num), None)
        if not dc_line:
            messagebox.showerror("Error", "DC line not found")
            return
        
        self.swh_results_text.delete(1.0, tk.END)
        
        # Get DC line requirements
        dc_totals = dc_line.calculate_totals()
        
        result_text = f"SWH GSTAR - DC LINE {dc_num} CALCULATION\n"
        result_text += "=" * 60 + "\n\n"
        result_text += f"Requirements:\n"
        result_text += f"  Readers: {dc_totals['readers']}\n"
        result_text += f"  Inputs:  {dc_totals['inputs']}\n"
        result_text += f"  Outputs: {dc_totals['outputs']}\n\n"
        
        # Select controller
        controller = self.swh_calculator.select_controller_for_readers(dc_totals['readers'])
        
        if not controller:
            result_text += f"❌ No suitable GSTAR controller found for {dc_totals['readers']} readers!\n"
            self.swh_results_text.insert(1.0, result_text)
            return
        
        result_text += "STEP 1: SELECT GSTAR CONTROLLER (Based on readers only)\n"
        result_text += "-" * 40 + "\n"
        result_text += f"Selected Controller for DC Line {dc_line.dc_number}:\n"
        result_text += f"  {controller.name}\n"
        result_text += f"  Readers provided: {controller.readers}\n"
        result_text += f"  Controller Cost: ${controller.price}\n"
        result_text += f"  ACM Modules included: {controller.number_of_acm}\n\n"
        
        result_text += f"Controller I/O Capabilities:\n"
        result_text += f"  Inputs provided:  {controller.inputs}\n"
        result_text += f"  Outputs provided: {controller.outputs}\n\n"
        
        # Calculate expansion
        expansion = self.swh_calculator.calculate_expansion_for_swh(
            dc_totals['inputs'],
            dc_totals['outputs'],
            controller.inputs,
            controller.outputs
        )
        
        result_text += expansion['result'] + "\n"
        
        total_cost = controller.price + expansion['cost']
        
        result_text += "FINAL COST BREAKDOWN:\n"
        result_text += "-" * 40 + "\n"
        result_text += f"  Controller: ${controller.price}\n"
        result_text += f"  Expansion:  ${expansion['cost']}\n"
        result_text += f"  ACM Modules: {controller.number_of_acm} included\n"
        result_text += f"  TOTAL:       ${total_cost}\n"
        
        self.swh_results_text.insert(1.0, result_text)
        
        # Store for export
        if not hasattr(self, 'swh_single_result'):
            self.swh_single_result = []
        self.swh_single_result.append({
            'dc_number': dc_line.dc_number,
            'requirements': dc_totals,
            'controller': controller,
            'expansion': expansion,
            'total_cost': total_cost
        })
        
    def calculate_swh_license(self):
        """Calculate SWH license based on total readers"""
        if not hasattr(self, 'gstar_results'):
            messagebox.showwarning("Warning", "Please calculate GSTAR controllers first!")
            return
        
        total_readers = self.gstar_results['total_readers']
        
        result_text = "SWH LICENSE CALCULATION\n"
        result_text += "=" * 60 + "\n\n"
        result_text += f"Total Readers in System: {total_readers}\n\n"
        
        result_text += "Available Licenses:\n"
        result_text += "-" * 40 + "\n"
        
        suitable_licenses = []
        for license_info in self.swh_calculator.swh_licenses:
            max_readers = license_info['max_readers']
            status = "✓ Suitable" if max_readers >= total_readers else "✗ Insufficient"
            result_text += f"  {license_info['name']:<12} Max Readers: {max_readers:<6} {status}\n"
            if max_readers >= total_readers:
                suitable_licenses.append(license_info)
        
        result_text += "\n"
        
        if suitable_licenses:
            suitable_licenses.sort(key=lambda x: x['max_readers'])
            recommended_license = suitable_licenses[0]
            
            result_text += "✅ RECOMMENDED LICENSE:\n"
            result_text += f"   {recommended_license['name']}\n"
            result_text += f"   Supports up to {recommended_license['max_readers']} readers\n"
            result_text += f"   Cost: ${recommended_license['cost']} (included in controller cost)\n"
            
            # Store license result
            self.swh_license_result = {
                'total_readers': total_readers,
                'selected_license': recommended_license['name'],
                'max_readers': recommended_license['max_readers'],
                'cost': recommended_license['cost']
            }
        else:
            result_text += "❌ NO SUITABLE LICENSE FOUND!\n"
            result_text += f"   Your system has {total_readers} readers\n"
            result_text += f"   Maximum available license supports {self.swh_calculator.swh_licenses[-1]['max_readers']} readers\n"
            result_text += f"   Consider splitting the system or contacting SWH for enterprise solutions\n"
        
        self.swh_results_text.insert(1.0, result_text)
        
    def calculate_kantech_license(self):
        """Calculate Kantech license requirements in GUI"""
        if not self.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured!")
            return
        
        self.kantech_license_results_text.delete(1.0, tk.END)
        
        # Calculate total controllers
        total_kt400 = 0
        total_kt2 = 0
        total_kt1 = 0
        
        for dc_line in self.dc_lines:
            dc_totals = dc_line.calculate_totals()
            controller_info = self.select_controllers_for_dc(dc_totals)
            
            if controller_info:
                total_kt400 += controller_info['kt-400']
                total_kt2 += controller_info['kt-2']
                total_kt1 += controller_info['kt-1']
        
        total_controllers = total_kt400 + total_kt2 + total_kt1
        
        result_text = "KANTECH LICENSE CALCULATION\n"
        result_text += "=" * 60 + "\n\n"
        
        result_text += "CONTROLLER SUMMARY:\n"
        result_text += "-" * 40 + "\n"
        result_text += f"Total Controllers Needed: {total_controllers}\n"
        result_text += f"Controller Breakdown:\n"
        result_text += f"  kt-400: {total_kt400} units\n"
        result_text += f"  kt-2:   {total_kt2} units\n"
        result_text += f"  kt-1:   {total_kt1} units\n\n"
        
        use_redundancy = self.redundancy_var.get()
        
        if use_redundancy:
            result_text += "REDUNDANCY CONFIGURATION SELECTED\n"
            result_text += "✅ Required License: Global License\n"
            result_text += "   Reason: Redundancy requires Global License (replaces Special/Corporate)\n"
            result_text += "   Description: Required for ANY redundancy configuration\n\n"
            
            result_text += "ADDITIONAL LICENSES FOR REDUNDANCY:\n"
            result_text += f"   1. Gateway License\n"
            result_text += f"      Cost: ${self.license_info['gateway']['cost']}\n"
            result_text += f"      Description: {self.license_info['gateway']['description']}\n\n"
            
            result_text += f"   2. Redundancy License\n"
            result_text += f"      Cost: ${self.license_info['redundancy']['cost']}\n"
            result_text += f"      Description: {self.license_info['redundancy']['description']}\n\n"
            
            total_license_cost = self.license_info['gateway']['cost'] + self.license_info['redundancy']['cost']
            
            result_text += "LICENSE SUMMARY:\n"
            result_text += "-" * 40 + "\n"
            result_text += f"Total Controllers: {total_controllers}\n"
            result_text += f"Configuration: Redundant\n\n"
            result_text += f"PRIMARY LICENSE:\n"
            result_text += f"  • Global License\n\n"
            result_text += f"ADDITIONAL LICENSES:\n"
            result_text += f"  • Gateway License: ${self.license_info['gateway']['cost']}\n"
            result_text += f"  • Redundancy License: ${self.license_info['redundancy']['cost']}\n\n"
            result_text += f"TOTAL LICENSE COST: ${total_license_cost}\n"
            
        else:
            if total_controllers <= 32:
                license_name = self.license_info['special']['name']
                result_text += f"✅ Required License: {license_name}\n"
                result_text += f"   Reason: {total_controllers} controllers ≤ 32\n"
                result_text += f"   Description: {self.license_info['special']['description']}\n"
            else:
                license_name = self.license_info['corporate']['name']
                result_text += f"✅ Required License: {license_name}\n"
                result_text += f"   Reason: {total_controllers} controllers > 32\n"
                result_text += f"   Description: {self.license_info['corporate']['description']}\n"
            
            result_text += "\nLICENSE SUMMARY:\n"
            result_text += "-" * 40 + "\n"
            result_text += f"Total Controllers: {total_controllers}\n"
            result_text += f"Configuration: Non-Redundant\n\n"
            result_text += f"PRIMARY LICENSE:\n"
            result_text += f"  • {license_name}\n\n"
            result_text += f"ADDITIONAL LICENSES: None\n"
            result_text += f"TOTAL LICENSE COST: $0 (included in controller cost)\n"
        
        self.kantech_license_results_text.insert(1.0, result_text)
        
    def calculate_swh_license_gui(self):
        """Calculate SWH license requirements in GUI"""
        if not self.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured!")
            return
        
        self.swh_license_results_text.delete(1.0, tk.END)
        
        # Calculate total readers
        total_readers = sum(dc.calculate_totals()['readers'] for dc in self.dc_lines)
        
        result_text = "SWH LICENSE CALCULATION\n"
        result_text += "=" * 60 + "\n\n"
        
        result_text += "SYSTEM SUMMARY:\n"
        result_text += "-" * 40 + "\n"
        result_text += f"Total DC Lines: {len(self.dc_lines)}\n"
        result_text += f"Total Readers in System: {total_readers}\n\n"
        
        result_text += "AVAILABLE SWH LICENSES:\n"
        result_text += "-" * 40 + "\n"
        
        suitable_licenses = []
        for license_info in self.swh_calculator.swh_licenses:
            max_readers = license_info['max_readers']
            status = "✓ Suitable" if max_readers >= total_readers else "✗ Insufficient"
            result_text += f"  {license_info['name']:<12} Max Readers: {max_readers:<6} {status}\n"
            if max_readers >= total_readers:
                suitable_licenses.append(license_info)
        
        result_text += "\n"
        
        if suitable_licenses:
            suitable_licenses.sort(key=lambda x: x['max_readers'])
            recommended_license = suitable_licenses[0]
            
            result_text += "✅ RECOMMENDED LICENSE:\n"
            result_text += f"   License Name: {recommended_license['name']}\n"
            result_text += f"   Maximum Readers Supported: {recommended_license['max_readers']}\n"
            result_text += f"   Your System Readers: {total_readers}\n"
            result_text += f"   Available Capacity: {recommended_license['max_readers'] - total_readers} readers\n"
            result_text += f"   License Cost: ${recommended_license['cost']} (included in controller cost)\n\n"
            
            result_text += "LICENSE SUMMARY:\n"
            result_text += "-" * 40 + "\n"
            result_text += f"Total Readers: {total_readers}\n"
            result_text += f"Selected License: {recommended_license['name']}\n"
            result_text += f"Total License Cost: ${recommended_license['cost']}\n"
            
            # Store license result
            self.swh_license_result = {
                'total_readers': total_readers,
                'selected_license': recommended_license['name'],
                'max_readers': recommended_license['max_readers'],
                'cost': recommended_license['cost']
            }
        else:
            result_text += "❌ NO SUITABLE LICENSE FOUND!\n"
            result_text += f"   Your system has {total_readers} readers\n"
            result_text += f"   Maximum available license supports {self.swh_calculator.swh_licenses[-1]['max_readers']} readers\n"
            result_text += f"   Consider splitting the system or contacting SWH for enterprise solutions\n"
        
        self.swh_license_results_text.insert(1.0, result_text)
        
    def export_kantech_results(self):
        """Export Kantech results to CSV"""
        if not hasattr(self, 'kantech_all_results'):
            messagebox.showwarning("Warning", "Please run Kantech calculations first!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="kantech_results.csv"
        )
        
        if filename:
            try:
                data = []
                
                for result in self.kantech_all_results:
                    dc_num = result['dc_number']
                    req = result['requirements']
                    controllers = result['controllers']
                    expansion = result['expansion']
                    total_cost = result['total_cost']
                    
                    # DC line requirements
                    data.append({
                        'DC_Line': dc_num,
                        'Type': 'Requirements',
                        'Readers': req['readers'],
                        'Inputs': req['inputs'],
                        'Outputs': req['outputs'],
                        'KT400': '',
                        'KT2': '',
                        'KT1': '',
                        'Controller_Cost': '',
                        'Expansion_Modules': '',
                        'Expansion_Cost': '',
                        'Total_Cost': ''
                    })
                    
                    # Controllers
                    data.append({
                        'DC_Line': dc_num,
                        'Type': 'Controllers',
                        'Readers': controllers['readers_provided'],
                        'Inputs': controllers['inputs_provided'],
                        'Outputs': controllers['outputs_provided'],
                        'KT400': controllers['kt-400'],
                        'KT2': controllers['kt-2'],
                        'KT1': controllers['kt-1'],
                        'Controller_Cost': controllers['cost'],
                        'Expansion_Modules': '',
                        'Expansion_Cost': '',
                        'Total_Cost': ''
                    })
                    
                    # Expansion
                    if expansion['modules']:
                        modules_str = ', '.join(expansion['modules'])
                        data.append({
                            'DC_Line': dc_num,
                            'Type': 'Expansion',
                            'Readers': '',
                            'Inputs': '',
                            'Outputs': '',
                            'KT400': '',
                            'KT2': '',
                            'KT1': '',
                            'Controller_Cost': '',
                            'Expansion_Modules': modules_str,
                            'Expansion_Cost': expansion['cost'],
                            'Total_Cost': ''
                        })
                    else:
                        data.append({
                            'DC_Line': dc_num,
                            'Type': 'Expansion',
                            'Readers': '',
                            'Inputs': '',
                            'Outputs': '',
                            'KT400': '',
                            'KT2': '',
                            'KT1': '',
                            'Controller_Cost': '',
                            'Expansion_Modules': 'None',
                            'Expansion_Cost': 0,
                            'Total_Cost': ''
                        })
                    
                    # Total for this DC line
                    data.append({
                        'DC_Line': dc_num,
                        'Type': 'TOTAL',
                        'Readers': '',
                        'Inputs': '',
                        'Outputs': '',
                        'KT400': '',
                        'KT2': '',
                        'KT1': '',
                        'Controller_Cost': '',
                        'Expansion_Modules': '',
                        'Expansion_Cost': '',
                        'Total_Cost': total_cost
                    })
                    
                    # Empty row
                    data.append({
                        'DC_Line': '',
                        'Type': '',
                        'Readers': '',
                        'Inputs': '',
                        'Outputs': '',
                        'KT400': '',
                        'KT2': '',
                        'KT1': '',
                        'Controller_Cost': '',
                        'Expansion_Modules': '',
                        'Expansion_Cost': '',
                        'Total_Cost': ''
                    })
                
                # Add grand total
                total_kt400 = sum(r['controllers']['kt-400'] for r in self.kantech_all_results)
                total_kt2 = sum(r['controllers']['kt-2'] for r in self.kantech_all_results)
                total_kt1 = sum(r['controllers']['kt-1'] for r in self.kantech_all_results)
                total_controller_cost = sum(r['controllers']['cost'] for r in self.kantech_all_results)
                total_expansion_cost = sum(r['expansion']['cost'] for r in self.kantech_all_results)
                
                data.append({
                    'DC_Line': 'GRAND TOTAL',
                    'Type': 'Summary',
                    'Readers': '',
                    'Inputs': '',
                    'Outputs': '',
                    'KT400': total_kt400,
                    'KT2': total_kt2,
                    'KT1': total_kt1,
                    'Controller_Cost': total_controller_cost,
                    'Expansion_Modules': '',
                    'Expansion_Cost': total_expansion_cost,
                    'Total_Cost': self.kantech_grand_total
                })
                
                df = pd.DataFrame(data)
                df.to_csv(filename, index=False)
                
                self.export_status.config(text=f"✅ Results exported to {filename}")
                messagebox.showinfo("Success", f"Results exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
                
    def export_gstar_results(self):
        """Export SWH/GSTAR results to CSV"""
        if not hasattr(self, 'gstar_results'):
            messagebox.showwarning("Warning", "Please run SWH/GSTAR calculations first!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="gstar_results.csv"
        )
        
        if filename:
            try:
                data = []
                
                # Add GSTAR controller results
                data.append(["GSTAR/SWH SYSTEM RESULTS", "", "", "", "", "", "", ""])
                data.append(["DC Line", "Readers", "Inputs", "Outputs", "Selected Controller", "Price", "Expansion Modules", "Total Cost"])
                
                for result in self.gstar_results['all_results']:
                    requirements = result['requirements']
                    controller = result['controller']
                    expansion = result['expansion']
                    total_cost = result['total_cost']
                    
                    if controller:
                        expansion_str = ", ".join(expansion['modules']) if expansion['modules'] else "None"
                        data.append([
                            result['dc_number'],
                            requirements['readers'],
                            requirements['inputs'],
                            requirements['outputs'],
                            controller.name,
                            controller.price,
                            expansion_str,
                            total_cost
                        ])
                    else:
                        data.append([
                            result['dc_number'],
                            requirements['readers'],
                            requirements['inputs'],
                            requirements['outputs'],
                            "No suitable controller",
                            "N/A",
                            "N/A",
                            "N/A"
                        ])
                
                # Add summary
                data.append(["", "", "", "", "", "", "", ""])
                data.append(["SUMMARY", "", "", "", "", "", "", ""])
                data.append(["Total Controllers", self.gstar_results['total_controllers'], "", "", "Total Cost", self.gstar_results['total_cost'], "", ""])
                
                # Add controller breakdown
                if 'controller_counts' in self.gstar_results:
                    for controller_name, count in self.gstar_results['controller_counts'].items():
                        data.append(["", f"{controller_name}: {count} units", "", "", "", "", "", ""])
                
                data.append(["Total Readers", self.gstar_results['total_readers'], "", "", "Total Expansion Cost", self.gstar_results['total_expansion_cost'], "", ""])
                data.append(["AS0073-000 Modules", self.gstar_results['total_input_modules'], "", "", "AS0074-000 Modules", self.gstar_results['total_output_modules'], "", ""])
                
                # Add license information if available
                if hasattr(self, 'swh_license_result'):
                    data.append(["", "", "", "", "", "", "", ""])
                    data.append(["LICENSE INFORMATION", "", "", "", "", "", "", ""])
                    data.append([
                        "Total Readers",
                        self.swh_license_result['total_readers'],
                        "",
                        "",
                        "Selected License",
                        self.swh_license_result['selected_license'],
                        f"Max Readers: {self.swh_license_result['max_readers']}",
                        ""
                    ])
                    data.append(["License Cost", self.swh_license_result['cost'], "", "", "", "", "", ""])
                
                df = pd.DataFrame(data)
                df.to_csv(filename, index=False, header=False)
                
                self.export_status.config(text=f"✅ Results exported to {filename}")
                messagebox.showinfo("Success", f"Results exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
                
    def export_system_summary(self):
        """Export system summary to CSV"""
        if not self.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="system_summary.csv"
        )
        
        if filename:
            try:
                data = []
                
                # DC lines summary
                data.append(["DC LINES SUMMARY", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
                data.append(["DC", "Smart Card", "Fingerprint", "Door Sensor", "Mag Lock", "Elec Lock", 
                           "REX", "Push Button", "Break Glass", "Buzzer", "DDL", "DDL Sensors",
                           "Readers", "Inputs", "Outputs"])
                
                for dc in self.dc_lines:
                    totals = dc.calculate_totals()
                    data.append([
                        dc.dc_number,
                        dc.smart_card,
                        dc.fingerprint,
                        dc.door_sensor,
                        dc.magnetic_lock,
                        dc.electric_lock,
                        dc.rex_button,
                        dc.push_button,
                        dc.break_glass,
                        dc.buzzer,
                        dc.double_door_lock,
                        dc.ddl_sensors,
                        totals['readers'],
                        totals['inputs'],
                        totals['outputs']
                    ])
                
                # Totals
                total_smart_card = sum(dc.smart_card for dc in self.dc_lines)
                total_fingerprint = sum(dc.fingerprint for dc in self.dc_lines)
                total_door_sensor = sum(dc.door_sensor for dc in self.dc_lines)
                total_magnetic_lock = sum(dc.magnetic_lock for dc in self.dc_lines)
                total_electric_lock = sum(dc.electric_lock for dc in self.dc_lines)
                total_rex_button = sum(dc.rex_button for dc in self.dc_lines)
                total_push_button = sum(dc.push_button for dc in self.dc_lines)
                total_break_glass = sum(dc.break_glass for dc in self.dc_lines)
                total_buzzer = sum(dc.buzzer for dc in self.dc_lines)
                total_ddl = sum(dc.double_door_lock for dc in self.dc_lines)
                total_ddl_sensors = sum(dc.ddl_sensors for dc in self.dc_lines)
                total_readers = sum(dc.calculate_totals()['readers'] for dc in self.dc_lines)
                total_inputs = sum(dc.calculate_totals()['inputs'] for dc in self.dc_lines)
                total_outputs = sum(dc.calculate_totals()['outputs'] for dc in self.dc_lines)
                
                data.append(["TOTAL", 
                           total_smart_card, total_fingerprint, total_door_sensor,
                           total_magnetic_lock, total_electric_lock, total_rex_button,
                           total_push_button, total_break_glass, total_buzzer,
                           total_ddl, total_ddl_sensors, total_readers, total_inputs, total_outputs])
                
                # Door types summary
                data.append(["", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
                data.append(["DOOR TYPES SUMMARY", "", "", "", "", "", "", ""])
                data.append(["ID", "Name", "Smart Card", "Fingerprint", "Door Sensor", "Readers", "Inputs", "Outputs"])
                
                for dt in self.access_door_types:
                    totals = dt.get_totals()
                    data.append([
                        dt.type_id,
                        dt.name,
                        dt.config.smart_card,
                        dt.config.fingerprint,
                        dt.config.door_sensor,
                        totals['readers'],
                        totals['inputs'],
                        totals['outputs']
                    ])
                
                df = pd.DataFrame(data)
                df.to_csv(filename, index=False, header=False)
                
                self.export_status.config(text=f"✅ System summary exported to {filename}")
                messagebox.showinfo("Success", f"System summary exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
                
    def show_gstar_calculation(self):
        """Switch to SWH calculation tab"""
        self.notebook.select(self.calculation_tab)
        calc_notebook = self.calculation_tab.winfo_children()[0]
        calc_notebook.select(self.swh_calc_tab)
        
    def run(self):
        """Run the GUI application"""
        # Initial updates
        self.update_dc_lines_list()
        self.update_door_types_list()
        
        self.root.mainloop()


def main():
    """Main function to run the application"""
    app = KantechDCCalculatorGUI()
    app.run()


if __name__ == "__main__":
    main()
