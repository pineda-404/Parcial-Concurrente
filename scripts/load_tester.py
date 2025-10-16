# python/scripts/load_tester.py
import socket, json, threading, random, time
import argparse

HOST = "127.0.0.1"
PORT = 6000   # puerto del ServidorCentral

def do_transfer(from_acc, to_acc, amount, timeout=3):
    try:
        with socket.create_connection((HOST, PORT), timeout=timeout) as s:
            req = {"type":"TRANSFERIR_CUENTA","from": from_acc, "to": to_acc, "amount": amount}
            s.sendall((json.dumps(req)+"\n").encode())
            resp = s.recv(4096).decode().strip()
            return resp
    except Exception as e:
        return str(e)

def worker_thread(iterations, max_acc):
    for i in range(iterations):
        a = random.randint(1000, 1000 + max_acc - 1)
        b = random.randint(1000, 1000 + max_acc - 1)
        if a==b: b = a+1
        amt = round(random.uniform(1, 100), 2)
        r = do_transfer(a,b,amt)
        print(f"[T] {a}->{b} {amt} => {r}")
        time.sleep(random.uniform(0.01, 0.2))  # small random delay

if __name__=="__main__":
    import sys
    threads = 50
    iters = 20
    maxacc = 10000
    if len(sys.argv)>1: threads = int(sys.argv[1])
    if len(sys.argv)>2: iters = int(sys.argv[2])
    print(f"Starting {threads} threads x {iters} iterations")
    ths=[]
    for _ in range(threads):
        t = threading.Thread(target=worker_thread, args=(iters,maxacc))
        t.start()
        ths.append(t)
    for t in ths: t.join()
    print("Done")
