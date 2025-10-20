"""
Syntax highlighting utilities for the DCS Lua Runner GUI.
Provides Lua syntax highlighting for text widgets.
"""

import tkinter as tk
from tkinter import font
import re

class LuaSyntaxHighlighter:
    """Provides syntax highlighting for Lua code in tkinter Text widgets."""
    
    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget
        self.setup_tags()
        
    def setup_tags(self):
        """Configure text tags for syntax highlighting."""
        # Get the current font
        current_font = font.Font(font=self.text_widget['font'])
        bold_font = current_font.copy()
        bold_font.configure(weight='bold')
        
        # Define color scheme (dark theme friendly)
        self.text_widget.tag_configure('keyword', foreground='#569CD6', font=bold_font)
        self.text_widget.tag_configure('string', foreground='#CE9178')
        self.text_widget.tag_configure('comment', foreground='#6A9955', font=('TkDefaultFont', 10, 'italic'))
        self.text_widget.tag_configure('number', foreground='#B5CEA8')
        self.text_widget.tag_configure('function', foreground='#DCDCAA')
        self.text_widget.tag_configure('operator', foreground='#D4D4D4')
        self.text_widget.tag_configure('normal', foreground='#D4D4D4')
        
        # Lua keywords
        self.keywords = {
            'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for',
            'function', 'if', 'in', 'local', 'nil', 'not', 'or', 'repeat',
            'return', 'then', 'true', 'until', 'while'
        }
        
        # Lua built-in functions
        self.builtins = {
            'assert', 'collectgarbage', 'dofile', 'error', 'getfenv', 'getmetatable',
            'ipairs', 'load', 'loadfile', 'loadstring', 'next', 'pairs', 'pcall',
            'print', 'rawequal', 'rawget', 'rawset', 'require', 'select', 'setfenv',
            'setmetatable', 'tonumber', 'tostring', 'type', 'unpack', 'xpcall',
            'string', 'table', 'math', 'io', 'os', 'debug'
        }
        
    def highlight_syntax(self, event=None):
        """Apply syntax highlighting to the entire text."""
        # Remove all existing tags
        for tag in ['keyword', 'string', 'comment', 'number', 'function', 'operator']:
            self.text_widget.tag_remove(tag, '1.0', 'end')
        
        content = self.text_widget.get('1.0', 'end-1c')
        
        # Highlight comments first (so they take precedence)
        self._highlight_comments(content)
        
        # Highlight strings
        self._highlight_strings(content)
        
        # Highlight numbers
        self._highlight_numbers(content)
        
        # Highlight keywords and functions
        self._highlight_keywords(content)
        
        # Highlight operators
        self._highlight_operators(content)
    
    def _highlight_comments(self, content):
        """Highlight Lua comments."""
        # Single line comments
        for match in re.finditer(r'--.*$', content, re.MULTILINE):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            self.text_widget.tag_add('comment', start_idx, end_idx)
        
        # Multi-line comments
        for match in re.finditer(r'--\[\[.*?\]\]', content, re.DOTALL):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            self.text_widget.tag_add('comment', start_idx, end_idx)
    
    def _highlight_strings(self, content):
        """Highlight Lua strings."""
        # Single quoted strings
        for match in re.finditer(r"'(?:[^'\\]|\\.)*'", content):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            self.text_widget.tag_add('string', start_idx, end_idx)
        
        # Double quoted strings
        for match in re.finditer(r'"(?:[^"\\]|\\.)*"', content):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            self.text_widget.tag_add('string', start_idx, end_idx)
        
        # Long strings
        for match in re.finditer(r'\[\[.*?\]\]', content, re.DOTALL):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            self.text_widget.tag_add('string', start_idx, end_idx)
    
    def _highlight_numbers(self, content):
        """Highlight Lua numbers."""
        # Integers and floats
        for match in re.finditer(r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b', content):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            self.text_widget.tag_add('number', start_idx, end_idx)
        
        # Hexadecimal numbers
        for match in re.finditer(r'\b0[xX][0-9a-fA-F]+\b', content):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            self.text_widget.tag_add('number', start_idx, end_idx)
    
    def _highlight_keywords(self, content):
        """Highlight Lua keywords and built-in functions."""
        # Keywords
        for keyword in self.keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            for match in re.finditer(pattern, content):
                start_idx = self._get_text_index(content, match.start())
                end_idx = self._get_text_index(content, match.end())
                self.text_widget.tag_add('keyword', start_idx, end_idx)
        
        # Built-in functions
        for builtin in self.builtins:
            pattern = r'\b' + re.escape(builtin) + r'\b'
            for match in re.finditer(pattern, content):
                start_idx = self._get_text_index(content, match.start())
                end_idx = self._get_text_index(content, match.end())
                self.text_widget.tag_add('function', start_idx, end_idx)
    
    def _highlight_operators(self, content):
        """Highlight Lua operators."""
        operators = ['+', '-', '*', '/', '%', '^', '#', '==', '~=', '<=', '>=', 
                    '<', '>', '=', '(', ')', '{', '}', '[', ']', ';', ':', ',', '.', '..', '...']
        
        for op in operators:
            pattern = re.escape(op)
            for match in re.finditer(pattern, content):
                start_idx = self._get_text_index(content, match.start())
                end_idx = self._get_text_index(content, match.end())
                self.text_widget.tag_add('operator', start_idx, end_idx)
    
    def _get_text_index(self, content, char_index):
        """Convert character index to tkinter text index (line.column)."""
        lines = content[:char_index].split('\n')
        line_num = len(lines)
        col_num = len(lines[-1])
        return f"{line_num}.{col_num}"

class SimpleTextHighlighter:
    """Simple syntax highlighter for result display."""
    
    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget
        self.setup_tags()
    
    def setup_tags(self):
        """Setup basic highlighting tags."""
        self.text_widget.tag_configure('json_key', foreground='#9CDCFE')
        self.text_widget.tag_configure('json_string', foreground='#CE9178')
        self.text_widget.tag_configure('json_number', foreground='#B5CEA8')
        self.text_widget.tag_configure('json_bool', foreground='#569CD6')
        self.text_widget.tag_configure('json_null', foreground='#569CD6')
        self.text_widget.tag_configure('lua_key', foreground='#9CDCFE')
        self.text_widget.tag_configure('lua_string', foreground='#CE9178')
        self.text_widget.tag_configure('lua_number', foreground='#B5CEA8')
        self.text_widget.tag_configure('lua_bool', foreground='#569CD6')
        self.text_widget.tag_configure('lua_nil', foreground='#569CD6')
    
    def highlight_json(self):
        """Highlight JSON syntax."""
        content = self.text_widget.get('1.0', 'end-1c')
        
        # Clear existing tags
        for tag in ['json_key', 'json_string', 'json_number', 'json_bool', 'json_null']:
            self.text_widget.tag_remove(tag, '1.0', 'end')
        
        # Highlight JSON strings (including keys)
        for match in re.finditer(r'"[^"]*"', content):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            # Check if it's a key (followed by :)
            if match.end() < len(content) and content[match.end():match.end()+1].strip().startswith(':'):
                self.text_widget.tag_add('json_key', start_idx, end_idx)
            else:
                self.text_widget.tag_add('json_string', start_idx, end_idx)
        
        # Highlight numbers
        for match in re.finditer(r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b', content):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            self.text_widget.tag_add('json_number', start_idx, end_idx)
        
        # Highlight booleans and null
        for match in re.finditer(r'\b(true|false|null)\b', content):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            if match.group(1) == 'null':
                self.text_widget.tag_add('json_null', start_idx, end_idx)
            else:
                self.text_widget.tag_add('json_bool', start_idx, end_idx)
    
    def highlight_lua(self):
        """Highlight Lua table syntax."""
        content = self.text_widget.get('1.0', 'end-1c')
        
        # Clear existing tags
        for tag in ['lua_key', 'lua_string', 'lua_number', 'lua_bool', 'lua_nil']:
            self.text_widget.tag_remove(tag, '1.0', 'end')
        
        # Highlight Lua strings
        for match in re.finditer(r'"[^"]*"', content):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            # Check if it's a key (inside brackets)
            before_match = content[:match.start()].strip()
            if before_match.endswith('['):
                self.text_widget.tag_add('lua_key', start_idx, end_idx)
            else:
                self.text_widget.tag_add('lua_string', start_idx, end_idx)
        
        # Highlight numbers
        for match in re.finditer(r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b', content):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            self.text_widget.tag_add('lua_number', start_idx, end_idx)
        
        # Highlight booleans and nil
        for match in re.finditer(r'\b(true|false|nil)\b', content):
            start_idx = self._get_text_index(content, match.start())
            end_idx = self._get_text_index(content, match.end())
            if match.group(1) == 'nil':
                self.text_widget.tag_add('lua_nil', start_idx, end_idx)
            else:
                self.text_widget.tag_add('lua_bool', start_idx, end_idx)
    
    def _get_text_index(self, content, char_index):
        """Convert character index to tkinter text index (line.column)."""
        lines = content[:char_index].split('\n')
        line_num = len(lines)
        col_num = len(lines[-1])
        return f"{line_num}.{col_num}"
