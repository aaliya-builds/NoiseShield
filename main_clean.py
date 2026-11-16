import customtkinter as ctk
from tkinter import messagebox
import sounddevice as sd 
import numpy as np
from pywebrtc_audio import AudioProcessor
import queue
import threading
import json
from pathlib import Path
from datetime import datetime 

from deepfilternet_rs import DeepFilterNetRealtime  

SETTINGS_FILE = Path(__file__).with_name("noiseshield_settings.json")


def load_preferences():
    defaults = {
        "remember_preferences": True,
        "appearance_mode": "Dark",
        "noise_suppression": True,
        "noise_reduction": 100.0,
    }

    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults

    if not isinstance(saved, dict):
        return defaults

    if not saved.get("remember_preferences", True):
        defaults["remember_preferences"] = False
        return defaults

    appearance_mode = saved.get("appearance_mode", "Dark")
    if appearance_mode not in ("Dark", "Light", "System"):
        appearance_mode = "Dark"

    try:
        noise_reduction = float(saved.get("noise_reduction", 100.0))
    except (TypeError, ValueError):
        noise_reduction = 100.0

    defaults.update({
        "appearance_mode": appearance_mode,
        "noise_suppression": bool(saved.get("noise_suppression", True)),
        "noise_reduction": max(0.0, min(100.0, noise_reduction)),
    })

    return defaults


saved_preferences = load_preferences()

def save_preferences():
    if remember_preferences_switch.get():
        preferences = {
            "remember_preferences": True,
            "appearance_mode": appearance_mode_dropdown.get(),
            "noise_suppression": bool(use_noise_suppression),
            "noise_reduction": float(deepfilter_atten_lim),
        }
    else:
        preferences = {
            "remember_preferences": False
        }

    try:
        SETTINGS_FILE.write_text(
            json.dumps(preferences, indent=4),
            encoding="utf-8"
        )
    except OSError as error:
        print(f"Could not save NoiseShield preferences: {error}")

def change_appearance_mode(choice):
    ctk.set_appearance_mode(choice.lower())
    save_preferences()

def toggle_remember_preferences():
    save_preferences()

def reset_settings():
    global use_noise_suppression, deepfilter_atten_lim

    if status_label.cget("text") == "● Active":
        messagebox.showwarning(
            "Protection Active",
            "Stop Protection before resetting settings.",
            parent=app
        )
        return

    confirm = messagebox.askyesno(
        "Reset Settings",
        "Restore all settings to their default values?",
        parent=app
    )

    if not confirm:
        return

    appearance_mode_dropdown.set("Dark")
    ctk.set_appearance_mode("dark")

    use_noise_suppression = True
    noise_switch.select()
    settings_noise_switch.select()

    noise_status_label.configure(
        text="Noise Suppression: ON",
        text_color=get_theme_color("accent")
    )

    deepfilter_atten_lim = 100.0
    noise_slider.set(100)
    settings_noise_slider.set(100)

    noise_value_label.configure(text="100")
    settings_noise_value_label.configure(text="100")

    remember_preferences_switch.select()

    save_preferences()

    messagebox.showinfo(
        "Settings Reset",
        "All settings have been restored to their default values.",
        parent=app
    )

ctk.set_appearance_mode(saved_preferences["appearance_mode"].lower())

THEMES = {
    "dark": {
        "main_bg": "#0B1220",
        "sidebar": "#061426",
        "nav_active": "#163047",
        "power_bg": "#0B292D",
        "power_hover": "#12413F",
        "nav_hover": "#163047",
        "control_button": "#40D9C0",
        "control_hover": "#2BBFA8",
        "slider_hover": "#2BBFA8",
        "switch_button": "#F1F5F9",
        "switch_hover": "#D9E5EF",
        "card": "#111E30",
        "border": "#263B52",
        "text": "#F1F5F9",
        "muted": "#A8B8CC",
        "warning": "#FBBF24",
        "accent": "#40D9C0",
    },
    "light": {
        "main_bg": "#F1F5F9",
        "sidebar": "#FFFFFF",
        "nav_active": "#E0F2F1",
        "power_bg": "#CCFBF1",
        "power_hover": "#99F6E4",
        "nav_hover": "#F1F5F9",
        "control_button": "#0D9488",
        "control_hover": "#0F766E",
        "slider_hover": "#0F766E",
        "switch_button": "#FFFFFF",
        "switch_hover": "#E2E8F0", 
        "card": "#FFFFFF",
        "border": "#D7E0EA",
        "text": "#172334",
        "muted": "#64748B",
        "warning": "#B45309",
        "accent": "#0D9488",
    }
}

current_theme = "dark" 

def get_theme_color(color_name):
    return (THEMES["light"][color_name], THEMES["dark"][color_name])

activity_logs = []  

def add_activity_log(event):
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")

    activity_logs.append({
        "event": event,
        "time": timestamp
    })

    total_events_value.configure(
        text=str(len(activity_logs))
    )

    sessions_count = sum(
        1 for log in activity_logs
        if log["event"] == "Protection started"
    )

    sessions_value.configure(
        text=str(sessions_count)
    ) 

    errors_count = sum(
        1 for log in activity_logs
        if log["event"] == "Protection failed"
    )

    errors_value.configure(
        text=str(errors_count)
    ) 

    activity_name.configure(
        text="\n\n".join(
            f'{log["event"]} - {log["time"]}'
            for log in reversed(activity_logs)
        )
    ) 


def clear_activity_logs():
    activity_logs.clear()

    total_events_value.configure(text="0")
    sessions_value.configure(text="0")
    errors_value.configure(text="0")

    activity_name.configure(text="No recent activity")


app = ctk.CTk()

app.title("NoiseShield")
app.geometry("1200x800")    
app.minsize(1000, 700)

# Main Dashboard Layout
app.grid_columnconfigure(0, weight=0)
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)

sidebar = ctk.CTkFrame(
    app, 
    width=220, 
    corner_radius=0,
    fg_color=get_theme_color("sidebar") 
    )
sidebar.grid(row=0, column=0, sticky="nsw")
sidebar.grid_propagate(False)

sidebar_title = ctk.CTkLabel(
    sidebar,
    text="◈ NoiseShield",
    font=("Segoe UI", 23, "bold"), 
    text_color=get_theme_color("accent")
)
sidebar_title.pack(pady=(30, 5), padx=15)

sidebar_subtitle = ctk.CTkLabel(
    sidebar,
    text="VOICE PROTECTION",
    font=("Segoe UI", 10, "bold"), 
    text_color=get_theme_color("muted")
)
sidebar_subtitle.pack(pady=(0, 25))
 
