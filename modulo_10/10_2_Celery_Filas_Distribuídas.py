from celery import Celery

app = Celery('tasks', broker='amqp://guest:guest@localhost//')

@app.task
def process_file(filename):
    #processamento pesado
    return resultado

# Executar
process_file.delay("arquivo.csv")

