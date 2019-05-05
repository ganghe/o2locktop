import threading
import time

def f():
    time.sleep(2)

t1 = threading.Thread(target=f,)
t2 = threading.Thread(target=f,)

now = time.time()
t1.start()
t2.start()

t1.join()
t2.join()

print(time.time()-now)