menu_title = ctk.CTkLabel(
    sidebar,
    text="WORKSPACE",
    font=("Segoe UI", 11, "bold"),
    text_color=get_theme_color("muted")
)
menu_title.pack(anchor="w", padx=20, pady=(10, 12))

sidebar_buttons = {} 
def sidebar_item(text, page_name):
    item = ctk.CTkButton(
        sidebar,
        text=text,
        height=44,
        anchor="w",
        font=("Segoe UI", 14),
        fg_color="transparent",
        hover_color=get_theme_color("nav_hover"),
        text_color=get_theme_color("text"),
        corner_radius=10,
        command=lambda: show_page(page_name)
    )
    item.pack(fill="x", padx=12, pady=4)
    sidebar_buttons[page_name] = item 


sidebar_item("⌂   Home", "Home")
sidebar_item("◷   Live Activity", "Live Activity")
sidebar_item("▤   Devices", "Devices")
sidebar_item("☷   Logs", "Logs")
sidebar_item("⚙   Settings", "Settings")
sidebar_item("ⓘ   About", "About")


# Page navigation setup
pages = {}

def show_page(page_name):
    for name, page in pages.items():
        page.grid_forget()

    pages[page_name].grid(row=0, column=0, sticky="nsew")

    for name, button in sidebar_buttons.items():
        if name == page_name:
            button.configure(
                fg_color=get_theme_color("nav_active"),
                text_color=get_theme_color("accent")
            )
        else:
            button.configure(
                fg_color="transparent",
                text_color=get_theme_color("text")
            ) 


sidebar_footer = ctk.CTkFrame(
    sidebar,
    fg_color=get_theme_color("card"), 
    corner_radius=16,
    border_width=1,
    border_color=get_theme_color("border")
)
sidebar_footer.pack(
    side="bottom",
    fill="x",
    padx=12,
    pady=20
)

footer_icon = ctk.CTkLabel(
    sidebar_footer,
    text="🛡",
    font=("Segoe UI", 27),
    text_color=get_theme_color("accent")
)
footer_icon.pack(pady=(12, 4))

footer_text = ctk.CTkLabel(
    sidebar_footer,
    text="Clear voice.\nZero distractions.",
    font=("Segoe UI", 12, "bold"),
    text_color=get_theme_color("text")
)
footer_text.pack(pady=(0, 12))



main_container = ctk.CTkFrame(
    app,
    corner_radius=0,
    fg_color=get_theme_color("main_bg") 
)
main_container.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=15,
    pady=15
)
main_container.grid_columnconfigure(0, weight=1)
main_container.grid_rowconfigure(0, weight=1)

main_area = ctk.CTkScrollableFrame(
    main_container,
    fg_color=get_theme_color("main_bg"), 
    corner_radius=0
)
main_area.grid(row=0, column=0, sticky="nsew")
main_area.grid_columnconfigure((0, 1), weight=1)

pages["Home"] = main_area 


