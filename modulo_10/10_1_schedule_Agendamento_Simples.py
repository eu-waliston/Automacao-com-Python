import schedule
import time

def tarefa_diaria():
    print("Executando backup...")

# Agendar
monitorar_sistema = ""
schedule.every().day.at("02:00").do(tarefa_diaria)
schedule.every(10).minutes.do(monitorar_sistema)

while True:
    schedule.run_pending()
    time.sleep(1)
