import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageGrab
import cv2
import mediapipe as mp
import pyautogui
import time
import threading

# --- Configurations ---
VIDEO_WIDTH, VIDEO_HEIGHT = 640, 480
PROCESSING_WIDTH, PROCESSING_HEIGHT = 320, 180

gesture_actions = [
    ('Move Cursor', 'Index + Middle up'),
    ('Freeze Cursor', 'Thumb + Index + Middle up'),
    ('Scroll Up', 'Thumb + Index + Middle + Ring up'),
    ('Scroll Down', 'Thumb + Index + Middle + Pinky up'),
    ('Left Click', 'Only Middle finger up'),
    ('Right Click', 'Only Index finger up'),
    ('Double Click', 'Both Index + Middle fingers down'),
    ('Screenshot', 'All fingers up')
]

# --- Colors & Fonts with final adjustments ---
BG_COLOR = "#FBFBFE"
PANEL_BG_COLOR = "#E3EBF7"
VIDEO_BG_COLOR = "#F9F9FB"
TITLE_COLOR = "#2072AF"
STATUS_TEXT_COLOR = "#6c757d" 
SENS_TITLE_COLOR = "#4A4E69" 
SENS_VALUE_COLOR = "#3a86ff"
BAR_COLOR = "#EAEAEA"
BUTTON_COLOR = "#ffbe0b"
BUTTON_TEXT = "#374151"
GESTURE_TITLE_COLOR = "#000000"
ACTION_NAME_COLOR = "#005f73"
DESC_COLOR = "#333333"
FONT_FAMILY = "Crimson Pro"

