#!/usr/bin/python

from socket import *
import threading 
import time
import sys

'''
This is mainly to simulate the protocol distance vector,and I just use the matrix to
store the routing info.In order to specify the id of routers in the routing info,I 
create a marker list: [] to store the each route id.
I create a transmit thread to send routing info, a recv thread to receive the routing 
info,of course when it received the info, it should check the type(heartbeat or routing)
and handle it with some associated operations.

'''

# Transmit the forwarding info to neighbours frequently	
def transmit():
	current_time = time.time()
	while 1:
		now_time = time.time()

		if now_time - current_time >= 5:
			forwarding_info = find_min_cost()
			send(forwarding_info)
			current_time = now_time

# Send the forwarding info
def send(forwarding_info):
	global send_socket
	global send_port

	for port in send_port:
		send_socket.sendto(forwarding_info, ('127.0.0.1', int(port)))


# Recv the route info and heartbeat and handle it with some specified operation
def recv():
	global recv_socket
	global markers
	global extend_flag

	current_time = time.time()
	heartbeat = []

	while 1:

		'''
		Check the heartbeat of its' neighbours every 3s, check whether it can found the id
		If not, which means the neighbour has shutdown.Just delete the route info and marker
		info the node.
		'''
		now_time = time.time()
		if now_time - current_time >= 3:
			delete_node_index = 0
			delete_node_flag = False

			for i in range(len(table)):
				marker_name = "%" + markers[i] + "%"
				if marker_name not in heartbeat:
					delete_node_flag = True
					delete_node_index = i

			if delete_node_flag:		
				delete_direct_node(delete_node_index)
				time.sleep(2)

			current_time = now_time		
			heartbeat = []

		forwarding, addr = recv_socket.recvfrom(2048)

		'''
		Deal with received the route info,check the its type and decide the 
		operation type.
		'''

		if forwarding.startswith('%') and forwarding.endswith('%'):
			heartbeat.append(forwarding)

		else:
			forwarding_arr = forwarding.split('\n')
			forwarding_arr.remove('')

			forwarding_arr_info = []
			for record in forwarding_arr:
				forwarding_arr_info.append(record.split('@'))

			# First should extend size of route table if necessary
			if extend_flag:
				extend(forwarding_arr_info)
				recompute(forwarding_arr_info)

			else:
				reduce_size(forwarding_arr_info)
				recompute(forwarding_arr_info)


# Initialise forwarding table
# Note that format  table:[[], [], []]
# And the markers: [A, B, C....]
# I just used the index of markers to specified the ID
def initialse_table():
	global markers
	global table
	global link_cost

	for i in range(len(markers)):
		table.append([])

	for i in range(len(markers)):
		for j in range(len(link_cost)):
			if markers[i] == link_cost[j][0]:
				table[i].append(float(link_cost[j][1]))
			else:
				table[i].append(float('inf'))


# Find the min cost
# Note that there are tow case, one is normal, the other is deceive
def find_min_cost():
	global ID
	global markers
	global table
	global deceive_marker
	global deceive_flag

	min_cost_info = ''

	# Normal case
	if not deceive_flag:
		for i in range(len(table[0])):
			cost = []
			for j in range(len(table)):
				cost.append(float(table[j][i]))
			min_cost = min(cost)
			min_cost_info += str(ID) + '@' + markers[i] + '@' + str(min_cost) + '\n'

	# Deceive case
	else:
		for i in range(len(table[0])):
			if i < len(deceive_marker) and deceive_marker[i] == 1:
				min_cost = float("inf")
			else:
				cost = []
				for j in range(len(table)):
					cost.append(float(table[j][i]))
				min_cost = min(cost)
			min_cost_info += str(ID) + '@' + markers[i] + '@' + str(min_cost) + '\n'	

	return min_cost_info

# Format the output based on forwarding table
def output_min_cost():
	global ID
	global markers
	global table

	output_cost_info = ''
	for i in range(len(table[0])):
		min_cost = float('inf')
		next_hop = ''
		for j in range(len(table)):
			if table[j][i] < min_cost:
				min_cost = table[j][i]
				next_hop = markers[j]

		output_cost_info += "shortest path to node " + markers[i] + " : the next hop is " + next_hop + " and the cost is " + str(min_cost) + '\n'

	return output_cost_info

# Extend the size of markers and row of table
def extend(forwarding_arr_info):
	global markers
	global table

	for record in forwarding_arr_info:
		for i in range(2):
			if record[i] != ID and record[i] not in markers:
				markers.append(record[i])
				for j in range(len(table)):
					table[j].append(float("inf"))


# Recompute the forwarding table
def recompute(forwarding_arr_info):
	global table
	global markers

	for i in range(len(table)):
		if markers[i] == forwarding_arr_info[0][0]:
			for j in range(len(table[0])):
				for record in forwarding_arr_info:
					if markers[j] == record[1]:
						table[i][j] = float(table[i][i]) + float(record[2])


