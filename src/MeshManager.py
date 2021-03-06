from tkinter import *
import numpy as np
import time
import os
import types

from DijkstraSolver import Graph
from CanvasBase import CanvasBase
from Node import Node
from Optimizer import RouterOptimizer


class MeshManager(CanvasBase):
    def __init__(self, canvas, frame, **kwargs):
        super(MeshManager, self).__init__(canvas, frame, **kwargs)
        self.dijkstra_graph = Graph(0)
        self.router_optimizer = RouterOptimizer(self)

        self.canvas.bind("<Button-1>", self.create_node_callback)
        self.canvas.bind("<Button-3>", self.delete_node_callback)
        self.canvas.bind("<B1-Motion>", self.drag_node_callback)
        self.canvas.bind("<B2-Motion>", self.drag_canvas)
        self.canvas.bind("<Button-2>", self.drag_canvas_click)
        self.canvas.bind("<Double-Button-3>", self.clear_canvas_callback)
        self.canvas.bind("<Control-Button-1>", self.create_router_callback)
        self.canvas.bind("<Shift-Button-1>", self.measure_distance_callback)
        self.canvas.bind("<ButtonRelease-1>", self.release_button_callback)
        self.canvas.bind_all("r", self.make_random_canvas_callback)
        self.canvas.bind_all("d", self.measure_all_distances_from_node)
        self.canvas.bind_all("s", self.optimize_router_position)
        #self.canvas.bind_all("<space>", self.make_random_canvas_callback)
        if os.name == 'nt':  # Windows
            self.canvas.bind("<MouseWheel>", self.wheelscroll_callback)
        else:  # Linux
            self.canvas.bind("<Button-4>", self.wheelscroll_callback)
            self.canvas.bind("<Button-5>", self.wheelscroll_callback)
        self.canvas_scale = 1
        self.prev_measure_node = -1
        self.last_measure_distance_callback_time = time.time()
        self.scale_text = self.canvas.create_text(50, 7, text="", fill='white')

    def get_connections_list(self):
        if self.node_list == []:
            return []
        else:
            # Find source node (any router)
            source_node = -1
            for i, node in enumerate(self.node_list):
                if node.type == 'router':
                    source_node = i
            if source_node == -1:
                print("No router node in the current graph")
                for node in self.node_list:
                    node.connection_tier = 0
                return []
            else:
                # Apply dijkstra algorithm
                self.dijkstra_graph.node_list = self.node_list
                rx_connection_list = self.dijkstra_graph.dijkstra(source_node, self.canvas_scale)
                return rx_connection_list

    def draw_current_canvas(self):
        # Delete all lines and text
        for line in self.line_list.copy():
            self.canvas.delete(line)
            self.line_list.remove(line)
        for txt in self.txt_list.copy():
            self.canvas.delete(txt)
            self.txt_list.remove(txt)

        # No nodes in graph or no router in graph
        if self.rx_connection_list == []:
            for node in self.node_list:
                node.update_txt()
            return

        # Draw the new lines
        for i in range(len(self.node_list)):
            node_child = self.node_list[i]
            if node_child.type != 'router':
                node_parent = self.node_list[self.rx_connection_list[i]]
                xc1, yc1 = node_child.get_center()
                xc2, yc2 = node_parent.get_center()
                line = self.canvas.create_line(xc1, yc1, xc2, yc2)
                txt = self.canvas.create_text(int(xc1 / 2 + xc2 / 2), int(yc1 / 2 + yc2 / 2),
                                              text=str(round(self.dijkstra_graph.get_distance(node_tx=node_parent, node_rx=node_child), 3))
                                              )
                self.line_list.append(line)
                self.txt_list.append(txt)

        # Update the info inside the nodes
        for node in self.node_list:
            node.update_txt()
        return

    def update_canvas_complete(self):
        '''
        Update the current canvas (recalculate the graph, update the drawings)
        '''
        # Get the connection
        self.rx_connection_list = self.get_connections_list()
        self.draw_current_canvas()

    def update_last_moved(self, event):
        '''
        Slowly drag the last activated node to the current cursor position
         - Solves the 'move mouse too fast' problem
        '''
        xc, yc = self.last_moved_node.get_center()
        [x, y] = [event.x, event.y]
        deltax = int(-(xc - x))
        deltay = int(-(yc - y))

        self.last_moved_node.move(deltax, deltay)
        self.update_canvas_complete()

    def update_canvas_scale(self, new_scale):

        for node in self.node_list:
            [x, y] = node.get_center()
            # Update the new [x,y]
            # Update in reference to the original [x0,y0] (unscaled positions)
            new_x, new_y = [int(c * new_scale / self.canvas_scale) for c in [x, y]]
            node.move_to(new_x, new_y)
        self.canvas_scale = new_scale
        self.canvas.itemconfigure(self.scale_text, text=round(new_scale, 3))
    '''
    Buttons callbacks
     - Button1 click         : add node
     - Button2 click         : remove node
     - Button2 double click  : remove all nodes
     - Ctrol + Button1 click : add router
     - Shift + Button1 click : measure distance between two nodes (shift click one, shift click another one)
     - Keyboard <r> press    : make random graph with 20 nodes
     - Keyboard <s> press    : optimize the position of the last added router´
     - Keyboard <d> press    : measure the distance from target node to all other nodes
    '''

    def optimize_router_position(self, event=None):
        '''
        Callback for keyboard key 's'
        '''
        # self.router_optimizer.optimize_router()
        self.router_optimizer.optimize_router()

    def make_random_canvas_callback(self, event=None):
        '''
        Callback for 'r' keyboard key press
        '''
        print('Random board...')
        self.clear_canvas_callback(None)
        self.create_router(np.random.randint(30, self.canvas.winfo_height() - 30),
                           np.random.randint(30, self.canvas.winfo_width() - 30))

        for n in range(0, 20):
            tries = 0
            while(tries < 1000):
                tries += 1
                [x, y] = [np.random.randint(30, self.canvas.winfo_height() - 30),
                          np.random.randint(30, self.canvas.winfo_width() - 30)]
                if self.check_any_intersection(x, y) == -1:
                    self.create_node(x, y)
                    tries = 1000
        self.update_canvas_complete()

    def wheelscroll_callback(self, event):
        '''
        Callback for mouse wheel
        '''
        # If Ctrl + Scroll
        if event.state == 36:
            if os.name == 'nt':  # Windows
                if event.delta > 0:
                    new_scale = self.canvas_scale + 0.1
                else:
                    new_scale = self.canvas_scale - 0.1

            else:  # Linux
                if event.num == 4:
                    new_scale = self.canvas_scale + 0.1
                elif event.num == 5:
                    new_scale = self.canvas_scale - 0.1
            new_scale = np.clip(new_scale, 0.25, 4)
            self.update_canvas_scale(new_scale)
            self.update_canvas_complete() 

        # If not Ctrl + Wheel
        else:
            # If on top of a object
            obj = self.check_any_intersection(event.x, event.y)
            if obj != -1:
                if os.name == 'nt':  # Windows
                    if event.delta > 0:
                        obj.node_power += 5
                    else:
                        obj.node_power = np.max([obj.node_power - 5, 0])

                else:  # Linux
                    if event.num == 4:
                        obj.node_power += 5
                    elif event.num == 5:
                        obj.node_power = np.max([obj.node_power - 5, 0])
                    obj.update_txt()
                self.update_canvas_complete()

    def drag_canvas_click(self, event):
        [x, y] = [event.x, event.y]
        self.last_drag_position = [x, y]

    def drag_canvas(self, event):
        x0, y0 = self.last_drag_position
        [x, y] = [event.x, event.y]
        dx = x0-x
        dy = y0-y
        for node in self.node_list:
            node.move(-dx/1.5, -dy/1.5)
        self.last_drag_position = [x, y]        
        self.draw_current_canvas()

    def drag_node_callback(self, event):
        '''
        Callback for left mouse motion
        '''
        if (time.time() - self.last_measure_distance_callback_time) < 1:
            return
        else:
            [x, y] = [event.x, event.y]
            obj = self.check_any_intersection(x, y)
            if obj != -1:
                self.move_node(obj, event)
            else:
                self.move_node(self.last_moved_node, event)
        self.update_canvas_complete()
        print(self.router_optimizer.average_node_distance())

    def release_button_callback(self, event):
        '''
        Callback for button1 release
        '''
        if (time.time() - self.last_measure_distance_callback_time) < 1:
            return
        else:
            self.update_canvas_complete()

    def delete_node_callback(self, event):
        '''
        Callback for right click
        '''
        [x, y] = [event.x, event.y]
        obj = self.check_any_intersection(x, y)
        if obj != -1:
            self.delete_node(obj)
        self.update_canvas_complete()

    def clear_canvas_callback(self, event=None):
        '''
        Callback for double right click
        '''
        for node in self.node_list.copy():
            self.delete_node(node)
        for line in self.line_list.copy():
            self.delete_line(line)
        self.last_moved_node = -1
        self.prev_measure_node = -1
        self.update_canvas_complete()

    def measure_all_distances_from_node(self, event):
        '''
        Callback for 'd' keyboard press
        '''
        [x, y] = [event.x, event.y]
        clicked_node = self.check_any_intersection(x, y)
        if clicked_node == -1:
            return
        else:
            for target_node in self.node_list:
                xc1, yc1 = clicked_node.get_center()
                xc2, yc2 = target_node.get_center()
                line = self.canvas.create_line(xc1, yc1, xc2, yc2, dash=(5, 5))
                distance = self.dijkstra_graph.get_distance(node_tx=clicked_node,
                                                            node_rx=target_node, canvas_scale=self.canvas_scale)
                txt = self.canvas.create_text(int(xc1 / 2 + xc2 / 2), int(yc1 / 2 + yc2 / 2),
                                              text=str(round(distance, 3)))
                self.line_list.append(line)
                self.txt_list.append(txt)

    def measure_distance_callback(self, event):
        '''
        Callback for shift click
        '''
        [x, y] = [event.x, event.y]
        clicked_node = self.check_any_intersection(x, y)
        if clicked_node != -1:
            if self.prev_measure_node == -1:
                self.prev_measure_node = clicked_node
            else:
                previous_node = self.prev_measure_node
                self.prev_measure_node = clicked_node

                xc1, yc1 = previous_node.get_center()
                xc2, yc2 = clicked_node.get_center()
                line = self.canvas.create_line(xc1, yc1, xc2, yc2, dash=(5, 5))
                distance = self.dijkstra_graph.get_distance(node_tx=clicked_node,
                                                            node_rx=target_node, canvas_scale=self.canvas_scale)
                txt = self.canvas.create_text(int(xc1 / 2 + xc2 / 2), int(yc1 / 2 + yc2 / 2),
                                              text=str(round(distance, 3)))
                self.line_list.append(line)
                self.txt_list.append(txt)
                self.prev_measure_node = clicked_node
        self.last_measure_distance_callback_time = time.time()

    def create_router_callback(self, event):
        '''
        Callback for Ctrl + left mouse click
        '''
        [x, y] = [event.x, event.y]
        self.create_router(x, y)
        self.update_canvas_complete()

    def create_node_callback(self, event):
        '''
        Callback for left mouse click
        '''
        [x, y] = [event.x, event.y]
        self.create_node(x, y)
        self.update_canvas_complete()