# Create the remaining application pages
for page_name in ("Live Activity", "Devices", "Logs", "Settings", "About"):
    page = ctk.CTkScrollableFrame(
        main_container,
        fg_color=get_theme_color("main_bg"),  
        corner_radius=0
    )
    page.grid_columnconfigure(0, weight=1)
    pages[page_name] = page

    page_title = ctk.CTkLabel(
        page,
        text=page_name,
        font=("Segoe UI", 28, "bold"),
        text_color=get_theme_color("text") 
    )
    page_title.grid(
        row=0,
        column=0,
        sticky="w",
        padx=25,
        pady=(25, 10)
    )


    if page_name == "Live Activity":
        
        overview_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        overview_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=25,
            pady=15
        )
        overview_frame.grid_columnconfigure(0, weight=1)

        overview_title = ctk.CTkLabel(
            overview_frame,
            text="Protection Overview",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        overview_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(18, 8)
        )

        overview_status = ctk.CTkLabel(
            overview_frame,
            text="● Inactive",
            font=("Segoe UI", 15),
            text_color=get_theme_color("muted")
        )
        overview_status.grid(
            row=1,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 18)
        ) 
        mic_activity_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        mic_activity_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=25,
            pady=10
        )
        mic_activity_frame.grid_columnconfigure(0, weight=1)

        mic_activity_title = ctk.CTkLabel(
            mic_activity_frame,
            text="Microphone Activity",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        mic_activity_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(18, 8)
        )

        mic_activity_status = ctk.CTkLabel(
            mic_activity_frame,
            text="Microphone monitoring is inactive",
            font=("Segoe UI", 14),
            text_color=get_theme_color("muted")
        )
        mic_activity_status.grid(
            row=1,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 18)
        ) 
        output_activity_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        output_activity_frame.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=25,
            pady=10
        )
        output_activity_frame.grid_columnconfigure(0, weight=1)

        output_activity_title = ctk.CTkLabel(
            output_activity_frame,
            text="Output Activity",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        output_activity_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(18, 8)
        )

        output_activity_status = ctk.CTkLabel(
            output_activity_frame,
            text="Audio output is inactive",
            font=("Segoe UI", 14),
            text_color=get_theme_color("muted")
        )
        output_activity_status.grid(
            row=1,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 18)
        )  

        processing_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        processing_frame.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=25,
            pady=10
        )
        processing_frame.grid_columnconfigure(0, weight=1)

        processing_title = ctk.CTkLabel(
            processing_frame,
            text="Processing Status",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        processing_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(18, 8)
        )

        processing_status = ctk.CTkLabel(
            processing_frame,
            text="Audio processing is stopped",
            font=("Segoe UI", 14),
            text_color=get_theme_color("muted")
        )
        processing_status.grid(
            row=1,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 18)
        ) 

        session_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"), 
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        session_frame.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=25,
            pady=10
        )
        session_frame.grid_columnconfigure(0, weight=1)

        session_title = ctk.CTkLabel(
            session_frame,
            text="Session Information",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        session_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(18, 8)
        )

        session_status = ctk.CTkLabel(
            session_frame,
            text="No active protection session",
            font=("Segoe UI", 14),
            text_color=get_theme_color("muted")
        )
        session_status.grid(
            row=1,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 18)
        )   
    
    if page_name == "Devices":
        devices_info = ctk.CTkLabel(
            page,
            text="Manage your audio devices",
            font=("Segoe UI", 14),
            text_color=get_theme_color("muted")
        )
        devices_info.grid(
            row=1,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 20)
        )

        devices_mic_label = ctk.CTkLabel(
            page,
            text="Available microphones",
            font=("Segoe UI", 16, "bold"),
            text_color=get_theme_color("text")
        )
        devices_mic_label.grid(
            row=2,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 8)
        )

        devices_mic_dropdown = ctk.CTkComboBox(
            page,
            values=["Loading microphones..."],
            width=400,
            font=("Segoe UI", 13),
            dropdown_font=("Segoe UI", 12),
            fg_color=get_theme_color("card"),
            border_color=get_theme_color("border"),
            button_color=get_theme_color("control_button"),
            button_hover_color=get_theme_color("control_hover"),
            text_color=get_theme_color("text"),
            dropdown_fg_color=get_theme_color("card"),
            corner_radius=10
        )
        devices_mic_dropdown.grid(
            row=3,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 20)
        )

        devices_output_label = ctk.CTkLabel(
            page,
            text="Audio Output",
            font=("Segoe UI", 16, "bold"),
            text_color=get_theme_color("text")
        )
        devices_output_label.grid(
            row=4,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 8)
        )

        devices_output_info = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"), 
            corner_radius=14,
            border_width=1,
            border_color=get_theme_color("border")
        )
        devices_output_info.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 20)
        )

        devices_output_text = ctk.CTkLabel(
            devices_output_info,
            text="VB-CABLE (CABLE Input)\nUsed for processed audio output",
            font=("Segoe UI", 13),
            text_color=get_theme_color("accent"),
            justify="left"
        )
        devices_output_text.pack(
            anchor="w",
            padx=18,
            pady=18
        ) 

        devices_output_label = ctk.CTkLabel(
            page,
            text="Available Output Devices",
            font=("Segoe UI", 15, "bold"),
            text_color=get_theme_color("text") 
        )
        devices_output_label.grid(
            row=6,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 8)
        )

        devices_output_dropdown = ctk.CTkComboBox(
            page,
            values=["Loading output devices..."],
            width=400,
            height=40,
            fg_color=get_theme_color("card"),
            border_color=get_theme_color("border"),
            text_color=get_theme_color("text"),
            button_color=get_theme_color("control_button"),
            button_hover_color=get_theme_color("control_hover"), 
            dropdown_fg_color=get_theme_color("card"),
            dropdown_text_color=get_theme_color("text"),
            corner_radius=10 
        )
        devices_output_dropdown.grid(
            row=7,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 20)
        )

        output_status_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=12,
            border_width=1,
            border_color=get_theme_color("border")
        )
        output_status_frame.grid(
            row=8,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 15)
        )

        output_status_label = ctk.CTkLabel(
            output_status_frame,
            text="● Selected output is shown above", 
            font=("Segoe UI", 12),
            text_color=get_theme_color("accent"),
            anchor="w"
        )
        output_status_label.pack(
            anchor="w",
            padx=16,
            pady=14
        ) 

    if page_name == "Logs":
        logs_info = ctk.CTkLabel(
            page,
            text="View your NoiseShield activity and protection history.",
            font=("Segoe UI", 14),
            text_color=get_theme_color("muted")
        )
        logs_info.grid(
            row=1,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 20)
        ) 
        summary_title = ctk.CTkLabel(
            page,
            text="Activity Summary",
            font=("Segoe UI", 20, "bold"),
            text_color=get_theme_color("text")
        )
        summary_title.grid(
            row=2,
            column=0,
            sticky="w",
            padx=25,
            pady=(10, 15)
        ) 
        summary_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        summary_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 20)
        )
        summary_frame.grid_columnconfigure(
            (0, 1, 2),
            weight=1
        ) 
        total_events_card = ctk.CTkFrame(
            summary_frame,
            fg_color=get_theme_color("card"),
            corner_radius=14
        )
        total_events_card.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(15, 8),
            pady=15
        )  
        total_events_label = ctk.CTkLabel(
            total_events_card,
            text="Total Events",
            font=("Segoe UI", 13),
            text_color=get_theme_color("muted")
        )
        total_events_label.pack(
            anchor="w",
            padx=15,
            pady=(15, 5)
        ) 
        total_events_value = ctk.CTkLabel(
            total_events_card,
            text="0",
            font=("Segoe UI", 28, "bold"),
            text_color=get_theme_color("accent")
        )
        total_events_value.pack(
            anchor="w",
            padx=15,
            pady=(0, 15)
        ) 
        sessions_card = ctk.CTkFrame(
            summary_frame,
            fg_color=get_theme_color("card"),
            corner_radius=14
        )
        sessions_card.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=15
        ) 
        sessions_label = ctk.CTkLabel(
            sessions_card,
            text="Protection Sessions",
            font=("Segoe UI", 13),
            text_color=get_theme_color("muted")
        )
        sessions_label.pack(
            anchor="w",
            padx=15,
            pady=(15, 5)
        ) 
        sessions_value = ctk.CTkLabel(
            sessions_card,
            text="0",
            font=("Segoe UI", 28, "bold"),
            text_color=get_theme_color("accent")
        )
        sessions_value.pack(
            anchor="w",
            padx=15,
            pady=(0, 15)
        ) 
        errors_card = ctk.CTkFrame(
            summary_frame,
            fg_color=get_theme_color("card"),
            corner_radius=14
        )
        errors_card.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(8, 15),
            pady=15
        ) 
        errors_label = ctk.CTkLabel(
            errors_card,
            text="Errors",
            font=("Segoe UI", 13),
            text_color=get_theme_color("muted")
        )
        errors_label.pack(
            anchor="w",
            padx=15,
            pady=(15, 5)
        ) 
        errors_value = ctk.CTkLabel(
            errors_card,
            text="0",
            font=("Segoe UI", 28, "bold"),
            text_color="#F87171"
        )
        errors_value.pack(
            anchor="w",
            padx=15,
            pady=(0, 15)
        ) 
        recent_activity_title = ctk.CTkLabel(
            page,
            text="Recent Activity",
            font=("Segoe UI", 20, "bold"),
            text_color=get_theme_color("text")
        )
        recent_activity_title.grid(
            row=4,
            column=0,
            sticky="w",
            padx=25,
            pady=(10, 15)
        ) 
        recent_activity_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        recent_activity_frame.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 20)
        )
        recent_activity_frame.grid_columnconfigure(0, weight=1)

        activity_entry = ctk.CTkFrame(
            recent_activity_frame,
            fg_color=get_theme_color("card"),
            corner_radius=12
        )
        activity_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=15,
            pady=15
        )
        activity_entry.grid_columnconfigure(0, weight=1)

        activity_name = ctk.CTkLabel(
            activity_entry,
            text="No recent activity",
            font=("Segoe UI", 14, "bold"),
            text_color=get_theme_color("text")
        )
        activity_name.grid(
            row=0,
            column=0,
            sticky="w",
            padx=15,
            pady=12
        ) 

        clear_logs_button = ctk.CTkButton(
            recent_activity_frame,
            text="Clear Logs",
            width=120,
            height=36,
            fg_color="#7F1D1D",
            hover_color="#991B1B",
            text_color="#FFFFFF",
            font=("Segoe UI", 12, "bold"),
            corner_radius=8,
            command=clear_activity_logs
        )
        clear_logs_button.grid(
            row=1,
            column=0,
            sticky="e",
            padx=15,
            pady=(0, 15)
        )  

    if page_name == "Settings":
        settings_info = ctk.CTkLabel(
            page,
            text="Customize your NoiseShield experience.",
            font=("Segoe UI", 14),
            text_color=get_theme_color("muted")
        )
        settings_info.grid(
            row=1,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 20)
        )  

        noise_settings_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        noise_settings_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=25,
            pady=10
        )

        noise_settings_title = ctk.CTkLabel(
            noise_settings_frame,
            text="Noise Reduction",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text") 
        )
        noise_settings_title.pack(
            anchor="w",
            padx=20,
            pady=(18, 5)
        )

        noise_settings_description = ctk.CTkLabel(
            noise_settings_frame,
            text="Adjust the noise reduction level from the Home dashboard.",
            font=("Segoe UI", 13),
            text_color=get_theme_color("muted")
        )
        noise_settings_description.pack(
            anchor="w",
            padx=20,
            pady=(0, 18)
        )

        settings_noise_switch = ctk.CTkSwitch(
            noise_settings_frame,
            text="Enable Noise Suppression",
            font=("Segoe UI", 14),
            text_color=get_theme_color("text"), 
            progress_color=get_theme_color("accent"),
            button_color=get_theme_color("switch_button"),
            button_hover_color=get_theme_color("switch_hover"),
            onvalue=1,
            offvalue=0,
        command=lambda: toggle_noise_suppression(settings_noise_switch) 
        )

        if saved_preferences["noise_suppression"]:
            settings_noise_switch.select()
        else:
            settings_noise_switch.deselect()
        settings_noise_switch.pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        ) 

        settings_noise_value_label = ctk.CTkLabel(
            noise_settings_frame,
            text=str(int(saved_preferences["noise_reduction"])),
            width=300, 
            font=("Segoe UI", 16, "bold"),
            text_color=get_theme_color("accent")
        )

        settings_noise_value_label.pack(
            anchor="w",
            padx=20, 
            pady=(0, 5)
        )   

        settings_noise_slider = ctk.CTkSlider(
            noise_settings_frame,
            from_=0,
            to=100,
            width=300,
            progress_color=get_theme_color("accent"),
            button_color=get_theme_color("accent"),
            button_hover_color=get_theme_color("slider_hover"),
            command=lambda value: update_noise_level(value)
        )
        settings_noise_slider.set(saved_preferences["noise_reduction"])
        settings_noise_slider.pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        ) 
        appearance_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        appearance_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=25,
            pady=10
        )
        appearance_title = ctk.CTkLabel(
            appearance_frame,
            text="Appearance Mode",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        appearance_title.pack(anchor="w", padx=20, pady=(18, 5))

        appearance_description = ctk.CTkLabel(
            appearance_frame,
            text="Choose Dark, Light, or follow your system settings.",
            font=("Segoe UI", 13),
            text_color=get_theme_color("muted")
        )
        appearance_description.pack(anchor="w", padx=20, pady=(0, 12))

        appearance_mode_dropdown = ctk.CTkComboBox(
            appearance_frame,
            values=["Dark", "Light", "System"],
            width=300,
            font=("Segoe UI", 14),
            dropdown_font=("Segoe UI", 14),
            fg_color=get_theme_color("card"),
            border_color=get_theme_color("border"),
            button_color=get_theme_color("control_button"),
            button_hover_color=get_theme_color("control_hover"),
            text_color=get_theme_color("text"),
            dropdown_fg_color=get_theme_color("card"),
            dropdown_text_color=get_theme_color("text"),
            corner_radius=10,
            command=change_appearance_mode 
        )
        appearance_mode_dropdown.set(saved_preferences["appearance_mode"])
        appearance_mode_dropdown.pack(anchor="w", padx=20, pady=(0, 20))

        remember_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        remember_frame.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=25,
            pady=10
        )

        remember_title = ctk.CTkLabel(
            remember_frame,
            text="Remember Preferences",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        remember_title.pack(anchor="w", padx=20, pady=(18, 5))

        remember_description = ctk.CTkLabel(
            remember_frame,
            text="Save your settings so they are restored when you reopen NoiseShield.",
            font=("Segoe UI", 13),
            text_color=get_theme_color("muted")
        )
        remember_description.pack(anchor="w", padx=20, pady=(0, 12))

        remember_preferences_switch = ctk.CTkSwitch(
            remember_frame,
            text="Remember my preferences",
            font=("Segoe UI", 14),
            text_color=get_theme_color("text"),
            progress_color=get_theme_color("accent"),
            button_color=get_theme_color("switch_button"),
            button_hover_color=get_theme_color("switch_hover"),
            onvalue=1,
            offvalue=0,
            command=toggle_remember_preferences
        )
        if saved_preferences["remember_preferences"]:
            remember_preferences_switch.select()
        else:
            remember_preferences_switch.deselect()
        remember_preferences_switch.pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        )

        reset_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        reset_frame.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=25,
            pady=10
        )

        reset_title = ctk.CTkLabel(
            reset_frame,
            text="Reset Settings",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        reset_title.pack(
            anchor="w",
            padx=20,
            pady=(18, 5)
        )

        reset_description = ctk.CTkLabel(
            reset_frame,
            text="Restore all settings to their default values.",
            font=("Segoe UI", 13),
            text_color=get_theme_color("muted")
        )
        reset_description.pack(
            anchor="w",
            padx=20,
            pady=(0, 12)
        )

        reset_button = ctk.CTkButton(
            reset_frame,
            text="Reset All Settings",
            width=180,
            height=38,
            font=("Segoe UI", 13, "bold"),
            fg_color="#B91C1C",
            hover_color="#991B1B",
            text_color="#FFFFFF",
            corner_radius=10,
            command=reset_settings
        )
        reset_button.pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        )

    if page_name == "About":

        about_info_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        about_info_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=25,
            pady=(10, 12)
        )

        about_info_title = ctk.CTkLabel(
            about_info_frame,
            text="NoiseShield",
            font=("Segoe UI", 22, "bold"),
            text_color=get_theme_color("accent")
        )
        about_info_title.pack(
            anchor="w",
            padx=20,
            pady=(18, 5)
        )

        about_info_version = ctk.CTkLabel(
            about_info_frame,
            text="Version 0.1.0  •  Development Build",
            font=("Segoe UI", 12, "bold"),
            text_color=get_theme_color("muted")
        )
        about_info_version.pack(
            anchor="w",
            padx=20,
            pady=(0, 10)
        )

        about_info_description = ctk.CTkLabel(
            about_info_frame,
            text=(
                "A desktop voice-protection app that reduces "
                "background noise from microphone audio in real "
                "time and routes the processed voice to a "
                "virtual audio output."
            ),
            font=("Segoe UI", 13),
            text_color=get_theme_color("muted"),
            wraplength=650,
            justify="left",
            anchor="w"
        )
        about_info_description.pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        )

        about_features_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        about_features_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=25,
            pady=12
        )

        about_features_title = ctk.CTkLabel(
            about_features_frame,
            text="Key Features",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        about_features_title.pack(
            anchor="w",
            padx=20,
            pady=(18, 12)
        )

        features = (
            "Real-time background-noise reduction",
            "Noise Suppression ON/OFF control",
            "Adjustable noise reduction level (0–100)",
            "Microphone and virtual audio device information",
            "Saved preferences and Reset Settings",
            "Activity, session and error logs"
        )

        for feature in features:
            feature_label = ctk.CTkLabel(
                about_features_frame,
                text=f"•  {feature}",
                font=("Segoe UI", 13),
                text_color=get_theme_color("muted"),
                anchor="w"
            )
            feature_label.pack(
                anchor="w",
                padx=22,
                pady=5
            )

        about_features_frame.configure(
            height=300
        )

        about_work_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        about_work_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=25,
            pady=12
        )

        about_work_title = ctk.CTkLabel(
            about_work_frame,
            text="How It Works",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        about_work_title.pack(
            anchor="w",
            padx=20,
            pady=(18, 12)
        )

        work_steps = (
            "1. Microphone captures your voice and surrounding sounds.",
            "2. The noise reduction engine processes the audio in real time.",
            "3. Processed audio is sent to the virtual audio output.",
            "4. Select CABLE Output as your microphone in a meeting app."
        )

        for step in work_steps:
            step_label = ctk.CTkLabel(
                about_work_frame,
                text=step,
                font=("Segoe UI", 13),
                text_color=get_theme_color("muted"),
                anchor="w",
                justify="left",
                wraplength=650
            )
            step_label.pack(
                anchor="w",
                padx=22,
                pady=6
            )

        about_work_frame.configure(
            height=250
        )

        about_tech_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        about_tech_frame.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=25,
            pady=12
        )

        about_tech_title = ctk.CTkLabel(
            about_tech_frame,
            text="Technology",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        about_tech_title.pack(
            anchor="w",
            padx=20,
            pady=(18, 12)
        )

        technologies = (
            "Python 3.12 — Core programming language",
            "CustomTkinter — Desktop user interface",
            "sounddevice — Audio input and output",
            "NumPy — Audio data and numerical processing",
            "DeepFilterNet — Real-time noise reduction engine",
            "VB-CABLE — Virtual audio routing"
        )

        for technology in technologies:
            technology_label = ctk.CTkLabel(
                about_tech_frame,
                text=f"•  {technology}",
                font=("Segoe UI", 13),
                text_color=get_theme_color("muted"),
                anchor="w",
                justify="left",
                wraplength=650
            )
            technology_label.pack(
                anchor="w",
                padx=22,
                pady=5
            )

        about_tech_frame.configure(
            height=300
        )

        about_credits_frame = ctk.CTkFrame(
            page,
            fg_color=get_theme_color("card"),
            corner_radius=18,
            border_width=1,
            border_color=get_theme_color("border")
        )
        about_credits_frame.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=25,
            pady=12
        )

        about_credits_title = ctk.CTkLabel(
            about_credits_frame,
            text="Credits & License",
            font=("Segoe UI", 18, "bold"),
            text_color=get_theme_color("text")
        )
        about_credits_title.pack(
            anchor="w",
            padx=20,
            pady=(18, 12)
        )

        license_items = (
            "CustomTkinter — MIT License",
            "sounddevice — MIT License",
            "NumPy — BSD 3-Clause License",
            "deepfilternet-rs — MIT License",
            "DeepFilterNet upstream components — MIT or Apache 2.0",
            "pywebrtc-audio — Apache 2.0 License",
            "VB-CABLE — Donationware (external audio driver)",
            "NoiseShield — Application license not yet assigned"
        )

        for item in license_items:
            license_label = ctk.CTkLabel(
                about_credits_frame,
                text=f"•  {item}",
                font=("Segoe UI", 12),
                text_color=get_theme_color("muted"),
                anchor="w",
                justify="left",
                wraplength=650
            )
            license_label.pack(
                anchor="w",
                padx=22,
                pady=5
            )

        about_credits_note = ctk.CTkLabel(
            about_credits_frame,
            text=(
                "Third-party components remain subject to "
                "their respective license terms."
            ),
            font=("Segoe UI", 11, "italic"),
            text_color=get_theme_color("muted"),
            wraplength=650,
            justify="left"
        )
        about_credits_note.pack(
            anchor="w",
            padx=20,
            pady=(10, 18)
        )

        
