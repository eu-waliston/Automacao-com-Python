import pyautogui
import time

# Segurança
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

# Exemplo: preencher formulário
pyautogui.click(100, 200)  # Coordenadas
pyautogui.typewrite("Texto", interval=0.1)
pyautogui.hotkey('ctrl', 's')