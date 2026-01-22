import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import json
import os

# Theme configuration
THEMES = {
    "light": {
        "bg": "#ffffff",
        "fg": "#000000",
        "primary": "#2c3e50",
        "secondary": "#3498db",
        "accent": "#e74c3c",
        "success": "#27ae60",
        "warning": "#f39c12",
        "tree_bg": "#f8f9fa",
        "tree_fg": "#212529",
        "tree_selected": "#3498db",
        "button_bg": "#3498db",
        "button_fg": "#ffffff",
        "text_bg": "#ffffff",
        "text_fg": "#000000",
        "border": "#dee2e6",
        "tab_bg": "#f8f9fa",
        "tab_selected": "#ffffff"
    },
    "dark": {
        "bg": "#1a1a1a",
        "fg": "#ffffff",
        "primary": "#34495e",
        "secondary": "#2980b9",
        "accent": "#c0392b",
        "success": "#229954",
        "warning": "#d68910",
        "tree_bg": "#2c3e50",
        "tree_fg": "#ecf0f1",
        "tree_selected": "#2980b9",
        "button_bg": "#2980b9",
        "button_fg": "#ffffff",
        "text_bg": "#2c3e50",
        "text_fg": "#ecf0f1",
        "border": "#34495e",
        "tab_bg": "#2c3e50",
        "tab_selected": "#34495e"
    }
}

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
    double_door_lock: int = 0
    ddl_sensors: int = 0
    
    def calculate_totals(self):
        """Calculate readers, inputs, outputs for this DC line"""
        readers = self.smart_card + self.fingerprint
        inputs = (self.door_sensor + self.rex_button + self.push_button + 
                 self.break_glass + self.buzzer + self.magnetic_lock + 
                 self.ddl_sensors + self.double_door_lock)
        outputs = (self.magnetic_lock + self.electric_lock + 
                  self.ddl_sensors + self.double_door_lock)
        return {'readers': readers, 'inputs': inputs, 'outputs': outputs}


class GSTARController:
    """GSTAR controller information"""
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
    """Calculator for SWH GSTAR controllers"""
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
        
        self.swh_expansion_modules = [
            {'name': 'AS0073-000', 'inputs': 8, 'outputs': 0, 'cost': 333},
            {'name': 'AS0074-000', 'inputs': 0, 'outputs': 8, 'cost': 395}
        ]
    
    def select_controller_for_readers(self, required_readers):
        suitable_controllers = []
        for controller in self.gstar_controllers:
            if controller.can_handle_readers(required_readers):
                suitable_controllers.append(controller)
        
        if not suitable_controllers:
            return None
        
        suitable_controllers.sort(key=lambda x: x.price)
        return suitable_controllers[0]