mic_status_frame = ctk.CTkFrame(
    pages["Devices"],
    fg_color=get_theme_color("card"),
    corner_radius=12,
    border_width=1,
    border_color=get_theme_color("border")
)
mic_status_frame.grid(
    row=9, 
    column=0,
    sticky="ew",
    padx=25,
    pady=(0, 15)
)

mic_status_label = ctk.CTkLabel(
    mic_status_frame,
    text="Selected microphone:",
    font=("Segoe UI", 12),
    text_color=get_theme_color("muted"),
    anchor="w"
)
mic_status_label.pack(
    side="left",
    padx=(16, 6),
    pady=14
)

mic_status_name = ctk.CTkLabel(
    mic_status_frame,
    text="Not selected",
    font=("Segoe UI", 12, "bold"),
    text_color=get_theme_color("accent"),
    anchor="w"
)
mic_status_name.pack(
    side="left",
    pady=14
) 



right_panel = ctk.CTkFrame(
    main_area,
    fg_color="transparent"
)
right_panel.grid(
    row=3,
    column=1,
    rowspan=4,
    sticky="nsew",
    padx=(10, 25),
    pady=15
)
right_panel.grid_columnconfigure(0, weight=1)



# Central Protection Panel
hero_frame = ctk.CTkFrame(
    main_area,
    fg_color=get_theme_color("card"),
    corner_radius=24,
    border_width=1,
    border_color=get_theme_color("border")
)
hero_frame.grid(
    row=3,
    column=0,
    sticky="ew",
    padx=(25, 10),
    pady=15
)

