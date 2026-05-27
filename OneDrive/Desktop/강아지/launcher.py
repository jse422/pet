from multiprocessing import Process
import subprocess

PYTHON = r'C:\Users\jsepr\miniconda3\pythonw.exe'
BASE   = r'C:\Users\jsepr\OneDrive\Desktop\강아지'

def run(script):
    subprocess.run([PYTHON, f'{BASE}\\{script}'])

if __name__ == '__main__':
    dog = Process(target=run, args=('dog\\dog_pet.py',))
    dog.start()
    dog.join()
