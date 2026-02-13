import keyboard

# registrar hotkey
keyboard.add_hotkey('ctrl+shift+a', lambda: print("Atalho precionadp"))

# Gravar macros
recorded = keyboard.record(until='esc')
keyboard.play(recorded, speed_factor=2)