hero_frame.grid_columnconfigure(0, weight=1)

hero_title = ctk.CTkLabel(
    hero_frame,
    text="Noise Protection",
    font=("Segoe UI", 28, "bold"),
    text_color=get_theme_color("text")
)
hero_title.pack(pady=(26, 6))

hero_subtitle = ctk.CTkLabel(
    hero_frame,
    text="Your voice, clear and focused",
    font=("Segoe UI", 14),
    text_color=get_theme_color("muted")
)
hero_subtitle.pack(pady=(0, 20))


hero_power_button = ctk.CTkButton(
    hero_frame,
    text="⏻",
    width=110,
    height=110,
    corner_radius=55,
    font=("Segoe UI", 42, "bold"),
    fg_color=get_theme_color("power_bg"),
    hover_color=get_theme_color("power_hover"),
    border_width=2,
    border_color=get_theme_color("accent"),
    text_color=get_theme_color("accent"),
    command=lambda: toggle_protection()
)
hero_power_button.pack(pady=(5, 15))

hero_status = ctk.CTkLabel(
    hero_frame,
    text="● Ready to protect",
    font=("Segoe UI", 15, "bold"),
    text_color=get_theme_color("accent")
)
hero_status.pack(pady=(0, 26))


device_card = ctk.CTkFrame(
    right_panel,
    fg_color=get_theme_color("card"),
    corner_radius=18,
    border_width=1,
    border_color=get_theme_color("border")
)
device_card.grid(
    row=0,
    column=0,
    sticky="ew",
    pady=(0, 12)
)