class GestureApp:
    def __init__(self, root):
        self.root = root
        root.title("Virtual Mouse Controller")
        root.configure(bg=BG_COLOR)
        self.is_running = True
        
        root.geometry('1010x740')
        
        self.style = ttk.Style(root)
        self.style.theme_use('default')
        self.style.configure("red.Horizontal.TProgressbar", troughcolor=BAR_COLOR, background='#d9534f', thickness=20)
        self.style.configure("yellow.Horizontal.TProgressbar", troughcolor=BAR_COLOR, background='#f0ad4e', thickness=20)
        self.style.configure("green.Horizontal.TProgressbar", troughcolor=BAR_COLOR, background='#5cb85c', thickness=20)
        self.style.configure("gray.Horizontal.TProgressbar", troughcolor=BAR_COLOR, background='#cccccc', thickness=20)

        # 1. Main container for the left side
        main_left_panel = tk.Frame(root, bg=BG_COLOR)
        main_left_panel.pack(side='left', fill='y', padx=10, pady=10, anchor='n')

        # 2. Frame for the TOP controls
        controls_frame = tk.Frame(main_left_panel, bg=BG_COLOR)
        controls_frame.pack(side='top', anchor='w')

        self.cooldown_var = tk.DoubleVar(value=0)
        self.cooldown_bar = ttk.Progressbar(
            controls_frame, orient='horizontal', length=400, mode='determinate',
            variable=self.cooldown_var, maximum=100,
            style="gray.Horizontal.TProgressbar"
        )
        self.cooldown_bar.pack(side='top', anchor='w', pady=(0, 4))
        self.func_text_var = tk.StringVar(value="Ready")
        self.func_text_label = tk.Label(
            controls_frame, textvariable=self.func_text_var, font=(FONT_FAMILY, 15, 'bold'),
            bg=BG_COLOR, fg=STATUS_TEXT_COLOR 
        )
        self.func_text_label.pack(side='top', anchor='w', padx=4, pady=(6, 4))
        
        sens_title_container = tk.Frame(main_left_panel, bg=BG_COLOR)
        sens_title_container.pack(side='top', anchor='w', fill='x', pady=(15, 5))
        
        tk.Label(
            sens_title_container, text="Mouse Sensitivity:", font=(FONT_FAMILY, 14, "bold"),
            bg=BG_COLOR, fg=SENS_TITLE_COLOR
        ).pack(side='left', padx=(2, 10))

        sens_slider_container = tk.Frame(main_left_panel, bg=BG_COLOR)
        sens_slider_container.pack(side='top', anchor='w')
        
        btn_minus = tk.Button(
            sens_slider_container, text='–', font=(FONT_FAMILY, 13, 'bold'),
            width=2, command=self.decrement_sensitivity,
            bg=BUTTON_COLOR, fg=BUTTON_TEXT, relief='flat', bd=0, highlightthickness=0, activebackground="#ffdd6b"
        )
        btn_minus.pack(side='left', padx=(0, 4))
        self.sens_var = tk.DoubleVar(value=2.2)
        self.sens_slider = tk.Scale(
            sens_slider_container, from_=1, to=5, orient='horizontal', variable=self.sens_var,
            showvalue=False, resolution=0.1, length=200,
            bg=VIDEO_BG_COLOR, fg=TITLE_COLOR, troughcolor=BAR_COLOR,
            activebackground=SENS_VALUE_COLOR, highlightthickness=0, relief='flat', sliderrelief='flat'
        )
        self.sens_slider.pack(side='left', padx=(0, 4))
        btn_plus = tk.Button(
            sens_slider_container, text='+', font=(FONT_FAMILY, 13, 'bold'),
            width=2, command=self.increment_sensitivity,
            bg=BUTTON_COLOR, fg=BUTTON_TEXT, relief='flat', bd=0, highlightthickness=0, activebackground="#ffdd6b"
        )
        btn_plus.pack(side='left', padx=(0, 10))
        self.sens_val_lbl = tk.Label(
            sens_slider_container, text=f"{self.sens_var.get():.1f}",
            font=(FONT_FAMILY, 12, 'bold'), bg=BG_COLOR, fg=SENS_VALUE_COLOR
        )
        self.sens_val_lbl.pack(side='left')
        self.sens_var.trace("w", lambda *a: self.sens_val_lbl.config(text=f"{self.sens_var.get():.1f}"))
        
        # --- NEW: Add a hint for new users to prevent misactions ---
        hint_text = "Hint: Start with the 'Move Cursor' gesture (Index + Middle up). Hold gestures clearly to prevent accidental actions, like a loose fist triggering Double Click."
        hint_label = tk.Label(
            main_left_panel,
            text=hint_text,
            font=(FONT_FAMILY, 10, 'bold italic'),
            bg=BG_COLOR,
            fg="#c75b0a", 
            wraplength=600,
            justify='center'
        )
        hint_label.pack(side='top', anchor='center', pady=(15, 0), padx=4)

        # 3. CV Window
        video_frame = tk.Frame(main_left_panel, bd=2, relief='groove', bg=VIDEO_BG_COLOR)
        video_frame.pack(side='top', pady=(20, 0))
        
        self.vid_label = tk.Label(video_frame, bg=VIDEO_BG_COLOR)
        self.vid_label.pack(padx=3, pady=3)

        # 4. Gesture Info Panel
        instr_frame = tk.Frame(root, bg=PANEL_BG_COLOR, width=280)
        instr_frame.pack(side='left', fill='y', padx=(10, 10), pady=10)
        
        tk.Label(
            instr_frame, text="Gesture Controls",
            font=(FONT_FAMILY, 20, "bold"),
            fg=GESTURE_TITLE_COLOR, bg=PANEL_BG_COLOR
        ).pack(pady=(50,40))
        for action, description in gesture_actions:
            tk.Label(
                instr_frame, text=f"{action}",
                anchor='w', justify='left',
                font=(FONT_FAMILY, 12,'bold'),
                bg=PANEL_BG_COLOR, fg=ACTION_NAME_COLOR, padx=15
            ).pack(fill='x', padx=1, pady=(2, 0))
            tk.Label(
                instr_frame, text=description,
                anchor='w', justify='left',
                font=(FONT_FAMILY, 11),
                bg=PANEL_BG_COLOR, fg=DESC_COLOR, padx=14
            ).pack(fill='x', padx=1, pady=(0, 7))

        # --- Gesture logic variables ---
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.show_camera_error_and_exit("Camera not found or cannot be opened.")
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
        self.screen_w, self.screen_h = pyautogui.size()
        self.anchor_hand_x = None
        self.last_click_time = 0
        self.click_delay = 1.0
        self.last_double_time = 0
        self.double_click_cooldown = 1.0
        self.last_scroll_time = 0
        self.scroll_cooldown = 3.0
        self.scroll_amount = 150
        self.last_screenshot_time = 0
        self.screenshot_cooldown = 3.0
        self.cooldown_end_time = 0
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        self.last_confirmed_hand = None
        self.candidate_hand = None
        self.hand_confirm_counter = 0
        self.HAND_CONFIRM_FRAMES = 3

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind('<Escape>', lambda e: self.on_close())
        self.update_video()

    def flash_slider_highlight(self):
        """Temporarily highlights the slider background to give user feedback."""
        highlight_color = SENS_VALUE_COLOR 
        default_color = VIDEO_BG_COLOR
        self.sens_slider.config(bg=highlight_color)
        self.root.after(200, lambda: self.sens_slider.config(bg=default_color))

    def increment_sensitivity(self):
        self.sens_var.set(min(5, round(self.sens_var.get() + 0.1, 1)))
        self.flash_slider_highlight()

    def decrement_sensitivity(self):
        self.sens_var.set(max(1, round(self.sens_var.get() - 0.1, 1)))
        self.flash_slider_highlight()

    def take_screenshot(self):
        try:
            image = ImageGrab.grab()
            filename = f"screenshot_{time.strftime('%Y%m%d-%H%M%S')}.png"
            image.save(filename)
            print(f"Screenshot saved as {filename}")
        except Exception as e:
            print(f"Screenshot failed: {e}")

    def update_video(self):
        if not self.is_running:
            return
        try:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.vid_label.config(
                    text="Webcam unavailable.",
                    fg='red', bg=VIDEO_BG_COLOR, font=(FONT_FAMILY, 12)
                )
                if self.is_running:
                    self.root.after(1000, self.update_video)
                return
            frame = cv2.flip(frame, 1)
            small_frame = cv2.resize(frame, (PROCESSING_WIDTH, PROCESSING_HEIGHT))
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_small_frame)
            action = None
            sensitivity = self.sens_var.get()
            if results and results.multi_hand_landmarks and results.multi_handedness:
                current_hand = results.multi_handedness[0].classification[0].label
                if self.last_confirmed_hand is None:
                    self.last_confirmed_hand = current_hand
                
                if current_hand == self.last_confirmed_hand:
                    self.hand_confirm_counter = 0
                    self.candidate_hand = None
                else:
                    if current_hand == self.candidate_hand:
                        self.hand_confirm_counter += 1
                    else:
                        self.candidate_hand = current_hand
                        self.hand_confirm_counter = 1
                
                if self.hand_confirm_counter >= self.HAND_CONFIRM_FRAMES:
                    self.last_confirmed_hand = self.candidate_hand
                    self.hand_confirm_counter = 0
                    self.candidate_hand = None

                is_left = (self.last_confirmed_hand == "Left")
                
                lmks = results.multi_hand_landmarks[0]
                x_thumb_tip = lmks.landmark[4].x
                x_thumb_ip = lmks.landmark[3].x
                
                if is_left:
                    thumb_up = int(x_thumb_tip > x_thumb_ip)
                else:
                    thumb_up = int(x_thumb_tip < x_thumb_ip)
                
                tip_ids = [8, 12, 16, 20]
                fingers = [thumb_up]
                for tip_id in tip_ids:
                    fingers.append(int(lmks.landmark[tip_id].y < lmks.landmark[tip_id - 2].y))
                thumb_up, index_up, middle_up, ring_up, pinky_up = fingers
                cur_time = time.time()

                if all([thumb_up, index_up, middle_up, ring_up, pinky_up]):
                    self.anchor_hand_x = None
                    if cur_time - self.last_screenshot_time > self.screenshot_cooldown:
                        threading.Thread(target=self.take_screenshot, daemon=True).start()
                        action = "Screenshot"
                        self.last_screenshot_time = cur_time
                        self.start_cooldown(self.screenshot_cooldown)
                elif thumb_up and index_up and middle_up and ring_up and not pinky_up:
                    self.anchor_hand_x = None
                    if cur_time - self.last_scroll_time > self.scroll_cooldown:
                        pyautogui.scroll(self.scroll_amount)
                        action = "Scroll Up"
                        self.last_scroll_time = cur_time
                        self.start_cooldown(self.scroll_cooldown)
                elif thumb_up and index_up and middle_up and not ring_up and pinky_up:
                    self.anchor_hand_x = None
                    if cur_time - self.last_scroll_time > self.scroll_cooldown:
                        pyautogui.scroll(-self.scroll_amount)
                        action = "Scroll Down"
                        self.last_scroll_time = cur_time
                        self.start_cooldown(self.scroll_cooldown)
                elif thumb_up and index_up and middle_up and not ring_up and not pinky_up:
                    self.anchor_hand_x = None
                    action = "Freeze Cursor"
                elif not thumb_up and index_up and middle_up and not ring_up and not pinky_up:
                    hand_px, hand_py = lmks.landmark[9].x * self.screen_w, lmks.landmark[9].y * self.screen_h
                    if self.anchor_hand_x is None:
                        self.anchor_hand_x, self.anchor_cursor_x = hand_px, pyautogui.position()[0]
                        self.anchor_hand_y, self.anchor_cursor_y = hand_py, pyautogui.position()[1]
                    dx = (hand_px - self.anchor_hand_x) * sensitivity
                    dy = (hand_py - self.anchor_hand_y) * sensitivity
                    pyautogui.moveTo(self.anchor_cursor_x + dx, self.anchor_cursor_y + dy, duration=0)
                    action = "Move Cursor"
                elif index_up and not middle_up and not ring_up and not pinky_up:
                    self.anchor_hand_x = None
                    if cur_time - self.last_click_time > self.click_delay:
                        pyautogui.click(button='right')
                        action = "Right Click"
                        self.last_click_time = cur_time
                        self.start_cooldown(self.click_delay)
                elif not index_up and middle_up and not ring_up and not pinky_up:
                    self.anchor_hand_x = None
                    if cur_time - self.last_click_time > self.click_delay:
                        pyautogui.click()
                        action = "Left Click"
                        self.last_click_time = cur_time
                        self.start_cooldown(self.click_delay)
                elif not index_up and not middle_up and not ring_up and not pinky_up:
                    self.anchor_hand_x = None
                    if cur_time - self.last_double_time > self.double_click_cooldown:
                        pyautogui.doubleClick()
                        action = "Double Click"
                        self.last_double_time = cur_time
                        self.start_cooldown(self.double_click_cooldown)
                else:
                    self.anchor_hand_x = None

                self.mp_draw.draw_landmarks(frame, lmks, self.mp_hands.HAND_CONNECTIONS)
            
            if action:
                self.func_text_var.set(action)
                if action in ["Move Cursor", "Freeze Cursor"] and self.cooldown_var.get() == 0:
                    self.cooldown_bar.config(style="gray.Horizontal.TProgressbar")
            else:
                if self.cooldown_var.get() == 0:
                    self.func_text_var.set("Ready")
                    self.cooldown_bar.config(style="gray.Horizontal.TProgressbar")
            
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)
            self.vid_label.imgtk = imgtk
            self.vid_label.configure(image=imgtk)
        except Exception as exc:
            print(f"An error occurred in the update loop: {exc}")
            if self.is_running:
                self.vid_label.config(text="An error occurred.", fg='red', bg=VIDEO_BG_COLOR, font=(FONT_FAMILY, 12))
        if self.is_running:
            self.root.after(10, self.update_video)

    def start_cooldown(self, duration):
        self.cooldown_var.set(100)
        self.cooldown_end_time = time.time() + duration
        self._cooldown_total = duration
        self.update_cooldown_bar()

    def update_cooldown_bar(self):
        remaining = self.cooldown_end_time - time.time()
        if remaining > 0:
            self.cooldown_var.set((remaining / self._cooldown_total) * 100)
            
            progress_percentage = (self._cooldown_total - remaining) / self._cooldown_total
            
            if progress_percentage < 0.5:
                self.cooldown_bar.config(style="red.Horizontal.TProgressbar")
            elif progress_percentage < 0.8:
                self.cooldown_bar.config(style="yellow.Horizontal.TProgressbar")
            else:
                self.cooldown_bar.config(style="green.Horizontal.TProgressbar")

            self.root.after(50, self.update_cooldown_bar)
        else:
            self.cooldown_var.set(0)
            self.cooldown_bar.config(style="gray.Horizontal.TProgressbar")

    def show_camera_error_and_exit(self, msg):
        top = tk.Toplevel(self.root)
        top.title("Webcam Error")
        tk.Label(top, text=msg, fg='red', font=(FONT_FAMILY, 12)).pack(padx=20, pady=20)
        tk.Button(top, text="Exit", command=self.on_close, bg=BUTTON_COLOR, fg=BUTTON_TEXT,
                  relief='flat', font=(FONT_FAMILY, 10)).pack(pady=10)
        self.root.withdraw()

    def on_close(self):
        if not self.is_running:
            return
        print("Closing application...")
        self.is_running = False
        self.root.after(50, self.release_resources)

    def release_resources(self):
        if hasattr(self, "cap") and self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GestureApp(root)
    root.mainloop()
