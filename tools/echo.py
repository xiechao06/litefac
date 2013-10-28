""" 
A simple echo server 
""" 

import socket 

host = '' 
port = 5000
backlog = 5 
size = 1024 
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
s.bind((host,port)) 
s.listen(backlog) 
while 1: 
    client, address = s.accept() 
    while True:
        data = client.recv(size) 
        if data: 
            print data
            client.send(data) 
        else:
            break
    client.close()