device_title = ctk.CTkLabel(
    device_card,
    text="Device Information",
    font=("Segoe UI", 17, "bold"),
    text_color=get_theme_color("text")
)
device_title.pack(anchor="w", padx=18, pady=(18, 10))

device_label = ctk.CTkLabel(
    device_card,
    text="Audio input and output",
    font=("Segoe UI", 13),
    text_color=get_theme_color("muted")
)
device_label.pack(anchor="w", padx=18, pady=(0, 18))


quick_card = ctk.CTkFrame(
    right_panel,
    fg_color=get_theme_color("card"),
    corner_radius=18,
    border_width=1,
    border_color=get_theme_color("border")
)
quick_card.grid(
    row=1,
    column=0,
    sticky="ew",
    pady=(0, 12)
) 

quick_title = ctk.CTkLabel(
    quick_card,
    text="Quick Info",
    font=("Segoe UI", 17, "bold"),
    text_color=get_theme_color("text")
)
quick_title.pack(anchor="w", padx=18, pady=(18, 10))

quick_text = ctk.CTkLabel(
    quick_card,
    text="• Choose your microphone\n• Adjust noise reduction\n• Start protection when ready",
    font=("Segoe UI", 13),
    text_color=get_theme_color("muted"),
    justify="left"
)
quick_text.pack(anchor="w", padx=18, pady=(0, 18))

logs_card = ctk.CTkFrame(
    right_panel,
    fg_color=get_theme_color("card"),
    corner_radius=18,
    border_width=1,
    border_color=get_theme_color("border")
)
logs_card.grid(
    row=2,
    column=0,
    sticky="ew",
    pady=(0, 12)
)

logs_title = ctk.CTkLabel(
    logs_card,
    text="Protection Guide",
    font=("Segoe UI", 17, "bold"),
    text_color=get_theme_color("text")
)
logs_title.pack(anchor="w", padx=18, pady=(18, 10))

logs_text = ctk.CTkLabel(
    logs_card,
    text="Protection is off until you start it.",
    font=("Segoe UI", 13),
    text_color=get_theme_color("muted"),
    wraplength=240,
    justify="left"
)
logs_text.pack(anchor="w", padx=18, pady=(0, 18))



welcome_label = ctk.CTkLabel(
    main_area,
    text="Welcome back",
    font=("Segoe UI", 14),
    text_color=get_theme_color("muted")
)
welcome_label.grid(
    row=0,
    column=0,
    columnspan=2,
    sticky="w",
    padx=25,
    pady=(20, 0)
)

title = ctk.CTkLabel(
    main_area,
    text="NoiseShield",
    font=("Segoe UI", 30, "bold"),
    text_color=get_theme_color("text")
)

title.grid(
    row=1,
    column=0,
    columnspan=2,
    sticky="w",
    padx=25,
    pady=(5, 0)
)


tagline = ctk.CTkLabel(
    main_area,
    text="Clear voice. Zero distractions.",
    font=("Segoe UI", 14),
    text_color=get_theme_color("muted")
)

tagline.grid(
    row=2,
    column=0,
    columnspan=2,
    sticky="w",
    padx=25,
    pady=(40, 15)
) 

status_frame = ctk.CTkFrame(
    main_area,
    fg_color=get_theme_color("card"),
    corner_radius=18,
    border_width=1,
    border_color=get_theme_color("border")
)

status_frame.grid(
    row=4,
    column=0,
    sticky="ew",
    padx=(25, 10),
    pady=15 
)

status_title = ctk.CTkLabel(
    status_frame,
    text="Protection Status",
    font=("Segoe UI", 17, "bold"),
    text_color=get_theme_color("text")
)

status_title.pack(pady=(18, 6))

status_label = ctk.CTkLabel(
    status_frame,
    text="● Inactive",
    font=("Segoe UI", 14, "bold"),
    text_color=get_theme_color("muted")
)

status_label.pack(pady=(0, 15))

def audio_callback(indata, frames, time, status):
    if status:
        print(status)

    audio = indata[:, 0].copy()

    if use_noise_suppression: 
        try:
            deepfilter_queue.put_nowait(audio)
        except queue.Full:
            try:
                deepfilter_queue.get_nowait()
            except queue.Empty:
                pass

            try:
                deepfilter_queue.put_nowait(audio)
            except queue.Full:
                pass 

    else:
        try:
            deepfilter_output_queue.put_nowait(audio)
        except queue.Full:
            try:
                deepfilter_output_queue.get_nowait()
            except queue.Empty:
                pass

            try:
                deepfilter_output_queue.put_nowait(audio)
            except queue.Full:
                pass



def output_callback(outdata, frames, time, status):
    global output_buffer

    if status:
        print(status)

    while len(output_buffer) < frames:
        try:
            enhanced = deepfilter_output_queue.get_nowait()
        except queue.Empty:
            break

        enhanced = np.asarray(enhanced, dtype=np.float32).reshape(-1)

        if enhanced.size:
            output_buffer = np.concatenate((output_buffer, enhanced))

    if len(output_buffer) >= frames:
        outdata[:, 0] = output_buffer[:frames]
        output_buffer = output_buffer[frames:]
    else:
        outdata.fill(0) 


