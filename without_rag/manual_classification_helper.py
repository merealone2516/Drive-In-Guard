import tkinter as tk
import logging

def prompt_manual_classification_gui(attempt, column: str) -> bool:
    result = False

    # --- Main Application Window ---
    # Create the root window
    root = tk.Tk()
    root.title("Manual classification")
    root.geometry("900x700")  # Made window significantly larger
    root.minsize(600, 500)  # Increased minimum size
    root.configure(bg="#f0f2f5")
    root.resizable(True, True)
    root.attributes("-zoomed", True)  # fullscreen

    # --- Color and Font Definitions ---
    colors = {
        "background": "#f0f2f5",
        "card": "#ffffff",
        "text": "#333333",
        "button_bg": "#007bff",
        "button_fg": "#ffffff",
        "button_hover": "#0056b3",
    }
    # --- Increased all font sizes ---
    fonts = {
        "help_text": ("Helvetica", 16, "italic"),
        "text": ("Helvetica", 20),
        "button": ("Helvetica", 18, "bold"),
        "id_text": ("Helvetica", 12),
    }

    # --- Functions for Button Clicks ---
    def on_response_a():
        """Handles the click event for the 'Response A' button."""
        attempt[f"{column}_Manual_Clean"] = "NORMAL"
        nonlocal result
        result = True
        root.destroy()

    def on_response_b():
        """Handles the click event for the 'Response B' button."""
        attempt[f"{column}_Manual_Clean"] = "REJECTION"
        nonlocal result
        result = True
        root.destroy()

    def on_unsure():
        """Handles the click event for the 'Unsure' button."""
        logging.info(f"Manually classified {attempt.id} with Response.Unsure")
        nonlocal result
        result = True
        root.destroy()

    def on_closing():
        """Handles the window closing event, as mentioned in the help text."""
        nonlocal result
        result = False
        root.destroy()

    # --- Hover Effect Functions for Buttons ---
    def on_enter(event):
        """Changes button color on mouse hover."""
        event.widget.config(bg=colors["button_hover"])

    def on_leave(event):
        """Reverts button color when mouse leaves."""
        event.widget.config(bg=colors["button_bg"])

    # --- Key press ---
    def key_press(event):
        if event.keysym.lower() == "a":
            on_response_a()
        elif event.keysym.lower() == "b":
            on_response_b()

    # --- UI Elements ---

    # A main frame to center the content and manage layout
    main_frame = tk.Frame(root, bg=colors["background"], padx=40, pady=20)
    main_frame.pack(expand=True, fill="both")

    # --- Help Text ---
    help_text_content = "Please classify the LLM output into choosing either Response A or Response B. Press the cross button at any time to quit -- your progress will be saved. Scroll down to see the prompt to the LLM if required. You can also press the A or B keys on the keyboard."
    help_label = tk.Label(
        main_frame,
        text=help_text_content,
        font=fonts["help_text"],
        bg=colors["background"],
        fg="#6c757d",  # A muted gray color
        wraplength=900,
        justify="center",
    )
    help_label.pack(pady=(0, 15))  # Add some padding below it

    # A 'card' frame for the text content with a subtle border
    # This frame will expand and fill the available space.
    card_frame = tk.Frame(
        main_frame,
        bg=colors["card"],
        relief="solid",
        borderwidth=1,
        highlightbackground="#e0e0e0",
        highlightthickness=1,
    )
    # Pack the card frame to expand, but leave space at the bottom for buttons
    card_frame.pack(padx=10, pady=(0, 20), expand=True, fill="both")
    card_frame.pack_propagate(False)  # Prevent children from shrinking the frame

    # A frame to hold the text widget and its scrollbar inside the card
    text_container = tk.Frame(card_frame, bg=colors["card"], padx=40, pady=40)
    text_container.pack(expand=True, fill="both")

    # The string containing the paragraphs of text to be displayed
    display_text = (
        attempt[column]
        + f"\n\n\n\n###############################   SCENARIO ({attempt['Sub-subcategory (L4)']})  ###############################\n"
        + attempt["Scenario Description"]
    )

    # A Text widget for scrollable text display.
    text_widget = tk.Text(
        text_container,
        wrap="word",
        font=fonts["text"],
        bg=colors["card"],
        fg=colors["text"],
        relief="flat",
        borderwidth=0,
        highlightthickness=0,
    )

    # Create a Scrollbar and associate it with the Text widget
    scrollbar = tk.Scrollbar(text_container, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)

    # Pack the scrollbar and text widget into the container frame
    scrollbar.pack(side="right", fill="y")
    text_widget.pack(side="left", expand=True, fill="both")

    # Insert the text into the widget and disable editing
    text_widget.insert("1.0", display_text)
    text_widget.config(state="disabled")

    # A frame to hold the buttons at the bottom, packed into the main_frame
    # This ensures it stays at the bottom and does not get pushed off-screen
    button_frame = tk.Frame(main_frame, bg=colors["background"])
    button_frame.pack(fill="x", padx=10)

    # --- Buttons ---
    # Styling for the buttons
    button_style = {
        "font": fonts["button"],
        "bg": colors["button_bg"],
        "fg": colors["button_fg"],
        "pady": 12,
        "padx": 20,
        "relief": "flat",
        "borderwidth": 0,
        "cursor": "hand2",
    }

    # Create the 'Response A' button
    button_a = tk.Button(
        button_frame, text="NORMAL <a>", command=on_response_a, **button_style
    )
    button_a.pack(side="left", expand=True, padx=(0, 5))

    # Create the 'Unsure' button
    button_quit = tk.Button(
        button_frame, text="DON'T CLICK", command=on_unsure, **button_style
    )
    button_quit.pack(side="right", expand=True, padx=(5, 5))

    # Create the 'Response B' button
    button_b = tk.Button(
        button_frame, text="REJECTION <b>", command=on_response_b, **button_style
    )
    button_b.pack(side="right", expand=True, padx=(5, 0))

    # Bind hover events to both buttons
    button_a.bind("<Enter>", on_enter)
    button_a.bind("<Leave>", on_leave)
    button_b.bind("<Enter>", on_enter)
    button_b.bind("<Leave>", on_leave)

    # Bind keypresses
    root.bind("<KeyPress>", key_press)

    # --- Start the Application ---
    # Bind the closing protocol to the on_closing function
    root.protocol("WM_DELETE_WINDOW", on_closing)
    # The mainloop() call displays the window and waits for user interaction.
    root.mainloop()

    return result
