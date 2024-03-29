# Server SQL Database ile haberlesip istenilen parcaya ve robota gore konum bilgilerini isteyecek
# Server Kullanicinin kaydetmek istedigi parcanin konum bilgilerini SQL Database yeni bir tablo olusturup kaydetecek

import mysql.connector
import sqlite3
import socket
import threading

HEADER = 8
HOST = "0.0.0.0"
PORT = 12345
FORMAT = "iso8859_9"
ADDR = (HOST, PORT)
DISCONNECT_MESSAGE = "!DISCONNECT"


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)
server.listen(10)
print("[Listening] Server is listening...")

clients = []
threads = []


def send(data: str, client: socket):
    len_data = f'{len(data)}'.encode(FORMAT)
    len_data = len_data + (b' ' * (8 - len(len_data)))
    client.send(len_data)
    client.send(data.encode(FORMAT))


def handle(client: socket):
    while (True):
        header_msg = client.recv(HEADER).decode(FORMAT)
        print(header_msg)
        if header_msg:
            msg_len = int(header_msg)
            msg = client.recv(msg_len)
            print(msg)
            msg = msg.decode(FORMAT)
            if msg[:4] == "user":
                userandpass = msg.split(" ")
                user_name = userandpass[1]
                password = userandpass[2]
                try:
                    con = mysql.connector.connect(host='192.168.0.250', port=3306,
                                                  user=f'{user_name}', password=f'{password}', database='presstransfer')
                    # con = sqlite3.connect('parts.db')
                    cur = con.cursor()
                    connected = True
                    if connected and user_name == "root":
                        qualified = True
                    else:
                        qualified = False
                    client.send("connected".encode(FORMAT))
                except:
                    connected = False
                    qualified = False
                    client.send("not connected".encode(FORMAT))
            elif msg[:6] == "create":
                part_name = msg[7:]
                if qualified:
                    sql_str = "create table %s (id int not null auto_increment, robot int not null, position int not null, x_axis double not null, y_axis double not null, z_axis double not null, a_axis double, b_axis double, c_axis double, p_axis double, q_axis double, unique (id), primary key (id));"
                    try:
                        cur.execute(sql_str %
                                    (msg[7:], ))
                        cur.execute(
                            f'insert into {part_name} (robot, position, x_axis, y_axis, z_axis, a_axis, b_axis, c_axis, p_axis, q_axis) values (1, 1, 0, 0, 0, 0, 0, 0, 0, 0)')
                        con.commit()
                        print("Parca olusturuldu.")
                    except:
                        print("error oldu yine")
                    client.send("qualified".encode(FORMAT))
                else:
                    client.send('not qualified'.encode(FORMAT))
            elif msg[:4] == "edit":
                if qualified:
                    edit_part_str = msg.split(' ')
                    part_name = edit_part_str[1]
                    position = edit_part_str[2]
                    position = position.split(',')
                    cur.execute(
                        f'select * from {part_name} where robot={position[0]} and position={position[1]}')
                    if cur.fetchone() == None:
                        cur.execute(
                            f'insert into {part_name} (robot, position, x_axis, y_axis, z_axis, a_axis, b_axis, c_axis, p_axis, q_axis) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', position)
                        con.commit()
                    else:
                        cur.execute(
                            f'update {part_name} set x_axis = %s, y_axis = %s, z_axis = %s, a_axis = %s, b_axis = %s, c_axis = %s, p_axis = %s, q_axis = %s where (robot = {position[0]} and position = {position[1]})', position[2:])
                        con.commit()
                    client.send("qualified".encode(FORMAT))
                else:
                    client.send("not qualified".encode(FORMAT))
            elif msg[:6] == "select":
                part_name = msg[7:]
                try:
                    cur.execute(f'select max(robot) from {part_name}')
                    max_robot = cur.fetchone()[0]
                    robot = []
                    for i in range(1, max_robot+1):
                        cur.execute(
                            f'select max(position) from {part_name} where robot={i}')  # !!!!!!!!
                        max_position = cur.fetchone()[0]
                        position = []
                        for j in range(1, max_position+1):
                            cur.execute(
                                f'select * from {part_name} where robot={i} and position={j}')
                            row = cur.fetchone()
                            position.append(','.join(str(k) for k in row))
                        robot.append(';'.join(str(k) for k in position))
                    coordinate = ':'.join(str(k) for k in robot)
                    send(coordinate, client)
                    print("ha buraya kadar geliyor.")
                except:
                    client.send("err".encode(FORMAT))
            elif msg[:4] == "drop":
                if qualified:
                    part_name = msg[5:]
                    client.send("qualified".encode(FORMAT))
                    cur.execute(f'drop table {part_name}')
                else:
                    client.send('not qualified'.encode(FORMAT))
            elif msg[:6] == "delete":
                if qualified:
                    message = msg[7:]
                    info = message.split(' ')
                    part_name = info[0]
                    robot = info[1]
                    try:
                        position = info[2]
                        cur.execute(
                            f'delete from {part_name} where robot = {robot} and position = {position}')
                        con.commit()
                    except:
                        print('hata mi oldu')
                        cur.execute(
                            f'delete from {part_name} where robot = {robot}')
                        con.commit()
                    client.send("qualified".encode(FORMAT))
                else:
                    client.send('not qualified'.encode(FORMAT))
            elif msg == "part_names":
                try:
                    cur.execute('show tables;')
                    # cur.execute("select name from sqlite_master where type='table'")
                    parts = cur.fetchall()
                    parts_list = [part[0] for part in parts]
                    parts_str = ','.join(str(i) for i in parts_list)
                    send(parts_str, client)
                except:
                    print("sunucuya baglanamadi!")
            elif msg == DISCONNECT_MESSAGE:
                print("Client disconnected!")
                break
            else:
                client.send("err".encode(FORMAT))
                break
            msg = ''
        header_msg = ''


while True:
    client, address = server.accept()
    print(f'Connected with {str(address)}')
    clients.append(client)
    thread = threading.Thread(target=handle, args=(client,))
    print("Aktif Baglanti sayisi: ", threading.active_count())
    threads.append(thread)
    thread.start()
