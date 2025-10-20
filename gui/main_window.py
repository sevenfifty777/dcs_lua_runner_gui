"""
Main window for the DCS Lua Runner GUI application.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from typing import Dict, Any

from core.dcs_client import DCSClient
from core.settings_manager import SettingsManager
from utils.syntax_highlighter import LuaSyntaxHighlighter, SimpleTextHighlighter


class MainWindow:
    """Main application window for DCS Lua Runner GUI."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.load_settings()
        self.dcs_client = DCSClient()
        
        self.setup_window()
        self.create_widgets()
        self.setup_syntax_highlighting()
        self.update_status_bar()
        
    def setup_window(self):
        """Configure the main window."""
        self.root.title("DCS Lua Runner")
        self.root.geometry(f"{self.settings['window_width']}x{self.settings['window_height']}")
        
        # Configure dark theme
        self.root.configure(bg='#1e1e1e')
        
        # Configure style for ttk widgets
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#2d2d30', borderwidth=0)
        style.configure('TNotebook.Tab', background='#3c3c3c', foreground='#ffffff', padding=[10, 5])
        style.map('TNotebook.Tab', background=[('selected', '#007acc')])
        style.configure('TFrame', background='#2d2d30')
        style.configure('TLabel', background='#2d2d30', foreground='#ffffff')
        style.configure('TButton', background='#0e639c', foreground='#ffffff')
        style.map('TButton', background=[('active', '#1177bb')])
        
    def create_widgets(self):
        """Create and layout all widgets."""
        # Create main menu
        self.create_menu()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create main content area with paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Code editor
        self.create_code_editor_panel(main_paned)
        
        # Right panel - Settings and Results
        self.create_right_panel(main_paned)
        
        # Status bar
        self.create_status_bar()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_menu(self):
        """Create the main menu bar."""
        menubar = tk.Menu(self.root, bg='#2d2d30', fg='#ffffff')
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, bg='#2d2d30', fg='#ffffff')
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_file_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0, bg='#2d2d30', fg='#ffffff')
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Cut", command=self.cut_text, accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=self.copy_text, accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=self.paste_text, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", command=self.select_all_text, accelerator="Ctrl+A")
        
        # Run menu
        run_menu = tk.Menu(menubar, tearoff=0, bg='#2d2d30', fg='#ffffff')
        menubar.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run Code", command=self.run_code, accelerator="F5")
        run_menu.add_command(label="Run Selected", command=self.run_selected, accelerator="F8")
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0, bg='#2d2d30', fg='#ffffff')
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Toggle Local/Remote", command=self.toggle_local_remote)
        settings_menu.add_command(label="Toggle Mission/GUI", command=self.toggle_mission_gui)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, bg='#2d2d30', fg='#ffffff')
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_file_as())
        self.root.bind('<F5>', lambda e: self.run_code())
        self.root.bind('<F8>', lambda e: self.run_selected())
        
    def create_toolbar(self):
        """Create the toolbar."""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # Run button
        self.run_button = ttk.Button(toolbar, text="▶ Run", command=self.run_code)
        self.run_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Run selected button
        self.run_selected_button = ttk.Button(toolbar, text="▶ Selected", command=self.run_selected)
        self.run_selected_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Local/Remote toggle
        self.local_remote_button = ttk.Button(toolbar, text="Local", command=self.toggle_local_remote)
        self.local_remote_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Mission/GUI toggle
        self.mission_gui_button = ttk.Button(toolbar, text="Mission", command=self.toggle_mission_gui)
        self.mission_gui_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Format toggle
        self.format_button = ttk.Button(toolbar, text="Lua", command=self.toggle_format)
        self.format_button.pack(side=tk.LEFT)
        
    def create_code_editor_panel(self, parent):
        """Create the code editor panel."""
        editor_frame = ttk.Frame(parent)
        parent.add(editor_frame, weight=2)
        
        # Editor label
        ttk.Label(editor_frame, text="Lua Code Editor").pack(anchor=tk.W, pady=(0, 5))
        
        # Create text widget with scrollbars
        text_frame = tk.Frame(editor_frame, bg='#1e1e1e')
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Line numbers frame
        line_frame = tk.Frame(text_frame, bg='#3c3c3c', width=40)
        line_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.line_numbers = tk.Text(line_frame, width=4, padx=3, pady=5,
                                   bg='#3c3c3c', fg='#858585', bd=0,
                                   state='disabled', wrap='none',
                                   font=(self.settings['editor_font_family'], self.settings['editor_font_size']))
        self.line_numbers.pack(fill=tk.Y, expand=True)
        
        # Code editor
        editor_scroll_frame = tk.Frame(text_frame)
        editor_scroll_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.code_editor = tk.Text(editor_scroll_frame, 
                                  bg='#1e1e1e', fg='#d4d4d4', 
                                  insertbackground='#ffffff',
                                  selectbackground='#264f78',
                                  font=(self.settings['editor_font_family'], self.settings['editor_font_size']),
                                  wrap='none', undo=True, maxundo=-1)
        
        # Scrollbars for editor
        v_scrollbar = ttk.Scrollbar(editor_scroll_frame, orient=tk.VERTICAL, command=self.code_editor.yview)
        h_scrollbar = ttk.Scrollbar(editor_scroll_frame, orient=tk.HORIZONTAL, command=self.code_editor.xview)
        
        self.code_editor.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars and editor
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.code_editor.pack(fill=tk.BOTH, expand=True)
        
        # Bind events for line numbers and syntax highlighting
        self.code_editor.bind('<KeyRelease>', self.on_text_change)
        self.code_editor.bind('<Button-1>', self.on_text_change)
        self.code_editor.bind('<MouseWheel>', self.sync_line_numbers)
        self.code_editor.bind('<Configure>', self.sync_line_numbers)
        
        # Sample Lua code
        sample_code = """-- DCS Lua Code Example
local player = world.getPlayer()
if player then
    env.info("Player name: " .. player:getName())
    return player:getPosition().p
else
    return "No player found"
end"""
        self.code_editor.insert('1.0', sample_code)
        
    def create_right_panel(self, parent):
        """Create the right panel with settings and results."""
        right_frame = ttk.Frame(parent)
        parent.add(right_frame, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Settings tab
        self.create_settings_tab()
        
        # Results tab
        self.create_results_tab()
        
    def create_settings_tab(self):
        """Create the settings tab."""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
        
        # Create scrollable frame
        canvas = tk.Canvas(settings_frame, bg='#2d2d30')
        scrollbar = ttk.Scrollbar(settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Connection Settings
        conn_frame = ttk.LabelFrame(scrollable_frame, text="Connection Settings", padding=10)
        conn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Server Address
        ttk.Label(conn_frame, text="Server Address:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.server_address_var = tk.StringVar(value=self.settings.get('server_address', ''))
        server_entry = ttk.Entry(conn_frame, textvariable=self.server_address_var, width=30)
        server_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # Server Port
        ttk.Label(conn_frame, text="Server Port:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.server_port_var = tk.StringVar(value=str(self.settings.get('server_port', 12080)))
        port_entry = ttk.Entry(conn_frame, textvariable=self.server_port_var, width=10)
        port_entry.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # GUI Server Address
        ttk.Label(conn_frame, text="GUI Server Address:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.server_address_gui_var = tk.StringVar(value=self.settings.get('server_address_gui', ''))
        gui_server_entry = ttk.Entry(conn_frame, textvariable=self.server_address_gui_var, width=30)
        gui_server_entry.grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # GUI Server Port
        ttk.Label(conn_frame, text="GUI Server Port:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.server_port_gui_var = tk.StringVar(value=str(self.settings.get('server_port_gui', 12081)))
        gui_port_entry = ttk.Entry(conn_frame, textvariable=self.server_port_gui_var, width=10)
        gui_port_entry.grid(row=3, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # HTTPS
        self.use_https_var = tk.BooleanVar(value=self.settings.get('use_https', False))
        https_check = ttk.Checkbutton(conn_frame, text="Use HTTPS", variable=self.use_https_var)
        https_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Authentication Settings
        auth_frame = ttk.LabelFrame(scrollable_frame, text="Authentication", padding=10)
        auth_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Username
        ttk.Label(auth_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.username_var = tk.StringVar(value=self.settings.get('web_auth_username', 'username'))
        username_entry = ttk.Entry(auth_frame, textvariable=self.username_var, width=20)
        username_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # Password
        ttk.Label(auth_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.password_var = tk.StringVar(value=self.settings.get('web_auth_password', 'password'))
        password_entry = ttk.Entry(auth_frame, textvariable=self.password_var, show="*", width=20)
        password_entry.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # Execution Settings
        exec_frame = ttk.LabelFrame(scrollable_frame, text="Execution Settings", padding=10)
        exec_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Local/Remote
        self.run_locally_var = tk.BooleanVar(value=self.settings.get('run_code_locally', True))
        local_check = ttk.Checkbutton(exec_frame, text="Run Code Locally", variable=self.run_locally_var)
        local_check.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # Mission/GUI Environment
        self.mission_env_var = tk.BooleanVar(value=self.settings.get('run_in_mission_env', True))
        mission_check = ttk.Checkbutton(exec_frame, text="Run in Mission Environment", variable=self.mission_env_var)
        mission_check.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # Display Settings
        display_frame = ttk.LabelFrame(scrollable_frame, text="Display Settings", padding=10)
        display_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Format
        ttk.Label(display_frame, text="Result Format:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.format_var = tk.StringVar(value=self.settings.get('return_display_format', 'lua'))
        format_combo = ttk.Combobox(display_frame, textvariable=self.format_var, values=['lua', 'json'], state='readonly', width=15)
        format_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # Save/Load buttons
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save Settings", command=self.save_settings).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Load Settings", command=self.load_settings).pack(side=tk.LEFT)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_results_tab(self):
        """Create the results tab."""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="Results")
        
        # Results label
        ttk.Label(results_frame, text="Execution Results").pack(anchor=tk.W, pady=(0, 5))
        
        # Results text area with scrollbar
        results_text_frame = tk.Frame(results_frame)
        results_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.results_text = tk.Text(results_text_frame,
                                   bg='#1e1e1e', fg='#d4d4d4',
                                   font=(self.settings['editor_font_family'], self.settings['editor_font_size']),
                                   wrap='word', state='disabled')
        
        results_scrollbar = ttk.Scrollbar(results_text_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scrollbar.set)
        
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Clear button
        ttk.Button(results_frame, text="Clear Results", command=self.clear_results).pack(pady=(5, 0))
        
    def create_status_bar(self):
        """Create the status bar."""
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_syntax_highlighting(self):
        """Setup syntax highlighting for the code editor."""
        self.lua_highlighter = LuaSyntaxHighlighter(self.code_editor)
        self.results_highlighter = SimpleTextHighlighter(self.results_text)
        
        # Initial highlighting
        self.lua_highlighter.highlight_syntax()
        
    def on_text_change(self, event=None):
        """Handle text changes in the code editor."""
        self.update_line_numbers()
        # Delay syntax highlighting to avoid performance issues
        self.root.after_idle(self.lua_highlighter.highlight_syntax)
        
    def update_line_numbers(self):
        """Update line numbers in the editor."""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)
        
        line_count = int(self.code_editor.index('end-1c').split('.')[0])
        line_numbers_text = '\n'.join(str(i) for i in range(1, line_count + 1))
        
        self.line_numbers.insert('1.0', line_numbers_text)
        self.line_numbers.config(state='disabled')
        
    def sync_line_numbers(self, event=None):
        """Synchronize line numbers scrolling with code editor."""
        self.line_numbers.yview_moveto(self.code_editor.yview()[0])
        
    def update_status_bar(self):
        """Update the status bar with current connection info."""
        connection_info = self.settings_manager.get_connection_info(self.settings)
        self.status_bar.config(text=connection_info)
        
        # Update button texts
        self.local_remote_button.config(text="Local" if self.settings.get('run_code_locally', True) else "Remote")
        self.mission_gui_button.config(text="Mission" if self.settings.get('run_in_mission_env', True) else "GUI")
        self.format_button.config(text=self.settings.get('return_display_format', 'lua').title())
        
    def run_code(self):
        """Run all code in the editor."""
        code = self.code_editor.get('1.0', 'end-1c').strip()
        if not code:
            messagebox.showwarning("Warning", "No code to execute")
            return
            
        self._execute_code(code, "Full Code")
        
    def run_selected(self):
        """Run selected code in the editor."""
        try:
            selected_code = self.code_editor.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if not selected_code:
                messagebox.showwarning("Warning", "No code selected")
                return
            self._execute_code(selected_code, "Selected Code")
        except tk.TclError:
            messagebox.showwarning("Warning", "No code selected")
            
    def _execute_code(self, code: str, code_type: str):
        """Execute code on DCS server in a separate thread."""
        def execute():
            self.run_button.config(state='disabled')
            self.run_selected_button.config(state='disabled')
            self.status_bar.config(text="Executing...")
            
            try:
                success, result = self.dcs_client.run_lua(code, self.settings)
                
                # Update results on main thread
                self.root.after(0, lambda: self._display_result(success, result, code_type))
                
            except Exception as e:
                self.root.after(0, lambda: self._display_result(False, str(e), code_type))
            finally:
                self.root.after(0, lambda: (
                    self.run_button.config(state='normal'),
                    self.run_selected_button.config(state='normal'),
                    self.update_status_bar()
                ))
        
        threading.Thread(target=execute, daemon=True).start()
        
    def _display_result(self, success: bool, result: Any, code_type: str):
        """Display execution result in the results tab."""
        self.results_text.config(state='normal')
        
        # Add timestamp and code type
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        header = f"[{timestamp}] {code_type} - {'SUCCESS' if success else 'ERROR'}\n"
        
        self.results_text.insert(tk.END, header)
        
        if success:
            if self.settings.get('return_display_format', 'lua') == 'lua':
                formatted_result = self.dcs_client.format_result_as_lua(result)
            else:
                import json
                formatted_result = json.dumps(result, indent=4) if result is not None else "null"
            
            self.results_text.insert(tk.END, formatted_result + "\n\n")
            
            # Apply syntax highlighting
            if self.settings.get('return_display_format', 'lua') == 'lua':
                self.results_highlighter.highlight_lua()
            else:
                self.results_highlighter.highlight_json()
        else:
            self.results_text.insert(tk.END, str(result) + "\n\n")
            
        self.results_text.config(state='disabled')
        self.results_text.see(tk.END)
        
        # Switch to results tab
        self.notebook.select(1)
        
    def toggle_local_remote(self):
        """Toggle between local and remote execution."""
        self.settings['run_code_locally'] = not self.settings.get('run_code_locally', True)
        self.run_locally_var.set(self.settings['run_code_locally'])
        self.update_status_bar()
        
    def toggle_mission_gui(self):
        """Toggle between mission and GUI environment."""
        self.settings['run_in_mission_env'] = not self.settings.get('run_in_mission_env', True)
        self.mission_env_var.set(self.settings['run_in_mission_env'])
        self.update_status_bar()
        
    def toggle_format(self):
        """Toggle between Lua and JSON result format."""
        current_format = self.settings.get('return_display_format', 'lua')
        new_format = 'json' if current_format == 'lua' else 'lua'
        self.settings['return_display_format'] = new_format
        self.format_var.set(new_format)
        self.update_status_bar()
        
    def save_settings(self):
        """Save current settings to file."""
        # Update settings from UI
        self.settings.update({
            'server_address': self.server_address_var.get(),
            'server_port': int(self.server_port_var.get()) if self.server_port_var.get().isdigit() else 12080,
            'server_address_gui': self.server_address_gui_var.get(),
            'server_port_gui': int(self.server_port_gui_var.get()) if self.server_port_gui_var.get().isdigit() else 12081,
            'use_https': self.use_https_var.get(),
            'web_auth_username': self.username_var.get(),
            'web_auth_password': self.password_var.get(),
            'run_code_locally': self.run_locally_var.get(),
            'run_in_mission_env': self.mission_env_var.get(),
            'return_display_format': self.format_var.get(),
            'window_width': self.root.winfo_width(),
            'window_height': self.root.winfo_height()
        })
        
        if self.settings_manager.save_settings(self.settings):
            messagebox.showinfo("Success", "Settings saved successfully")
            self.update_status_bar()
        else:
            messagebox.showerror("Error", "Failed to save settings")
            
    def load_settings(self):
        """Load settings from file."""
        self.settings = self.settings_manager.load_settings()
        
        # Update UI
        self.server_address_var.set(self.settings.get('server_address', ''))
        self.server_port_var.set(str(self.settings.get('server_port', 12080)))
        self.server_address_gui_var.set(self.settings.get('server_address_gui', ''))
        self.server_port_gui_var.set(str(self.settings.get('server_port_gui', 12081)))
        self.use_https_var.set(self.settings.get('use_https', False))
        self.username_var.set(self.settings.get('web_auth_username', 'username'))
        self.password_var.set(self.settings.get('web_auth_password', 'password'))
        self.run_locally_var.set(self.settings.get('run_code_locally', True))
        self.mission_env_var.set(self.settings.get('run_in_mission_env', True))
        self.format_var.set(self.settings.get('return_display_format', 'lua'))
        
        self.update_status_bar()
        messagebox.showinfo("Success", "Settings loaded successfully")
        
    def clear_results(self):
        """Clear the results text area."""
        self.results_text.config(state='normal')
        self.results_text.delete('1.0', tk.END)
        self.results_text.config(state='disabled')
        
    def new_file(self):
        """Create a new file."""
        if messagebox.askyesno("New File", "Clear current code?"):
            self.code_editor.delete('1.0', tk.END)
            
    def open_file(self):
        """Open a Lua file."""
        filename = filedialog.askopenfilename(
            title="Open Lua File",
            filetypes=[("Lua files", "*.lua"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.code_editor.delete('1.0', tk.END)
                self.code_editor.insert('1.0', content)
                self.lua_highlighter.highlight_syntax()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")
                
    def save_file(self):
        """Save current code to a file."""
        filename = filedialog.asksaveasfilename(
            title="Save Lua File",
            defaultextension=".lua",
            filetypes=[("Lua files", "*.lua"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.code_editor.get('1.0', 'end-1c'))
                messagebox.showinfo("Success", "File saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
                
    def save_file_as(self):
        """Save current code to a new file."""
        self.save_file()
        
    def cut_text(self):
        """Cut selected text."""
        try:
            self.code_editor.event_generate("<<Cut>>")
        except:
            pass
            
    def copy_text(self):
        """Copy selected text."""
        try:
            self.code_editor.event_generate("<<Copy>>")
        except:
            pass
            
    def paste_text(self):
        """Paste text from clipboard."""
        try:
            self.code_editor.event_generate("<<Paste>>")
        except:
            pass
            
    def select_all_text(self):
        """Select all text in the editor."""
        self.code_editor.tag_add(tk.SEL, "1.0", tk.END)
        self.code_editor.mark_set(tk.INSERT, "1.0")
        self.code_editor.see(tk.INSERT)
        
    def show_about(self):
        """Show about dialog."""
        about_text = """DCS Lua Runner GUI
        
A standalone application for executing Lua code in DCS World.

Based on the DCS Fiddle project and DCS Lua Runner VSCode extension.

Features:
• Execute Lua code on local or remote DCS servers
• Syntax highlighting for Lua code
• Mission and GUI environment support  
• Authentication for remote connections
• Configurable result formatting

Version: 1.0.0"""
        messagebox.showinfo("About", about_text)
        
    def on_closing(self):
        """Handle window closing."""
        # Save current window size
        self.settings['window_width'] = self.root.winfo_width()
        self.settings['window_height'] = self.root.winfo_height()
        self.settings_manager.save_settings(self.settings)
        
        self.root.destroy()
        
    def run(self):
        """Start the application."""
        self.root.mainloop()