class KantechDCCalculator:
    def __init__(self):
        self.dc_lines: List[DCDevice] = []
        self.swh_calculator = SWHControllerCalculator()
        
        self.controllers = [
            {'name': 'kt-1', 'readers': 1, 'cost': 450, 'inputs': 4, 'outputs': 2},
            {'name': 'kt-2', 'readers': 2, 'cost': 750, 'inputs': 8, 'outputs': 2},
            {'name': 'kt-400', 'readers': 4, 'cost': 1400, 'inputs': 16, 'outputs': 4}
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


class ModernButton(ttk.Button):
    """Custom styled button"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(style='Modern.TButton')


class DCApp:
    def __init__(self, root):
        self.root = root
        self.calculator = KantechDCCalculator()
        self.current_theme = "light"
        self.setup_styles()
        self.setup_ui()
        
    def setup_styles(self):
        """Setup ttk styles for both themes"""
        self.style = ttk.Style()
        
        # Configure modern button style
        self.style.configure('Modern.TButton',
                           padding=10,
                           relief="flat",
                           font=('Segoe UI', 10))
        
        # Configure Treeview style
        self.style.configure('Modern.Treeview',
                           rowheight=25,
                           fieldbackground=THEMES[self.current_theme]["tree_bg"])
        self.style.configure('Modern.Treeview.Heading',
                           font=('Segoe UI', 10, 'bold'))
        
        # Configure Notebook style
        self.style.configure('Modern.TNotebook',
                           background=THEMES[self.current_theme]["tab_bg"])
        self.style.configure('Modern.TNotebook.Tab',
                           padding=[15, 5],
                           font=('Segoe UI', 10))
        
        # Configure LabelFrame style
        self.style.configure('Modern.TLabelframe',
                           background=THEMES[self.current_theme]["bg"],
                           foreground=THEMES[self.current_theme]["fg"])
        self.style.configure('Modern.TLabelframe.Label',
                           font=('Segoe UI', 10, 'bold'),
                           background=THEMES[self.current_theme]["bg"],
                           foreground=THEMES[self.current_theme]["fg"])
    
    def apply_theme(self, theme_name):
        """Apply the selected theme to all widgets"""
        self.current_theme = theme_name
        theme = THEMES[theme_name]
        
        # Apply to root window
        self.root.configure(bg=theme["bg"])
        
        # Apply theme to all widgets
        self.apply_widget_theme(self.root, theme)
        
        # Update specific widget colors
        if hasattr(self, 'dc_tree'):
            self.dc_tree.configure(bg=theme["tree_bg"], fg=theme["tree_fg"])
        
        if hasattr(self, 'kantech_results'):
            self.kantech_results.configure(bg=theme["text_bg"], fg=theme["text_fg"])
        
        if hasattr(self, 'swh_results'):
            self.swh_results.configure(bg=theme["text_bg"], fg=theme["text_fg"])
        
        if hasattr(self, 'license_results'):
            self.license_results.configure(bg=theme["text_bg"], fg=theme["text_fg"])
        
        if hasattr(self, 'summary_text'):
            self.summary_text.configure(bg=theme["text_bg"], fg=theme["text_fg"])
        
        # Update status bar
        if hasattr(self, 'status_bar'):
            self.status_bar.configure(background=theme["primary"], foreground=theme["fg"])
    
    def apply_widget_theme(self, widget, theme):
        """Recursively apply theme to all widgets"""
        try:
            widget_type = widget.winfo_class()
            
            if widget_type in ('TFrame', 'TLabelframe'):
                widget.configure(background=theme["bg"])
            elif widget_type == 'TLabel':
                widget.configure(background=theme["bg"], foreground=theme["fg"])
            elif widget_type == 'TButton':
                widget.configure(style='Modern.TButton')
            elif widget_type == 'TRadiobutton':
                widget.configure(background=theme["bg"], foreground=theme["fg"])
            elif widget_type == 'TNotebook':
                widget.configure(style='Modern.TNotebook')
            
            # Apply to children
            for child in widget.winfo_children():
                self.apply_widget_theme(child, theme)
        except:
            pass
    
    def setup_ui(self):
        self.root.title("Access Control System Calculator")
        self.root.geometry("1400x800")
        self.root.minsize(1200, 700)
        
        # Configure grid weights for main window
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        
        # Header frame with title and theme selector
        header_frame = ttk.Frame(main_container)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(header_frame, 
                               text="Access Control System Calculator", 
                               font=('Segoe UI', 20, 'bold'))
        title_label.grid(row=0, column=0, sticky="w")
        
        # Theme selector
        theme_frame = ttk.Frame(header_frame)
        theme_frame.grid(row=0, column=1, sticky="e")
        
        ttk.Label(theme_frame, text="Theme:", font=('Segoe UI', 10)).pack(side="left", padx=(0, 5))
        self.theme_var = tk.StringVar(value="light")
        theme_combo = ttk.Combobox(theme_frame, 
                                  textvariable=self.theme_var, 
                                  values=["light", "dark"], 
                                  state="readonly",
                                  width=10)
        theme_combo.pack(side="left")
        theme_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_theme(self.theme_var.get()))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container, style='Modern.TNotebook')
        self.notebook.grid(row=1, column=0, sticky="nsew")
        
        # Create tabs
        self.setup_dc_tab()
        self.setup_kantech_tab()
        self.setup_swh_tab()
        self.setup_license_tab()
        self.setup_summary_tab()
        
        # Status bar
        status_container = ttk.Frame(main_container)
        status_container.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(status_container, 
                                   textvariable=self.status_var, 
                                   relief='flat',
                                   anchor='w',
                                   padding=5,
                                   font=('Segoe UI', 9))
        self.status_bar.pack(fill='x')
        
        # Apply initial theme
        self.apply_theme("light")
    
    def setup_dc_tab(self):
        """Setup DC Line Configuration tab"""
        self.dc_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dc_tab, text="DC Line Configuration")
        
        # Top frame for controls
        control_frame = ttk.LabelFrame(self.dc_tab, text="DC Line Controls", padding=15)
        control_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        # Control buttons with icons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill='x')
        
        button_data = [
            ("➕ Add New DC Line", self.add_dc_line),
            ("✏️ Edit Selected", self.edit_dc_line),
            ("🗑️ Delete Selected", self.delete_dc_line),
            ("🗑️ Clear All", self.clear_all_dc)
        ]
        
        for text, command in button_data:
            btn = ModernButton(button_frame, text=text, command=command)
            btn.pack(side='left', padx=5, pady=5, fill='x', expand=True)
        
        # DC Lines treeview frame
        tree_frame = ttk.LabelFrame(self.dc_tab, text="DC Lines Configuration", padding=10)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create scrollable frame for treeview
        tree_container = ttk.Frame(tree_frame)
        tree_container.pack(fill='both', expand=True)
        
        # DC Lines treeview
        columns = ("DC#", "Smart Card", "Fingerprint", "Door Sensor", "Mag Lock", 
                  "Elec Lock", "REX", "Push Button", "Break Glass", "Buzzer", 
                  "DDL", "DDL Sensors", "Readers", "Inputs", "Outputs")
        
        self.dc_tree = ttk.Treeview(tree_container, 
                                   columns=columns, 
                                   show='headings', 
                                   height=12,
                                   style='Modern.Treeview')
        
        # Configure columns
        col_widths = [45, 80, 80, 80, 80, 80, 45, 90, 80, 55, 45, 85, 65, 55, 65]
        for idx, (col, width) in enumerate(zip(columns, col_widths)):
            self.dc_tree.heading(col, text=col)
            self.dc_tree.column(col, width=width, anchor='center')
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(tree_container, orient='vertical', command=self.dc_tree.yview)
        x_scrollbar = ttk.Scrollbar(tree_container, orient='horizontal', command=self.dc_tree.xview)
        self.dc_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Grid layout for tree and scrollbars
        self.dc_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Info frame
        info_frame = ttk.Frame(self.dc_tab)
        info_frame.pack(fill='x', padx=10, pady=(5, 10))
        
        self.dc_info = tk.StringVar()
        self.dc_info.set("No DC lines configured")
        info_label = ttk.Label(info_frame, 
                              textvariable=self.dc_info, 
                              font=('Segoe UI', 10),
                              foreground=THEMES[self.current_theme]["accent"])
        info_label.pack(anchor='w')
    
    def setup_kantech_tab(self):
        """Setup Kantech Calculation tab"""
        self.kantech_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.kantech_tab, text="Kantech System")
        
        # Configure grid
        self.kantech_tab.grid_columnconfigure(0, weight=3)
        self.kantech_tab.grid_columnconfigure(1, weight=1)
        self.kantech_tab.grid_rowconfigure(0, weight=1)
        
        # Left frame for calculations
        left_frame = ttk.LabelFrame(self.kantech_tab, text="Calculations", padding=15)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_rowconfigure(2, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        ttk.Label(left_frame, text="KANTECH SYSTEM CALCULATIONS", 
                 font=('Segoe UI', 12, 'bold')).grid(row=0, column=0, pady=(0, 15), sticky="w")
        
        # Buttons frame
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=1, column=0, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        ModernButton(button_frame, text="📊 Calculate Selected DC Line", 
                    command=self.calc_kantech_single).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ModernButton(button_frame, text="📈 Calculate All DC Lines", 
                    command=self.calc_kantech_all).grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        # Results frame
        results_frame = ttk.LabelFrame(left_frame, text="Calculation Results", padding=10)
        results_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        self.kantech_results = tk.Text(results_frame, height=20, width=50, 
                                      font=('Consolas', 10), wrap='word')
        self.kantech_results.grid(row=0, column=0, sticky="nsew")
        
        # Add scrollbar to results
        results_scrollbar = ttk.Scrollbar(results_frame, orient='vertical', command=self.kantech_results.yview)
        self.kantech_results.configure(yscrollcommand=results_scrollbar.set)
        results_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Right frame for summary
        right_frame = ttk.LabelFrame(self.kantech_tab, text="Controller Information", padding=15)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(right_frame, text="KANTECH CONTROLLERS", 
                 font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, pady=(0, 10), sticky="w")
        
        controllers_text = """╔══════════════════════════════════╗
║ KANTECH CONTROLLERS             ║
╠══════════════════════════════════╣
║ kt-1:                           ║
║   • 1 reader, 4 inputs, 2 outputs║
║   • Cost: $450                  ║
║                                 ║
║ kt-2:                           ║
║   • 2 readers, 8 inputs, 2 outputs║
║   • Cost: $750                  ║
║                                 ║
║ kt-400:                         ║
║   • 4 readers, 16 inputs, 4 outputs║
║   • Cost: $1400                 ║
╠══════════════════════════════════╣
║ EXPANSION MODULES:              ║
║                                 ║
║ • inout16 series: $447 each     ║
║ • in16: 16 inputs - $470        ║
║ • r8: 8 outputs - $470          ║
╠══════════════════════════════════╣
║ SELECTION METHOD:               ║
║                                 ║
║ Based on readers only, then add ║
║ expansion modules for I/O needs.║
╚══════════════════════════════════╝"""
        
        controller_info = tk.Text(right_frame, height=30, width=40, 
                                 font=('Consolas', 9), wrap='word')
        controller_info.insert('1.0', controllers_text)
        controller_info.config(state='disabled')
        controller_info.grid(row=1, column=0, sticky="nsew")
    
    def setup_swh_tab(self):
        """Setup SWH GSTAR Calculation tab"""
        self.swh_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.swh_tab, text="SWH GSTAR System")
        
        # Configure grid
        self.swh_tab.grid_columnconfigure(0, weight=3)
        self.swh_tab.grid_columnconfigure(1, weight=1)
        self.swh_tab.grid_rowconfigure(0, weight=1)
        
        # Left frame for calculations
        left_frame = ttk.LabelFrame(self.swh_tab, text="Calculations", padding=15)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_rowconfigure(2, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        ttk.Label(left_frame, text="SWH GSTAR CALCULATIONS", 
                 font=('Segoe UI', 12, 'bold')).grid(row=0, column=0, pady=(0, 15), sticky="w")
        
        # Buttons frame
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=1, column=0, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1)
        
        ModernButton(button_frame, text="📊 Calculate Selected", 
                    command=self.calc_swh_single).grid(row=0, column=0, padx=(0, 3), sticky="ew")
        ModernButton(button_frame, text="📈 Calculate All", 
                    command=self.calc_swh_all).grid(row=0, column=1, padx=3, sticky="ew")
        ModernButton(button_frame, text="📋 Calculate License", 
                    command=self.calc_swh_license).grid(row=0, column=2, padx=(3, 0), sticky="ew")
        
        # Results frame
        results_frame = ttk.LabelFrame(left_frame, text="Calculation Results", padding=10)
        results_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        self.swh_results = tk.Text(results_frame, height=20, width=50, 
                                  font=('Consolas', 10), wrap='word')
        self.swh_results.grid(row=0, column=0, sticky="nsew")
        
        # Add scrollbar to results
        results_scrollbar = ttk.Scrollbar(results_frame, orient='vertical', command=self.swh_results.yview)
        self.swh_results.configure(yscrollcommand=results_scrollbar.set)
        results_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Right frame for summary
        right_frame = ttk.LabelFrame(self.swh_tab, text="GSTAR Information", padding=15)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(right_frame, text="GSTAR CONTROLLERS", 
                 font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, pady=(0, 10), sticky="w")
        
        gstar_text = """╔══════════════════════════════════╗
║ GSTAR CONTROLLERS               ║
╠══════════════════════════════════╣
║ GSTAR004 (4R):                  ║
║   • 4 readers, 8I/4O           ║
║   • $1,395                      ║
║                                 ║
║ GSTAR004 (8R):                  ║
║   • 8 readers, 16I/12O         ║
║   • $2,123                      ║
║                                 ║
║ GSTAR008:                       ║
║   • 8 readers, 24I/8O          ║
║   • $3,125 (1 ACM)              ║
║                                 ║
║ GSTAR016:                       ║
║   • 16 readers, 48I/16O        ║
║   • $4,166 (2 ACM)              ║
║                                 ║
║ GSTAR016 (24R):                 ║
║   • 24 readers, 72I/24O        ║
║   • $5,166 (3 ACM)              ║
║                                 ║
║ GSTAR016 (32R):                 ║
║   • 32 readers, 96I/32O        ║
║   • $6,166 (4 ACM)              ║
╠══════════════════════════════════╣
║ EXPANSION MODULES:              ║
║                                 ║
║ • AS0073-000: 8 inputs - $333   ║
║ • AS0074-000: 8 outputs - $395  ║
╚══════════════════════════════════╝"""
        
        gstar_info = tk.Text(right_frame, height=30, width=40, 
                            font=('Consolas', 9), wrap='word')
        gstar_info.insert('1.0', gstar_text)
        gstar_info.config(state='disabled')
        gstar_info.grid(row=1, column=0, sticky="nsew")
    
    def setup_license_tab(self):
        """Setup License Calculation tab"""
        self.license_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.license_tab, text="License")
        
        # Main frame with padding
        main_frame = ttk.Frame(self.license_tab, padding=20)
        main_frame.pack(fill='both', expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        ttk.Label(title_frame, text="📋 LICENSE CALCULATION", 
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(title_frame, text="Configure system requirements and calculate license needs",
                 font=('Segoe UI', 10)).pack(anchor='w')
        
        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="System Configuration", padding=15)
        config_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 20))
        config_frame.grid_columnconfigure(0, weight=1)
        config_frame.grid_columnconfigure(1, weight=1)
        
        # Redundancy selection
        redundancy_frame = ttk.Frame(config_frame)
        redundancy_frame.grid(row=0, column=0, sticky="w", padx=10, pady=10)
        
        ttk.Label(redundancy_frame, text="System Type:", 
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        self.redundancy_var = tk.BooleanVar(value=False)
        ttk.Radiobutton(redundancy_frame, text="🏢 Non-Redundant System", 
                       variable=self.redundancy_var, value=False,
                       style='TRadiobutton').pack(anchor='w', pady=2)
        ttk.Radiobutton(redundancy_frame, text="🔄 Redundant System", 
                       variable=self.redundancy_var, value=True,
                       style='TRadiobutton').pack(anchor='w', pady=2)
        
        # Info panel
        info_frame = ttk.Frame(config_frame)
        info_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        info_text = """📋 LICENSE RULES:
────────────────────
1. NON-REDUNDANT SYSTEMS:
   • ≤ 32 controllers → Kantech Special License
   • > 32 controllers → Kantech Corporate License

2. REDUNDANT SYSTEMS:
   • Migrate to Global License (replaces Special/Corporate)
   • Add Gateway License (for server communication)
   • Add Redundancy License (for failover capability)

💡 Note: License costs are included in controller costs
        for non-redundant systems."""
        
        info_label = ttk.Label(info_frame, text=info_text, justify='left',
                              font=('Consolas', 9))
        info_label.pack(anchor='w')
        
        # Calculate button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        
        ModernButton(button_frame, text="🧮 Calculate License Requirements", 
                    command=self.calc_license).pack(pady=10)
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding=10)
        results_frame.grid(row=3, column=0, sticky="nsew")
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        self.license_results = tk.Text(results_frame, height=15, 
                                      font=('Consolas', 10), wrap='word')
        self.license_results.grid(row=0, column=0, sticky="nsew")
        
        # Add scrollbar to results
        results_scrollbar = ttk.Scrollbar(results_frame, orient='vertical', 
                                         command=self.license_results.yview)
        self.license_results.configure(yscrollcommand=results_scrollbar.set)
        results_scrollbar.grid(row=0, column=1, sticky="ns")
    
    def setup_summary_tab(self):
        """Setup Summary and Export tab"""
        self.summary_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_tab, text="Summary & Export")
        
        # Main frame
        main_frame = ttk.Frame(self.summary_tab, padding=20)
        main_frame.pack(fill='both', expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        ttk.Label(title_frame, text="📊 SYSTEM SUMMARY", 
                 font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        ttk.Label(title_frame, text="View complete system summary and export results",
                 font=('Segoe UI', 10)).pack(anchor='w')
        
        # Summary text area
        summary_frame = ttk.LabelFrame(main_frame, text="System Summary", padding=10)
        summary_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 20))
        summary_frame.grid_rowconfigure(0, weight=1)
        summary_frame.grid_columnconfigure(0, weight=1)
        
        self.summary_text = tk.Text(summary_frame, height=20, 
                                   font=('Consolas', 10), wrap='word')
        self.summary_text.grid(row=0, column=0, sticky="nsew")
        
        # Add scrollbar to summary
        summary_scrollbar = ttk.Scrollbar(summary_frame, orient='vertical', 
                                         command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scrollbar.set)
        summary_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Export buttons
        export_frame = ttk.LabelFrame(main_frame, text="Export Options", padding=15)
        export_frame.grid(row=2, column=0, sticky="ew")
        
        # Button grid
        button_grid = ttk.Frame(export_frame)
        button_grid.pack(fill='x')
        
        ModernButton(button_grid, text="🔄 Update Summary", 
                    command=self.update_summary).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ModernButton(button_grid, text="💾 Export Kantech Results", 
                    command=self.export_kantech).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ModernButton(button_grid, text="💾 Export GSTAR Results", 
                    command=self.export_gstar).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        ModernButton(button_grid, text="📦 Export All Data", 
                    command=self.export_all).grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        # Configure button grid columns
        for i in range(4):
            button_grid.grid_columnconfigure(i, weight=1)
    
    # All other methods remain EXACTLY THE SAME from here on...
    # Only the UI setup methods were modified above
    # The following methods are unchanged from the original code:
    
    def add_dc_line(self):
        """Open dialog to add new DC line"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add DC Line")
        dialog.geometry("400x550")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Apply theme to dialog
        self.apply_widget_theme(dialog, THEMES[self.current_theme])
        
        # Title
        ttk.Label(dialog, text="Add New DC Line", 
                 font=('Segoe UI', 12, 'bold')).pack(pady=(10, 20))
        
        # Device entries frame
        entries_frame = ttk.Frame(dialog)
        entries_frame.pack(fill='both', expand=True, padx=20)
        
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
        for idx, (label, key) in enumerate(devices):
            frame = ttk.Frame(entries_frame)
            frame.pack(fill='x', pady=2)
            
            ttk.Label(frame, text=label, width=30, anchor='w').pack(side='left', padx=(0, 10))
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, '0')
            entry.pack(side='right')
            entries[key] = entry
        
        def save_dc_line():
            try:
                dc_num = len(self.calculator.dc_lines) + 1
                dc_line = DCDevice(dc_number=dc_num)
                
                for key, entry in entries.items():
                    value = int(entry.get())
                    if value < 0:
                        messagebox.showerror("Error", f"{key} must be 0 or positive")
                        return
                    setattr(dc_line, key, value)
                
                self.calculator.dc_lines.append(dc_line)
                self.update_dc_tree()
                dialog.destroy()
                self.status_var.set(f"DC Line {dc_num} added successfully")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")
        
        # Save button
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', pady=20, padx=20)
        
        ModernButton(btn_frame, text="💾 Save DC Line", 
                    command=save_dc_line).pack(fill='x')
    
    def edit_dc_line(self):
        """Edit selected DC line"""
        selection = self.dc_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a DC line to edit")
            return
        
        item = self.dc_tree.item(selection[0])
        values = item['values']
        dc_num = values[0]
        
        # Find DC line
        dc_line = next((dc for dc in self.calculator.dc_lines if dc.dc_number == dc_num), None)
        if not dc_line:
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit DC Line {dc_num}")
        dialog.geometry("400x550")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Apply theme to dialog
        self.apply_widget_theme(dialog, THEMES[self.current_theme])
        
        # Title
        ttk.Label(dialog, text=f"Edit DC Line {dc_num}", 
                 font=('Segoe UI', 12, 'bold')).pack(pady=(10, 20))
        
        # Device entries with current values
        entries_frame = ttk.Frame(dialog)
        entries_frame.pack(fill='both', expand=True, padx=20)
        
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
        for idx, (label, key) in enumerate(devices):
            frame = ttk.Frame(entries_frame)
            frame.pack(fill='x', pady=2)
            
            ttk.Label(frame, text=label, width=30, anchor='w').pack(side='left', padx=(0, 10))
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, str(getattr(dc_line, key)))
            entry.pack(side='right')
            entries[key] = entry
        
        def save_changes():
            try:
                for key, entry in entries.items():
                    value = int(entry.get())
                    if value < 0:
                        messagebox.showerror("Error", f"{key} must be 0 or positive")
                        return
                    setattr(dc_line, key, value)
                
                self.update_dc_tree()
                dialog.destroy()
                self.status_var.set(f"DC Line {dc_num} updated")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")
        
        # Save button
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', pady=20, padx=20)
        
        ModernButton(btn_frame, text="💾 Save Changes", 
                    command=save_changes).pack(fill='x')
    
    def delete_dc_line(self):
        """Delete selected DC line"""
        selection = self.dc_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a DC line to delete")
            return
        
        item = self.dc_tree.item(selection[0])
        values = item['values']
        dc_num = values[0]
        
        if messagebox.askyesno("Confirm Delete", f"Delete DC Line {dc_num}?"):
            self.calculator.dc_lines = [dc for dc in self.calculator.dc_lines if dc.dc_number != dc_num]
            # Renumber remaining DC lines
            for idx, dc in enumerate(self.calculator.dc_lines, 1):
                dc.dc_number = idx
            self.update_dc_tree()
            self.status_var.set(f"DC Line {dc_num} deleted")
    
    def clear_all_dc(self):
        """Clear all DC lines"""
        if messagebox.askyesno("Confirm Clear", "Delete all DC lines?"):
            self.calculator.dc_lines.clear()
            self.update_dc_tree()
            self.status_var.set("All DC lines cleared")
    
    def update_dc_tree(self):
        """Update the DC lines treeview"""
        # Clear tree
        for item in self.dc_tree.get_children():
            self.dc_tree.delete(item)
        
        # Add DC lines
        for dc_line in self.calculator.dc_lines:
            totals = dc_line.calculate_totals()
            values = (
                dc_line.dc_number,
                dc_line.smart_card,
                dc_line.fingerprint,
                dc_line.door_sensor,
                dc_line.magnetic_lock,
                dc_line.electric_lock,
                dc_line.rex_button,
                dc_line.push_button,
                dc_line.break_glass,
                dc_line.buzzer,
                dc_line.double_door_lock,
                dc_line.ddl_sensors,
                totals['readers'],
                totals['inputs'],
                totals['outputs']
            )
            self.dc_tree.insert('', 'end', values=values)
        
        # Update info label
        if self.calculator.dc_lines:
            total_readers = sum(dc.calculate_totals()['readers'] for dc in self.calculator.dc_lines)
            total_inputs = sum(dc.calculate_totals()['inputs'] for dc in self.calculator.dc_lines)
            total_outputs = sum(dc.calculate_totals()['outputs'] for dc in self.calculator.dc_lines)
            self.dc_info.set(f"{len(self.calculator.dc_lines)} DC line(s), "
                           f"{total_readers} readers, {total_inputs} inputs, {total_outputs} outputs")
        else:
            self.dc_info.set("No DC lines configured")
    
    def calc_kantech_single(self):
        """Calculate Kantech for selected DC line"""
        selection = self.dc_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a DC line to calculate")
            return
        
        item = self.dc_tree.item(selection[0])
        values = item['values']
        dc_num = values[0]
        
        # Find DC line
        dc_line = next((dc for dc in self.calculator.dc_lines if dc.dc_number == dc_num), None)
        if not dc_line:
            return
        
        # Calculate
        dc_totals = dc_line.calculate_totals()
        controller_info = self.calculator.select_controllers_for_dc(dc_totals)
        
        if not controller_info:
            self.kantech_results.delete('1.0', 'end')
            self.kantech_results.insert('1.0', f"No controller combination found for DC Line {dc_num}")
            return
        
        # Calculate expansion
        input_shortage = max(0, dc_totals['inputs'] - controller_info['inputs_provided'])
        output_shortage = max(0, dc_totals['outputs'] - controller_info['outputs_provided'])
        
        expansion_cost = 0
        expansion_modules = []
        
        if input_shortage > 0 or output_shortage > 0:
            # Simple expansion calculation
            if input_shortage > 0:
                in16_needed = int(np.ceil(input_shortage / 16))
                expansion_modules.append(f"in16 (x{in16_needed})")
                expansion_cost += 470 * in16_needed
            if output_shortage > 0:
                r8_needed = int(np.ceil(output_shortage / 8))
                expansion_modules.append(f"r8 (x{r8_needed})")
                expansion_cost += 470 * r8_needed
        
        total_cost = controller_info['cost'] + expansion_cost
        
        # Display results
        result_text = f"""KANTECH CALCULATION - DC LINE {dc_num}
{'='*50}

REQUIREMENTS:
  Readers: {dc_totals['readers']}
  Inputs:  {dc_totals['inputs']}
  Outputs: {dc_totals['outputs']}

SELECTED CONTROLLERS:
  kt-400: {controller_info['kt-400']} units
  kt-2:   {controller_info['kt-2']} units
  kt-1:   {controller_info['kt-1']} units

CONTROLLER CAPABILITIES:
  Readers provided: {controller_info['readers_provided']}
  Inputs provided:  {controller_info['inputs_provided']}
  Outputs provided: {controller_info['outputs_provided']}

I/O SHORTAGE:
  Input shortage:  {input_shortage}
  Output shortage: {output_shortage}

EXPANSION MODULES:
  {', '.join(expansion_modules) if expansion_modules else 'None needed'}

COST BREAKDOWN:
  Controllers: ${controller_info['cost']}
  Expansion:   ${expansion_cost}
  {'-'*30}
  TOTAL:       ${total_cost}
{'='*50}"""
        
        self.kantech_results.delete('1.0', 'end')
        self.kantech_results.insert('1.0', result_text)
        self.status_var.set(f"Kantech calculation complete for DC Line {dc_num}")
    
    def calc_kantech_all(self):
        """Calculate Kantech for all DC lines"""
        if not self.calculator.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured")
            return
        
        all_results = []
        total_cost = 0
        
        for dc_line in self.calculator.dc_lines:
            dc_totals = dc_line.calculate_totals()
            controller_info = self.calculator.select_controllers_for_dc(dc_totals)
            
            if controller_info:
                # Calculate expansion
                input_shortage = max(0, dc_totals['inputs'] - controller_info['inputs_provided'])
                output_shortage = max(0, dc_totals['outputs'] - controller_info['outputs_provided'])
                
                expansion_cost = 0
                if input_shortage > 0:
                    in16_needed = int(np.ceil(input_shortage / 16))
                    expansion_cost += 470 * in16_needed
                if output_shortage > 0:
                    r8_needed = int(np.ceil(output_shortage / 8))
                    expansion_cost += 470 * r8_needed
                
                line_cost = controller_info['cost'] + expansion_cost
                total_cost += line_cost
                
                all_results.append({
                    'dc_num': dc_line.dc_number,
                    'controllers': controller_info,
                    'expansion_cost': expansion_cost,
                    'line_cost': line_cost
                })
        
        # Display results
        result_text = f"""KANTECH ALL DC LINES CALCULATION
{'='*50}

SYSTEM SUMMARY:
  Total DC Lines: {len(self.calculator.dc_lines)}
  Total Cost:     ${total_cost:,.2f}

{'='*50}
DETAILED BREAKDOWN:
"""
        
        for result in all_results:
            result_text += f"""
DC LINE {result['dc_num']}:
  Controllers: kt-400({result['controllers']['kt-400']}) 
               kt-2({result['controllers']['kt-2']}) 
               kt-1({result['controllers']['kt-1']})
  Controller Cost: ${result['controllers']['cost']}
  Expansion Cost:  ${result['expansion_cost']}
  Line Total:      ${result['line_cost']}
  {'-'*30}"""
        
        # Calculate totals
        total_kt400 = sum(r['controllers']['kt-400'] for r in all_results)
        total_kt2 = sum(r['controllers']['kt-2'] for r in all_results)
        total_kt1 = sum(r['controllers']['kt-1'] for r in all_results)
        
        result_text += f"""

TOTALS:
  kt-400: {total_kt400} units
  kt-2:   {total_kt2} units
  kt-1:   {total_kt1} units
  Total Controllers: {total_kt400 + total_kt2 + total_kt1}
  Total Cost: ${total_cost:,.2f}
{'='*50}"""
        
        self.kantech_results.delete('1.0', 'end')
        self.kantech_results.insert('1.0', result_text)
        self.status_var.set(f"Kantech calculation complete for all {len(self.calculator.dc_lines)} DC lines")
    
    def calc_swh_single(self):
        """Calculate SWH GSTAR for selected DC line"""
        selection = self.dc_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a DC line to calculate")
            return
        
        item = self.dc_tree.item(selection[0])
        values = item['values']
        dc_num = values[0]
        
        # Find DC line
        dc_line = next((dc for dc in self.calculator.dc_lines if dc.dc_number == dc_num), None)
        if not dc_line:
            return
        
        # Calculate
        dc_totals = dc_line.calculate_totals()
        controller = self.calculator.swh_calculator.select_controller_for_readers(dc_totals['readers'])
        
        if not controller:
            self.swh_results.delete('1.0', 'end')
            self.swh_results.insert('1.0', f"No suitable GSTAR controller found for {dc_totals['readers']} readers")
            return
        
        # Calculate expansion
        input_shortage = max(0, dc_totals['inputs'] - controller.inputs)
        output_shortage = max(0, dc_totals['outputs'] - controller.outputs)
        
        expansion_cost = 0
        expansion_modules = []
        
        if input_shortage > 0:
            as0073_needed = int(np.ceil(input_shortage / 8))
            expansion_modules.append(f"AS0073-000 (x{as0073_needed})")
            expansion_cost += 333 * as0073_needed
        
        if output_shortage > 0:
            as0074_needed = int(np.ceil(output_shortage / 8))
            expansion_modules.append(f"AS0074-000 (x{as0074_needed})")
            expansion_cost += 395 * as0074_needed
        
        total_cost = controller.price + expansion_cost
        
        # Display results
        result_text = f"""SWH GSTAR CALCULATION - DC LINE {dc_num}
{'='*50}

REQUIREMENTS:
  Readers: {dc_totals['readers']}
  Inputs:  {dc_totals['inputs']}
  Outputs: {dc_totals['outputs']}

SELECTED CONTROLLER:
  {controller.name}
  Readers: {controller.readers}
  Inputs:  {controller.inputs}
  Outputs: {controller.outputs}
  ACM Modules: {controller.number_of_acm}
  Price: ${controller.price}

I/O SHORTAGE:
  Input shortage:  {input_shortage}
  Output shortage: {output_shortage}

EXPANSION MODULES:
  {', '.join(expansion_modules) if expansion_modules else 'None needed'}

COST BREAKDOWN:
  Controller: ${controller.price}
  Expansion:  ${expansion_cost}
  {'-'*30}
  TOTAL:      ${total_cost}
{'='*50}"""
        
        self.swh_results.delete('1.0', 'end')
        self.swh_results.insert('1.0', result_text)
        self.status_var.set(f"SWH calculation complete for DC Line {dc_num}")
    
    def calc_swh_all(self):
        """Calculate SWH GSTAR for all DC lines"""
        if not self.calculator.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured")
            return
        
        all_results = []
        total_cost = 0
        total_readers = 0
        total_input_modules = 0
        total_output_modules = 0
        
        for dc_line in self.calculator.dc_lines:
            dc_totals = dc_line.calculate_totals()
            controller = self.calculator.swh_calculator.select_controller_for_readers(dc_totals['readers'])
            total_readers += dc_totals['readers']
            
            if controller:
                # Calculate expansion
                input_shortage = max(0, dc_totals['inputs'] - controller.inputs)
                output_shortage = max(0, dc_totals['outputs'] - controller.outputs)
                
                expansion_cost = 0
                input_modules = 0
                output_modules = 0
                
                if input_shortage > 0:
                    as0073_needed = int(np.ceil(input_shortage / 8))
                    expansion_cost += 333 * as0073_needed
                    input_modules = as0073_needed
                    total_input_modules += as0073_needed
                
                if output_shortage > 0:
                    as0074_needed = int(np.ceil(output_shortage / 8))
                    expansion_cost += 395 * as0074_needed
                    output_modules = as0074_needed
                    total_output_modules += as0074_needed
                
                line_cost = controller.price + expansion_cost
                total_cost += line_cost
                
                all_results.append({
                    'dc_num': dc_line.dc_number,
                    'controller': controller,
                    'expansion_cost': expansion_cost,
                    'input_modules': input_modules,
                    'output_modules': output_modules,
                    'line_cost': line_cost
                })
        
        # Display results
        result_text = f"""SWH GSTAR ALL DC LINES CALCULATION
{'='*50}

SYSTEM SUMMARY:
  Total DC Lines: {len(self.calculator.dc_lines)}
  Total Readers:  {total_readers}
  Total Cost:     ${total_cost:,.2f}

{'='*50}
DETAILED BREAKDOWN:
"""
        
        for result in all_results:
            result_text += f"""
DC LINE {result['dc_num']}:
  Controller: {result['controller'].name}
  Controller Cost: ${result['controller'].price}
  Expansion Cost:  ${result['expansion_cost']}
  Line Total:      ${result['line_cost']}
  {'-'*30}"""
        
        result_text += f"""

TOTALS:
  Total Controllers: {len(all_results)}
  Total AS0073-000: {total_input_modules}
  Total AS0074-000: {total_output_modules}
  Total Readers:    {total_readers}
  Total Cost:       ${total_cost:,.2f}
{'='*50}"""
        
        self.swh_results.delete('1.0', 'end')
        self.swh_results.insert('1.0', result_text)
        self.status_var.set(f"SWH calculation complete for all {len(self.calculator.dc_lines)} DC lines")
    
    def calc_swh_license(self):
        """Calculate SWH license based on total readers"""
        if not self.calculator.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured")
            return
        
        # Calculate total readers
        total_readers = sum(dc.calculate_totals()['readers'] for dc in self.calculator.dc_lines)
        
        # Find suitable license
        suitable_licenses = []
        for license_info in self.calculator.swh_calculator.swh_licenses:
            if license_info['max_readers'] >= total_readers:
                suitable_licenses.append(license_info)
        
        if not suitable_licenses:
            self.swh_results.delete('1.0', 'end')
            self.swh_results.insert('1.0', f"No suitable license found for {total_readers} readers")
            return
        
        suitable_licenses.sort(key=lambda x: x['max_readers'])
        recommended_license = suitable_licenses[0]
        
        result_text = f"""SWH LICENSE CALCULATION
{'='*50}

SYSTEM SUMMARY:
  Total DC Lines: {len(self.calculator.dc_lines)}
  Total Readers:  {total_readers}

AVAILABLE LICENSES:
"""
        
        for license_info in self.calculator.swh_calculator.swh_licenses:
            status = "✓ Suitable" if license_info['max_readers'] >= total_readers else "✗ Insufficient"
            result_text += f"  {license_info['name']:<12} Max Readers: {license_info['max_readers']:<6} {status}\n"
        
        result_text += f"""
{'='*50}

RECOMMENDED LICENSE:
  {recommended_license['name']}
  Supports up to {recommended_license['max_readers']} readers
  Cost: ${recommended_license['cost']} (included in controller cost)

This license will support all {total_readers} readers in your system.
{'='*50}"""
        
        self.swh_results.delete('1.0', 'end')
        self.swh_results.insert('1.0', result_text)
        self.status_var.set(f"SWH license calculation complete - {recommended_license['name']} recommended")
    
    def calc_license(self):
        """Calculate license requirements"""
        if not self.calculator.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured")
            return
        
        # Calculate total controllers
        total_kt400 = 0
        total_kt2 = 0
        total_kt1 = 0
        
        for dc_line in self.calculator.dc_lines:
            dc_totals = dc_line.calculate_totals()
            controller_info = self.calculator.select_controllers_for_dc(dc_totals)
            
            if controller_info:
                total_kt400 += controller_info['kt-400']
                total_kt2 += controller_info['kt-2']
                total_kt1 += controller_info['kt-1']
        
        total_controllers = total_kt400 + total_kt2 + total_kt1
        use_redundancy = self.redundancy_var.get()
        
        # Build result text
        result_text = f"""LICENSE CALCULATION RESULTS
{'='*50}

CONTROLLER SUMMARY:
  Total Controllers: {total_controllers}
  kt-400: {total_kt400} units
  kt-2:   {total_kt2} units
  kt-1:   {total_kt1} units

CONFIGURATION:
  {'Redundant System' if use_redundancy else 'Non-Redundant System'}

{'='*50}
LICENSE REQUIREMENTS:
"""
        
        if use_redundancy:
            result_text += f"""
  Required Licenses:
  1. {self.calculator.license_info['global']['name']}
     - Base license for redundant systems
     - Cost: ${self.calculator.license_info['global']['cost']}
  
  2. {self.calculator.license_info['gateway']['name']}
     - For gateway/server communication
     - Cost: ${self.calculator.license_info['gateway']['cost']}
  
  3. {self.calculator.license_info['redundancy']['name']}
     - For failover/redundancy capability
     - Cost: ${self.calculator.license_info['redundancy']['cost']}
  
  Total License Cost: ${self.calculator.license_info['gateway']['cost'] + 
                       self.calculator.license_info['redundancy']['cost']:,.2f}
  """
        else:
            if total_controllers <= 32:
                license_name = self.calculator.license_info['special']['name']
                reason = f"{total_controllers} controllers ≤ 32"
            else:
                license_name = self.calculator.license_info['corporate']['name']
                reason = f"{total_controllers} controllers > 32"
            
            result_text += f"""
  Required License:
  • {license_name}
    - Reason: {reason}
    - Cost: $0 (included in controller cost)
  
  Total License Cost: $0.00
  """
        
        result_text += f"""
{'='*50}
Note: For redundant systems, Global License replaces Special/Corporate licenses.
"""
        
        self.license_results.delete('1.0', 'end')
        self.license_results.insert('1.0', result_text)
        self.status_var.set(f"License calculation complete")
    
    def update_summary(self):
        """Update the summary tab"""
        if not self.calculator.dc_lines:
            self.summary_text.delete('1.0', 'end')
            self.summary_text.insert('1.0', "No DC lines configured. Please add DC lines first.")
            return
        
        # Calculate totals
        total_readers = sum(dc.calculate_totals()['readers'] for dc in self.calculator.dc_lines)
        total_inputs = sum(dc.calculate_totals()['inputs'] for dc in self.calculator.dc_lines)
        total_outputs = sum(dc.calculate_totals()['outputs'] for dc in self.calculator.dc_lines)
        
        summary_text = f"""ACCESS CONTROL SYSTEM SUMMARY
{'='*60}

SYSTEM OVERVIEW:
  • Total DC Lines: {len(self.calculator.dc_lines)}
  • Total Readers:  {total_readers}
  • Total Inputs:   {total_inputs}
  • Total Outputs:  {total_outputs}

{'='*60}
DC LINES DETAIL:
"""
        
        for dc_line in self.calculator.dc_lines:
            totals = dc_line.calculate_totals()
            summary_text += f"""
DC Line {dc_line.dc_number}:
  Devices: Smart Card({dc_line.smart_card}), 
           Fingerprint({dc_line.fingerprint}), 
           Door Sensor({dc_line.door_sensor}), 
           Mag Lock({dc_line.magnetic_lock}), 
           Elec Lock({dc_line.electric_lock})
  REX({dc_line.rex_button}), Push Button({dc_line.push_button}), 
  Break Glass({dc_line.break_glass}), Buzzer({dc_line.buzzer}), 
  DDL({dc_line.double_door_lock}), DDL Sensors({dc_line.ddl_sensors})
  Totals: {totals['readers']}R/{totals['inputs']}I/{totals['outputs']}O
  {'-'*40}"""
        
        summary_text += f"""
{'='*60}

CALCULATION OPTIONS:
  1. Kantech System:
     • Multiple controllers per DC line
     • Based on readers only, then expand I/O
     • Various controller models available
  
  2. SWH GSTAR System:
     • One controller per DC line
     • Based on readers only
     • Standard expansion modules
     • License based on total readers

{'='*60}
NEXT STEPS:
  1. Go to 'Kantech System' tab for Kantech calculations
  2. Go to 'SWH GSTAR System' tab for SWH calculations
  3. Go to 'License' tab for license requirements
  4. Use 'Export' buttons to save results
"""
        
        self.summary_text.delete('1.0', 'end')
        self.summary_text.insert('1.0', summary_text)
        self.status_var.set("Summary updated")
    
    def export_kantech(self):
        """Export Kantech results to CSV"""
        if not self.calculator.dc_lines:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="kantech_results.csv"
        )
        
        if not filename:
            return
        
        try:
            # Prepare data for export
            data = []
            
            for dc_line in self.calculator.dc_lines:
                dc_totals = dc_line.calculate_totals()
                controller_info = self.calculator.select_controllers_for_dc(dc_totals)
                
                if controller_info:
                    row = {
                        'DC_Line': dc_line.dc_number,
                        'Smart_Card': dc_line.smart_card,
                        'Fingerprint': dc_line.fingerprint,
                        'Door_Sensor': dc_line.door_sensor,
                        'Mag_Lock': dc_line.magnetic_lock,
                        'Elec_Lock': dc_line.electric_lock,
                        'REX': dc_line.rex_button,
                        'Push_Button': dc_line.push_button,
                        'Break_Glass': dc_line.break_glass,
                        'Buzzer': dc_line.buzzer,
                        'DDL': dc_line.double_door_lock,
                        'DDL_Sensors': dc_line.ddl_sensors,
                        'Required_Readers': dc_totals['readers'],
                        'Required_Inputs': dc_totals['inputs'],
                        'Required_Outputs': dc_totals['outputs'],
                        'KT400': controller_info['kt-400'],
                        'KT2': controller_info['kt-2'],
                        'KT1': controller_info['kt-1'],
                        'Controller_Cost': controller_info['cost']
                    }
                    data.append(row)
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            messagebox.showinfo("Success", f"Kantech results exported to {filename}")
            self.status_var.set(f"Exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def export_gstar(self):
        """Export GSTAR results to CSV"""
        if not self.calculator.dc_lines:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="gstar_results.csv"
        )
        
        if not filename:
            return
        
        try:
            # Prepare data for export
            data = []
            total_readers = 0
            
            for dc_line in self.calculator.dc_lines:
                dc_totals = dc_line.calculate_totals()
                total_readers += dc_totals['readers']
                controller = self.calculator.swh_calculator.select_controller_for_readers(dc_totals['readers'])
                
                row = {
                    'DC_Line': dc_line.dc_number,
                    'Required_Readers': dc_totals['readers'],
                    'Required_Inputs': dc_totals['inputs'],
                    'Required_Outputs': dc_totals['outputs']
                }
                
                if controller:
                    row.update({
                        'Selected_Controller': controller.name,
                        'Controller_Readers': controller.readers,
                        'Controller_Inputs': controller.inputs,
                        'Controller_Outputs': controller.outputs,
                        'Controller_Price': controller.price,
                        'ACM_Modules': controller.number_of_acm
                    })
                else:
                    row.update({
                        'Selected_Controller': 'No suitable controller',
                        'Controller_Readers': '',
                        'Controller_Inputs': '',
                        'Controller_Outputs': '',
                        'Controller_Price': '',
                        'ACM_Modules': ''
                    })
                
                data.append(row)
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            messagebox.showinfo("Success", f"GSTAR results exported to {filename}")
            self.status_var.set(f"Exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def export_all(self):
        """Export all data to CSV"""
        if not self.calculator.dc_lines:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="access_control_data.csv"
        )
        
        if not filename:
            return
        
        try:
            # Prepare comprehensive data
            data = []
            
            for dc_line in self.calculator.dc_lines:
                dc_totals = dc_line.calculate_totals()
                
                # Kantech calculation
                kantech_info = self.calculator.select_controllers_for_dc(dc_totals)
                
                # SWH calculation
                swh_controller = self.calculator.swh_calculator.select_controller_for_readers(dc_totals['readers'])
                
                row = {
                    'DC_Line': dc_line.dc_number,
                    'Smart_Card': dc_line.smart_card,
                    'Fingerprint': dc_line.fingerprint,
                    'Door_Sensor': dc_line.door_sensor,
                    'Mag_Lock': dc_line.magnetic_lock,
                    'Elec_Lock': dc_line.electric_lock,
                    'REX': dc_line.rex_button,
                    'Push_Button': dc_line.push_button,
                    'Break_Glass': dc_line.break_glass,
                    'Buzzer': dc_line.buzzer,
                    'DDL': dc_line.double_door_lock,
                    'DDL_Sensors': dc_line.ddl_sensors,
                    'Total_Readers': dc_totals['readers'],
                    'Total_Inputs': dc_totals['inputs'],
                    'Total_Outputs': dc_totals['outputs'],
                    'Kantech_KT400': kantech_info['kt-400'] if kantech_info else '',
                    'Kantech_KT2': kantech_info['kt-2'] if kantech_info else '',
                    'Kantech_KT1': kantech_info['kt-1'] if kantech_info else '',
                    'Kantech_Cost': kantech_info['cost'] if kantech_info else '',
                    'SWH_Controller': swh_controller.name if swh_controller else '',
                    'SWH_Cost': swh_controller.price if swh_controller else ''
                }
                data.append(row)
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            messagebox.showinfo("Success", f"All data exported to {filename}")
            self.status_var.set(f"All data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")


def main():
    root = tk.Tk()
    app = DCApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