# Check stable based on old_table(20s before) and new_table
def check_stable():
	global table

	current_table = str(table)
	current_time = time.time()
	serial = 1
	while 1:
		now_time = time.time()
		if now_time - current_time >= 20:
			now_table = str(table)
			if current_table == now_table:
				return True
			else:
				current_table = now_table
				current_time = now_time
			serial += 1


# Send hearbeat everysecond
def heartbeat():
	current_time = time.time()
	while 1:
		now_time = time.time()
		if now_time - current_time >= 1:
			send_hearbeat()
			current_time = now_time


# Send the heartbeat format in %ID%
def send_hearbeat():
	global ID
	global send_socket
	global send_port

	data  = "%" + ID + "%"
	for port in send_port:
		send_socket.sendto(data, ("127.0.0.1", int(port)))

# Delete the neighbour (marker, table_size, associated row)
def delete_direct_node(marker_index):
	global table
	global markers

	table.remove(table[marker_index])
	for i in range(len(table)):
		del table[i][marker_index]
	markers.remove(markers[marker_index])

# Reduce size of forwarding table after shutdown the node
def reduce_size(forwarding_arr_info):
	global ID
	global markers

 
	forwarding_arr_info_nodes = []
	local_nodes = []

	forwarding_arr_info_nodes.append(forwarding_arr_info[0][0])
	for record in forwarding_arr_info:
		forwarding_arr_info_nodes.append(record[1])

	local_nodes.append(ID)
	for node in markers:
		local_nodes.append(node)

	for i in range(len(local_nodes)):
		if local_nodes[i] not in forwarding_arr_info_nodes:
			remove_node(i - 1)


# Remove associated node (marker, row) and table_size if necessary
def remove_node(node_index):
	global table
	global markers

	if node_index < len(table):
		del table[node_index]
	for i in range(len(table)):
		del table[i][node_index]
	markers.remove(markers[node_index])

# Reinitialise the forwarding table when the link cost changed
def re_initialise_table():
	global table
	global markers
	global changed_link_cost
	global deceive_marker

	for i in range(len(table)):
		for j in range(len(changed_link_cost)):
			if markers[i] == changed_link_cost[j][0]:
				if table[i][i] != float(changed_link_cost[j][1]):
					table[i][i] = float(changed_link_cost[j][1])
					deceive_marker.append(1)
				else:
					deceive_marker.append(0)

def main():

	global ID
	global markers
	global table
	global link_cost
	global changed_link_cost
	global send_port
	global send_socket
	global recv_socket
	global extend_flag
	global pr_flag
	global deceive_flag
	global deceive_marker


	input_length = len(sys.argv[1:])

	ID = sys.argv[1]
	port = sys.argv[2]
	file_path = sys.argv[3]

	if input_length == 4:
		if "-p" == sys.argv[4]:
			pr_flag = True


	if not pr_flag:
		for line in open(file_path, 'r'):
			line_arr = line.split()
			if len(line_arr) != 1 and line_arr != []:
				markers.append(line_arr[0])
				link_cost.append([line_arr[0], line_arr[1]])
				send_port.append(line_arr[-1])
	else:
		for line in open(file_path, 'r'):
			line_arr = line.split()
			if len(line_arr) != 1 and line_arr != []:
				markers.append(line_arr[0])
				link_cost.append([line_arr[0], line_arr[1]])
				changed_link_cost.append([line_arr[0], line_arr[2]])
				send_port.append(line_arr[-1])


	initialse_table()


	addr = ('127.0.0.1', int(port))
	recv_socket = socket(AF_INET,SOCK_DGRAM)
	recv_socket.bind(addr)

	send_socket = socket(AF_INET, SOCK_DGRAM)

	thread_transmit = threading.Thread(target = transmit, args = ())
	thread_transmit.setDaemon(True)
	thread_transmit.start()


	thread_recv = threading.Thread(target = recv, args = ())
	thread_recv.setDaemon(True)
	thread_recv.start()


	thread_stable = threading.Thread(target = check_stable, args = ())
	thread_stable.setDaemon(True)
	thread_stable.start()

	thread_heartbeat = threading.Thread(target = heartbeat, args = ())
	thread_heartbeat.setDaemon(True)
	thread_heartbeat.start()


	re_initialise_table_flag = True

	while 1 :
		if check_stable():
			if not pr_flag:
				extend_flag = False
				print output_min_cost()

			else:
				print output_min_cost()
				if re_initialise_table_flag:
					re_initialise_table()

					deceive_flag = True
					re_initialise_table_flag = False
		pass
	
if __name__ == '__main__':

	ID = ''
	markers = []
	table = []
	link_cost = []
	changed_link_cost = []
	send_port = []
	extend_flag = True
	pr_flag = False
	deceive_marker = []
	deceive_flag = False
	main()








