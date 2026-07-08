import os
import sys
import time
import tkinter as tk
from tkinter import ttk
from pynput import keyboard

# Adjust path to import core and database modules
UI_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(UI_DIR)
sys.path.insert(0, PROJECT_ROOT)

from database import db_manager
from core.recommender import Recommender

class NotificationWindow:
    def __init__(self, product_ids):
        self.product_ids = product_ids
        
        # Initialize Recommender
        db_manager.init_db()
        self.recommender = Recommender()
        self.recommendations = self.recommender.get_recommendations(self.product_ids)
        
        # If no recommendations, exit immediately
        if not self.recommendations:
            print("[INFO] Nenhuma sugestão aplicável para este carrinho.")
            sys.exit(0)
            
        # UI configuration
        self.bg_color = "#0F172A"       # Deep dark blue
        self.card_color = "#1E293B"     # Slate gray/blue
        self.hover_color = "#334155"    # Lighter slate for hover
        self.accent_color = "#8B5CF6"   # Purple
        self.cyan_color = "#06B6D4"     # Cyan
        self.text_white = "#FFFFFF"     # White
        self.text_gray = "#94A3B8"      # Gray
        self.green_color = "#10B981"     # Emerald Green
        
        self.width = 380
        # Calculate height dynamically based on number of recommendations
        self.height = 140 + (len(self.recommendations) * 95)
        
        # Create root window
        self.root = tk.Tk()
        self.root.title("PdvApp Sugestões")
        
        # Configure borderless window
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=self.bg_color)
        
        # Apply neon border using a surrounding frame
        self.border_frame = tk.Frame(self.root, bg=self.accent_color, bd=2)
        self.border_frame.pack(fill=tk.BOTH, expand=True)
        
        self.main_frame = tk.Frame(self.border_frame, bg=self.bg_color)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Setup coordinates
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        self.x = self.screen_width - self.width - 25
        self.y_target = self.screen_height - self.height - 60  # Float above taskbar
        self.y_start = self.screen_height                      # Start offscreen
        
        # Start position
        self.root.geometry(f"{self.width}x{self.height}+{self.x}+{self.y_start}")
        self.root.attributes("-alpha", 0.0)
        
        # Build UI Elements
        self._build_header()
        self._build_cards()
        self._build_footer()
        
        # Setup hotkeys
        self.root.bind("<F1>", lambda e: self._select_recommendation(0))
        self.root.bind("<F2>", lambda e: self._select_recommendation(1))
        self.root.bind("<F3>", lambda e: self._select_recommendation(2))
        self.root.bind("<Escape>", lambda e: self._close_notification())
        
        # Hover state detection for pausing the timer
        self.timer_paused = False
        self.root.bind("<Enter>", self._on_window_enter)
        self.root.bind("<Leave>", self._on_window_leave)
        
        # Slide up and Fade in animation
        self.current_y = self.y_start
        self.current_alpha = 0.0
        self._animate_in()
        
        # Start countdown timer
        self.timeout_ms = 10000  # 10 seconds
        self.remaining_ms = self.timeout_ms
        self.last_timer_update = time.time()
        self._update_timer()
        
        self.root.mainloop()

    def _build_header(self):
        # Header Container
        header_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        header_frame.pack(fill=tk.X, padx=15, pady=(15, 5))
        
        # Accent category tip
        tip_label = tk.Label(
            header_frame, 
            text="💡 SUGESTÃO DE COMPLEMENTO", 
            font=("Inter", 9, "bold"), 
            fg=self.cyan_color, 
            bg=self.bg_color
        )
        tip_label.pack(anchor="w")
        
        # Main Title
        title_label = tk.Label(
            header_frame, 
            text="O cliente pode precisar de:", 
            font=("Inter", 13, "bold"), 
            fg=self.text_white, 
            bg=self.bg_color
        )
        title_label.pack(anchor="w", pady=(2, 0))
        
        # Subtitle or explanation
        subtitle_label = tk.Label(
            header_frame, 
            text="Pressione F1-F3 ou clique no card para bipar o item", 
            font=("Inter", 8, "italic"), 
            fg=self.text_gray, 
            bg=self.bg_color
        )
        subtitle_label.pack(anchor="w")
        
        # Divider Line
        divider = tk.Frame(self.main_frame, bg="#334155", height=1)
        divider.pack(fill=tk.X, padx=15, pady=8)

    def _build_cards(self):
        self.card_frames = []
        for idx, rec in enumerate(self.recommendations):
            hotkey_str = f"F{idx+1}"
            
            # Card Outer Frame
            card = tk.Frame(self.main_frame, bg=self.card_color, cursor="hand2")
            card.pack(fill=tk.X, padx=15, pady=4)
            self.card_frames.append(card)
            
            # Card contents layouts
            content_frame = tk.Frame(card, bg=self.card_color)
            content_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
            
            # Top row: Product Name and Price
            top_row = tk.Frame(content_frame, bg=self.card_color)
            top_row.pack(fill=tk.X)
            
            name_lbl = tk.Label(
                top_row, 
                text=rec["name"], 
                font=("Inter", 10, "bold"), 
                fg=self.text_white, 
                bg=self.card_color,
                anchor="w",
                justify="left",
                wraplength=210
            )
            name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            price_lbl = tk.Label(
                top_row, 
                text=f"R$ {rec['price']:.2f}", 
                font=("Inter", 11, "bold"), 
                fg=self.green_color, 
                bg=self.card_color,
                anchor="e"
            )
            price_lbl.pack(side=tk.RIGHT)
            
            # Mid row: Category and Hotkey tag
            mid_row = tk.Frame(content_frame, bg=self.card_color)
            mid_row.pack(fill=tk.X, pady=(2, 0))
            
            cat_lbl = tk.Label(
                mid_row, 
                text=f"{rec['category']} • Código: {rec['id']}", 
                font=("Inter", 8), 
                fg=self.text_gray, 
                bg=self.card_color
            )
            cat_lbl.pack(side=tk.LEFT)
            
            hotkey_lbl = tk.Label(
                mid_row, 
                text=f"[{hotkey_str}]", 
                font=("Inter", 8, "bold"), 
                fg=self.cyan_color, 
                bg=self.card_color
            )
            hotkey_lbl.pack(side=tk.RIGHT)
            
            # Bottom row: Trigger Explanation (Layer info)
            best_reason = rec["reasons"][0] if rec["reasons"] else "Recomendação inteligente"
            reason_lbl = tk.Label(
                content_frame, 
                text=best_reason, 
                font=("Inter", 7, "italic"), 
                fg=self.text_gray, 
                bg=self.card_color,
                anchor="w",
                justify="left",
                wraplength=320
            )
            reason_lbl.pack(fill=tk.X, pady=(4, 0))
            
            # Bind events to simulate click/hover on all widgets inside the card
            for widget in (card, content_frame, top_row, name_lbl, price_lbl, mid_row, cat_lbl, hotkey_lbl, reason_lbl):
                widget.bind("<Button-1>", lambda e, i=idx: self._select_recommendation(i))
                widget.bind("<Enter>", lambda e, i=idx: self._on_card_enter(i))
                widget.bind("<Leave>", lambda e, i=idx: self._on_card_leave(i))

    def _build_footer(self):
        # Progress bar container
        self.progress_canvas = tk.Canvas(
            self.main_frame, 
            bg=self.bg_color, 
            height=4, 
            highlightthickness=0
        )
        self.progress_canvas.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=(5, 12))
        
        # Draw background bar
        self.progress_canvas.create_rectangle(
            0, 0, self.width - 30, 4, 
            fill="#1E293B", 
            outline=""
        )
        
        # Draw dynamic bar
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, self.width - 30, 4, 
            fill=self.cyan_color, 
            outline=""
        )

    def _on_card_enter(self, index):
        card = self.card_frames[index]
        card.configure(bg=self.hover_color)
        for child in card.winfo_children():
            child.configure(bg=self.hover_color)
            for subchild in child.winfo_children():
                # Keep custom label colors
                try:
                    fg_color = subchild.cget("fg")
                    if fg_color not in (self.green_color, self.cyan_color, self.text_white):
                        subchild.configure(fg=self.text_white)
                except tk.TclError:
                    pass
                subchild.configure(bg=self.hover_color)

    def _on_card_leave(self, index):
        card = self.card_frames[index]
        card.configure(bg=self.card_color)
        for child in card.winfo_children():
            child.configure(bg=self.card_color)
            for subchild in child.winfo_children():
                try:
                    fg_color = subchild.cget("fg")
                    if fg_color not in (self.green_color, self.cyan_color):
                        # Restore text gray
                        if "name" in str(subchild) or subchild.cget("font") == ("Inter", 10, "bold"):
                            subchild.configure(fg=self.text_white)
                        else:
                            subchild.configure(fg=self.text_gray)
                except tk.TclError:
                    pass
                subchild.configure(bg=self.card_color)

    def _on_window_enter(self, event):
        self.timer_paused = True

    def _on_window_leave(self, event):
        self.timer_paused = False
        self.last_timer_update = time.time()

    def _animate_in(self):
        """Animates slide-up and fade-in."""
        step_y = 15
        step_alpha = 0.08
        
        if self.current_y > self.y_target or self.current_alpha < 1.0:
            self.current_y = max(self.y_target, self.current_y - step_y)
            self.current_alpha = min(1.0, self.current_alpha + step_alpha)
            
            self.root.geometry(f"{self.width}x{self.height}+{self.x}+{self.current_y}")
            self.root.attributes("-alpha", self.current_alpha)
            
            self.root.after(10, self._animate_in)

    def _animate_out(self, on_complete):
        """Animates slide-down and fade-out."""
        step_y = 18
        step_alpha = 0.1
        
        if self.current_y < self.y_start or self.current_alpha > 0.0:
            self.current_y = min(self.y_start, self.current_y + step_y)
            self.current_alpha = max(0.0, self.current_alpha - step_alpha)
            
            self.root.geometry(f"{self.width}x{self.height}+{self.x}+{self.current_y}")
            self.root.attributes("-alpha", self.current_alpha)
            
            self.root.after(10, lambda: self._animate_out(on_complete))
        else:
            on_complete()

    def _update_timer(self):
        """Updates countdown timer and shrinks progress bar."""
        now = time.time()
        elapsed_since_update = (now - self.last_timer_update) * 1000
        self.last_timer_update = now
        
        if not self.timer_paused:
            self.remaining_ms -= elapsed_since_update
            
            # Update visual progress bar width
            pct = max(0.0, self.remaining_ms / self.timeout_ms)
            max_width = self.width - 30
            current_width = max_width * pct
            self.progress_canvas.coords(self.progress_bar, 0, 0, current_width, 4)
            
        if self.remaining_ms <= 0:
            self._close_notification()
        else:
            self.root.after(30, self._update_timer)

    def _select_recommendation(self, index):
        """Processes selection of a recommended product and injects it into the active POS window."""
        if index >= len(self.recommendations):
            return
            
        selected_rec = self.recommendations[index]
        barcode = selected_rec["id"]
        
        print(f"\n[INTERATIVO] Sugestão selecionada: {selected_rec['name']} (Código: {barcode})")
        
        # Close notification window first (slide down)
        self._animate_out(on_complete=lambda: self._simulate_keyboard_injection(barcode))

    def _simulate_keyboard_injection(self, barcode):
        """Uses pynput to type the barcode digits and press Enter to register the item."""
        # Wait briefly for focus to return to POS application
        time.sleep(0.2)
        
        kb_controller = keyboard.Controller()
        
        # Type the barcode characters one by one with a tiny delay to simulate a real scanner wedge
        for char in barcode:
            kb_controller.press(char)
            kb_controller.release(char)
            time.sleep(0.01)
            
        # Press and release Enter
        kb_controller.press(keyboard.Key.enter)
        kb_controller.release(keyboard.Key.enter)
        
        print(f"[INTERATIVO] Injetado código {barcode} + Enter via emulador de teclado.")
        self.root.destroy()
        sys.exit(0)

    def _close_notification(self):
        self._animate_out(on_complete=self._destroy_and_exit)

    def _destroy_and_exit(self):
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    # Test arguments
    # Filter products IDs out of command line arguments
    product_args = [arg for arg in sys.argv[1:] if not arg.startswith('--') and not arg.endswith('.py') and not arg.endswith('.exe')]
    
    # Default fallback test list if no arguments passed (e.g. toilet 3001)
    if not product_args:
        product_args = ["3001"]
        
    print(f"Iniciando notificação de sugestões para carrinho: {product_args}")
    NotificationWindow(product_args)