def toggle_protection():
    global audio_stream, audio_output_stream, deepfilter_running, deepfilter_thread

    if status_label.cget("text") == "● Inactive":
        selected_output = devices_output_dropdown.get().strip()
        valid_outputs = get_output_devices()

        if not selected_output or selected_output not in valid_outputs:
            output_status_label.configure(
                text="● VB-CABLE not detected. Protection cannot start.",
                text_color=get_theme_color("warning")
            )
            add_activity_log("Protection failed") 
            return

        selected_mic = mic_dropdown.get().strip()
        try:
            device_index = int(selected_mic.split(":")[0])
            output_device_index = int(selected_output.split(":")[0])
        except (ValueError, IndexError):
            output_status_label.configure(
                text="Select a valid microphone and VB-CABLE output.",
                text_color=get_theme_color("warning")
            )
            add_activity_log("Protection failed") 
            return

        try:
            # Start the audio streams first; only mark protection active if both work.
            audio_stream = sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=48000,
                blocksize=480,
                dtype="float32",
                callback=audio_callback
            )
            audio_stream.start()

            audio_output_stream = sd.OutputStream(
                device=output_device_index,
                samplerate=48000,
                channels=1,
                blocksize=480,
                dtype="float32",
                latency="low", 
                callback=output_callback
            )
            audio_output_stream.start()

            print("Input stream latency:", audio_stream.latency)    #latency checking 
            print("Output stream latency:", audio_output_stream.latency)  #latency checking

            deepfilter_running = True
            deepfilter_thread = threading.Thread(
                target=deepfilter_worker,
                daemon=True
            )
            deepfilter_thread.start()

        except Exception as error:
            deepfilter_running = False
            if audio_stream is not None:
                try:
                    audio_stream.stop()
                    audio_stream.close()
                except Exception:
                    pass
                audio_stream = None
            if audio_output_stream is not None:
                try:
                    audio_output_stream.stop()
                    audio_output_stream.close()
                except Exception:
                    pass
                audio_output_stream = None
            print(f"Could not start NoiseShield audio: {error}")
            add_activity_log("Protection failed") 
            status_label.configure(text="● Inactive", text_color=get_theme_color("muted"))
            start_button.configure(text="Start Protection")
            hero_status.configure(text="● Audio setup failed — see terminal", text_color=get_theme_color("warning"))
            return

        status_label.configure(text="● Active", text_color=get_theme_color("accent"))
        overview_status.configure(text="● Active", text_color=get_theme_color("accent"))
        mic_activity_status.configure(
            text="Microphone monitoring is active",
            text_color=get_theme_color("accent")
        ) 
        start_button.configure(text="Stop Protection")
        hero_power_button.configure(text="⏻", fg_color="#B91C1C")
        hero_status.configure(text="● Protection Active", text_color="#10B981")
        output_status_label.configure(
            text="● Active — processed audio is sent to VB-CABLE",
            text_color=get_theme_color("accent")
        )
        output_activity_status.configure(
            text="● Processed audio is active",
            text_color=get_theme_color("accent")
        ) 
        processing_status.configure(
            text="● Audio processing is running",
            text_color=get_theme_color("accent")
        ) 
        session_status.configure(
            text="● Protection session is active",
            text_color=get_theme_color("accent")
        ) 
        add_activity_log("Protection started") 

    else:
        deepfilter_running = False

        if audio_stream is not None:
            try:
                audio_stream.stop()
                audio_stream.close()
            except Exception as error:
                print(f"Error closing microphone stream: {error}")
            audio_stream = None

        if audio_output_stream is not None:
            try:
                audio_output_stream.stop()
                audio_output_stream.close()
            except Exception as error:
                print(f"Error closing output stream: {error}")
            audio_output_stream = None

        if deepfilter_thread is not None:
            deepfilter_thread.join(timeout=2)
            deepfilter_thread = None

        with deepfilter_queue.mutex:
            deepfilter_queue.queue.clear()
        with deepfilter_output_queue.mutex:
            deepfilter_output_queue.queue.clear()

        deepfilter_atten_lim = 100.0 
        status_label.configure(text="● Inactive", text_color=get_theme_color("muted"))
        overview_status.configure(text="● Inactive", text_color=get_theme_color("muted"))
        mic_activity_status.configure(
            text="Microphone monitoring is inactive",
            text_color=get_theme_color("muted")
        ) 
        start_button.configure(text="Start Protection")
        hero_power_button.configure(fg_color=get_theme_color("power_bg"))
        hero_status.configure(text="● Ready to protect", text_color=get_theme_color("muted"))
        output_status_label.configure(
            text="● VB-CABLE selected — processed audio goes to CABLE Output",
            text_color=get_theme_color("accent")
        ) 
        output_activity_status.configure(
            text="● Audio output is inactive",
            text_color=get_theme_color("muted")
        ) 
        processing_status.configure(
            text="Audio processing is stopped",
            text_color=get_theme_color("muted")
        ) 
        session_status.configure(
            text="No active protection session",
            text_color=get_theme_color("muted")
        ) 
        add_activity_log("Protection stopped") 
 


def get_microphones():

    microphones = []

    for index, device in enumerate(sd.query_devices()):

        if device["max_input_channels"] > 0:
            microphones.append(f"{index}: {device['name']}")

    return microphones 

def get_output_devices():
    # NoiseShield must send processed audio to VB-CABLE, not the headphones.
    output_devices = []

    for index, device in enumerate(sd.query_devices()):
        name = device["name"].lower()
        is_virtual_cable = (
            "cable input" in name
            or "cable in" in name
            or ("vb-audio" in name and "cable" in name and "input" in name)
        )
        if device["max_output_channels"] > 0 and is_virtual_cable:
            output_devices.append(f"{index}: {device['name']}")

    return output_devices

audio_stream = None 
audio_output_stream =None
output_buffer = np.empty(0, dtype=np.float32)
use_noise_suppression = bool(saved_preferences["noise_suppression"])


deepfilter_queue = queue.Queue(maxsize=4)
deepfilter_output_queue = queue.Queue(maxsize=4)

deepfilter_running = False
deepfilter_thread = None
deepfilter_atten_lim = float(saved_preferences["noise_reduction"])

def deepfilter_worker():
    global deepfilter_running

    processor = DeepFilterNetRealtime(
        model_path=None,
        atten_lim=deepfilter_atten_lim,
        log_level="warn",
        compensate_delay=True,
        post_filter_beta=0.0,
    )

    print("DeepFilterNet AI worker ready")

    while deepfilter_running:
        try:
            audio = deepfilter_queue.get(timeout=0.1)
        except queue.Empty:
            continue
 
        if use_noise_suppression:
            enhanced = processor.process_chunk(audio)
        else:
            enhanced = audio 

        try:
            deepfilter_output_queue.put_nowait(enhanced)

        except queue.Full:

            try:
                deepfilter_output_queue.get_nowait()
            except queue.Empty:
                pass

            try:
                deepfilter_output_queue.put_nowait(enhanced)
            except queue.Full:
                pass 

    processor.close()

    print("DeepFilterNet AI worker stopped")



audio_processor = AudioProcessor(
    sample_rate=16000,
    num_channels=1,
    noise_suppression=True,
    echo_cancellation=False,
    auto_gain_control=False,
    ns_level=3
)


start_button = ctk.CTkButton(
    main_area,
    text="Start Protection",
    width=220,
    height=48,
    font=("Segoe UI", 15, "bold"),
    fg_color=get_theme_color("control_button"),
    hover_color=get_theme_color("control_hover"), 
    text_color=get_theme_color("text"),
    corner_radius=12, 
    command=toggle_protection 
)

start_button.grid(
    row=5,
    column=0,
    sticky="ew",
    padx=(25, 10),
    pady=15
)


mic_frame = ctk.CTkFrame(
    main_area,
    fg_color=get_theme_color("card"),
    corner_radius=18,
    border_width=1,
    border_color=get_theme_color("border") 
)

mic_frame.grid(
    row=6,
    column=0,
    sticky="ew",
    padx=(25, 10),
    pady=10
)

mic_title = ctk.CTkLabel(
    mic_frame,
    text="Microphone",
    font=("Segoe UI", 15, "bold"),
    text_color=get_theme_color("text")
)

mic_title.pack(pady=(10, 5))

mic_dropdown = ctk.CTkComboBox(
    mic_frame,
    values=get_microphones(),
    font=("Segoe UI", 13),
    dropdown_font=("Segoe UI", 12),
    fg_color=get_theme_color("card"),
    border_color=get_theme_color("border"),
    button_color=get_theme_color("control_button"), 
    button_hover_color=get_theme_color("control_hover"),
    text_color=get_theme_color("text"),
    corner_radius=10 
)

mic_dropdown.pack(pady=(0, 10))  

available_mics = get_microphones()
devices_mic_dropdown.configure(values=available_mics)
devices_mic_dropdown.set(mic_dropdown.get())

available_outputs = get_output_devices()
devices_output_dropdown.configure(
    values=available_outputs if available_outputs else ["VB-CABLE not detected"]
)

preferred_output = next(
    (device for device in available_outputs
     if "cable input" in device.lower() 
     and sd.query_hostapis(
            sd.query_devices(int(device.split(":")[0]))["hostapi"]
        )["name"] == "Windows WASAPI"
    ),
    available_outputs[0] if available_outputs else ""
)

if preferred_output:
    devices_output_dropdown.set(preferred_output)
    output_status_label.configure(
        text="● VB-CABLE selected — processed audio goes to CABLE Output",
        text_color=get_theme_color("accent")
    )
else:
    devices_output_dropdown.set("VB-CABLE not detected")
    output_status_label.configure(
        text="● VB-CABLE not detected. Protection cannot start.",
        text_color=get_theme_color("warning")
    )

def update_output_status(choice):
    if choice in get_output_devices():
        output_status_label.configure(
            text="● VB-CABLE selected — processed audio goes to CABLE Output",
            text_color=get_theme_color("accent")
        )
    else:
        output_status_label.configure(
            text="● VB-CABLE not detected. Protection cannot start.",
            text_color=get_theme_color("warning")
        )

devices_output_dropdown.configure(command=update_output_status)

def sync_microphone_choice(choice):
    mic_dropdown.set(choice) 
    devices_mic_dropdown.set(choice)
    mic_status_name.configure(text=choice) 
    mic_activity_status.configure(text=f"Selected microphone: {choice}")
    

devices_mic_dropdown.configure(command=sync_microphone_choice)
mic_dropdown.configure(command=sync_microphone_choice) 

noise_frame = ctk.CTkFrame(
    main_area,
    fg_color=get_theme_color("card"),
    corner_radius=18,
    border_width=1,
    border_color=get_theme_color("border") 
)

noise_frame.grid(
    row=7,
    column=0,
    sticky="ew",
    padx=(25, 10),
    pady=10 
)

noise_title = ctk.CTkLabel(
    noise_frame,
    text="Noise Reduction",
    font=("Segoe UI", 15, "bold"),
    text_color=get_theme_color("text") 
) 

noise_title.pack(pady=(10, 5))

noise_status_label = ctk.CTkLabel(
    noise_frame,
    text=("Noise Suppression: ON" if saved_preferences["noise_suppression"] else "Noise Suppression: OFF"),
    font=("Segoe UI", 12, "bold"),
    text_color=(get_theme_color("accent") if saved_preferences["noise_suppression"] else "#F59E0B")
)

noise_status_label.pack(pady=(5, 5))


def toggle_noise_suppression(source):
    global use_noise_suppression

    use_noise_suppression = bool(source.get())

    if use_noise_suppression:
        noise_switch.select()
        settings_noise_switch.select()

        noise_status_label.configure(
            text="Noise Suppression: ON",
            text_color=get_theme_color("accent")
        )

    else:
        noise_switch.deselect()
        settings_noise_switch.deselect()

        noise_status_label.configure(
            text="Noise Suppression: OFF",
            text_color="#F59E0B"
        ) 

    save_preferences()


noise_switch = ctk.CTkSwitch(
    noise_frame,
    text="Enable Noise Suppression",
    command=lambda: toggle_noise_suppression(noise_switch),
    onvalue=1,
    offvalue=0,
    progress_color=get_theme_color("accent"),
    button_color=get_theme_color("switch_button"),
    button_hover_color=get_theme_color("switch_hover"),
    text_color=get_theme_color("text")
)

if saved_preferences["noise_suppression"]:
    noise_switch.select()
else:
    noise_switch.deselect()
noise_switch.pack(pady=(5, 10))  


noise_value_label = ctk.CTkLabel(
    noise_frame,
    text=str(int(saved_preferences["noise_reduction"])), 
    font=("Segoe UI", 16, "bold"),
    text_color=get_theme_color("accent") 
)

noise_value_label.pack(pady=(0, 5))


def update_noise_level(value):
    global deepfilter_atten_lim

    deepfilter_atten_lim  = float(value)

    noise_value_label.configure(
        text=str(int(float(value)))
    )

    settings_noise_value_label.configure(
        text=str(int(float(value)))
    ) 

    noise_slider.set(value)
    settings_noise_slider.set(value) 
    save_preferences()


noise_slider = ctk.CTkSlider(
    noise_frame,
    from_=0,
    to=100,
    width=300,
    progress_color=get_theme_color("accent"),
    button_color=get_theme_color("accent"),
    button_hover_color=get_theme_color("slider_hover"), 
    command=update_noise_level 
)

noise_slider.set(saved_preferences["noise_reduction"]) 

noise_slider.pack(pady=(8, 20)) 

def close_app():
    if status_label.cget("text") == "● Active":
        toggle_protection()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", close_app)

show_page("Home") 
app.mainloop() 


