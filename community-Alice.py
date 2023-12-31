import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import matplotlib as mpl
from pylab import rcParams
from collections import defaultdict


def import_facebook_data(path):

    data = pd.read_csv(path, sep = " ", header=None)
    data = pd.concat([data, pd.DataFrame(np.array(data.iloc[:,::-1]), columns= data.columns)], axis = 0)
    return np.array(data, dtype=np.int32) 


def import_bitcoin_data(path):
    data = pd.read_csv(path, usecols=[0,1], sep = ",", header=None)
    data = pd.concat([data, pd.DataFrame(np.array(data.iloc[:,::-1]), columns= data.columns)], axis = 0)
    return np.array(data, dtype=np.int32) 

def spectralDecomp_OneIter(E):
    nodes = E.ravel()
    nodes = np.unique(nodes)
    s = len(nodes)

    node_id = dict((val, ind) for ind, val in enumerate(nodes))

    idx_map = np.array([[node_id[s], node_id[t]] for s, t in E])
  
    A = np.zeros((s,s), dtype=int)
    
    for i in range(idx_map.shape[0]):
        A[idx_map[i][0]][idx_map[i][1]]=1
        A[idx_map[i][1]][idx_map[i][0]]=1
    
    degree = np.sum(A, axis=1)
    D = np.diag(degree)
    L = D - A

    e_val, e_vec = np.linalg.eigh(L)
    idx = np.argsort(e_val)   
    e_val = e_val[idx]
    e_vec = e_vec[idx]

    th = 0.95
    i = 0
    while((abs(e_val[i+1] - e_val[i])/e_val[i+1]) < th):
        i += 1

    fielder_vec = e_vec[:,i+1]
    
    c1 = np.min(nodes[fielder_vec<=0])
    c2 = np.min(nodes[fielder_vec>0])

    l = np.zeros_like(nodes)
    l[fielder_vec<=0] = c1
    l[fielder_vec>0] = c2

    graph_partition =  np.hstack((nodes.reshape(-1,1), l.reshape(-1,1)))
    return fielder_vec, A, graph_partition


def spectralDecomposition(E):

    _, _, gp = spectralDecomp_OneIter(E)

    node, com_id = gp[:, 0], gp[:, 1]
    com_id = np.unique(com_id)
    n_com = dict()
    s = len(node)

    for i in range(s):
        n_com[gp[i,0]] = gp[i,1]

    uid_0 = []
    uid_1 = []
    cut = 0

    for i in range(E.shape[0]):
        s,t = E[i,0], E[i,1]
        c1, c2 = n_com[s], n_com[t]
        if c1 != c2:
            cut += 1  
        else:
            uid_0.append([s,t]) if c1 == com_id[0] else uid_1.append([s,t])

    uid_0, uid_1 = np.array(uid_0), np.array(uid_1)

    v0, v1 = len(uid_0), len(uid_1)
    if v0 == 0 or v1 == 0:
        gp[:, 1] = np.ones(gp.shape[0]) * np.min(gp[:, 1])
        return gp

    conductance = cut/min(v0,v1)

    if (conductance > 0.2):
        gp[:, 1] = np.ones(gp.shape[0]) * np.min(gp[:, 1])
        return gp

    gp0 = spectralDecomposition(uid_0)
    gp1 = spectralDecomposition(uid_1)

    i = 0
    j = 0
    graph_partition = []
    while(i < gp0.shape[0] or j < gp1.shape[0]):
        if i == gp0.shape[0]:
            graph_partition.append(gp1[j])
            j += 1
            continue
        
        if j == gp1.shape[0]:
            graph_partition.append(gp0[i])
            i += 1
            continue

        if gp0[i, 0] < gp1[j, 0]:
            graph_partition.append(gp0[i])
            i += 1
        else:
            graph_partition.append(gp1[j])
            j += 1

    return np.array(graph_partition)

def graph_plotter(labels, E):
    G = nx.from_edgelist(E)
    pos = nx.spring_layout(G)

    low, high = np.min(labels[:, 1]), np.max(labels[:, 1])

    norm = mpl.colors.Normalize(vmin=low, vmax=high, clip=True)
    mapper = mpl.cm.ScalarMappable(norm=norm, cmap=mpl.cm.magma)
    node_color = mapper.to_rgba(labels[:, 1])

    plt.rcParams['figure.figsize'] = 10, 6
    nx.draw(G, pos=pos, nodelist=labels[:, 0], node_size=50, node_color=node_color, with_labels=False)
    plt.show()


def createSortedAdjMat(gp, data):
     
    com_id = np.unique(gp[:,1])

    partition = {}
    for com in com_id:
        nodes=[]
        for i in range(gp.shape[0]):
            if gp[i,1] == com:
                nodes.append(gp[i,0])
        partition[com]=np.array(nodes)

    key=np.array([], dtype = np.int32)
    for i in range(com_id.shape[0]):
        key=np.concatenate((key, partition[com_id[i]]))

    adj=np.zeros((key.shape[0],key.shape[0]), dtype=int)

    dict1=dict((val, ind) for ind, val in enumerate(key))
    
    idx_map=np.array([[dict1[scr], dict1[tar]] for scr, tar in data])

    for i in range(idx_map.shape[0]):
        adj[idx_map[i,0]][idx_map[i,1]]=1
        adj[idx_map[i,1]][idx_map[i,0]]=1

    return adj




def louvain_one_iter(graph):
    #phase 1 operations: Demerge and Merge
    # Difference in modularity [Q_after - Q_before]
    # def modularity_gain(nodei, comm):
    #     Comm_nodes = partition[comm]
    #     Curr_Cnodes = partition[nodei]
    #     total_Deg_M = sum(degree[X] for X in Comm_nodes )
    #     total_Deg_D= sum(degree[X] for X in Curr_Cnodes )

    #     deg_i = degree[nodei]
    #     deg_i_in = 2*np.sum(adj_matrix[nodei,Comm_nodes])
    #     deg_i_out = 2*np.sum(adj_matrix[nodei,Curr_Cnodes])

    #     Qdemerge = 2*deg_i*total_Deg_D - 2*deg_i**2 - deg_i_out
    #     Qmerge = deg_i_in - 2*total_Deg_M*deg_i

    #     return Qdemerge+Qmerge
    def demerge(nodei):
        Curr_Cnodes = partition[comm_map[nodei]]
        cur_idx = [node_map[i] for i in Curr_Cnodes]

        total_Deg_D= sum(degree[X] for X in cur_idx )
        deg_i_out = 2*np.sum(adj_matrix[node_map[nodei],cur_idx])
        deg_i = degree[node_map[nodei]]
        Qdemerge = 2*deg_i*total_Deg_D - 2*deg_i**2 - deg_i_out
        return Qdemerge
    
    def merge(nodei, C):
        Comm_nodes = partition[C]
        comm_idx = [node_map[i] for i in Comm_nodes]
        total_Deg_M = sum(degree[X] for X in comm_idx)

        deg_i_in = 2*np.sum(adj_matrix[node_map[nodei],comm_idx])
        deg_i = degree[node_map[nodei]]
        Qmerge = deg_i_in - 2*total_Deg_M*deg_i
        return Qmerge    
    

    # Creating node Map with index:
    node = np.unique(graph)
    node_map = {i: k for k, i in enumerate(node)}

    # Creating initial Commu_id Map:
    comm_map = {i:i for i in node}
    partition = {i:[i] for i in node}

    # Creating Neighbour_Map:
    neigh_dict = defaultdict(list)
    for source, target in graph:
        neigh_dict[source].append(target)

    # adjacent matrix:
    size = np.unique(graph)
    num_node = len(size)
    adj_matrix = np.zeros((num_node, num_node),dtype=int)
    for edge in graph:
        i, j = edge
        adj_matrix[node_map[i]][node_map[j]] = 1
        adj_matrix[node_map[j]][node_map[i]] = 1
    nodes_connectivity_list_fb = adj_matrix

    # Degree of each node:
    degree = np.sum(nodes_connectivity_list_fb, axis=1)

    m  = np.sum(degree)
    degree = degree/m
    adj_matrix = adj_matrix/m

    ##### Repeat until no further improvement in modularity is possible #####

    while True:
        diff = 0
        
        for nody in node:
            curr_comm = comm_map[nody]
            neigh_comm = set()
            for neigh in neigh_dict[nody]:
                if comm_map[neigh] != curr_comm:
                    neigh_comm.add(comm_map[neigh])

            max_gain = 0
            max_com = curr_comm
            del_curr = demerge(nody)
            for com in neigh_comm:
                del_com = merge(nody,com)
                mod_gain = del_curr  + del_com
                if max_gain < mod_gain:
                    max_gain = mod_gain
                    max_com = com
        
            
            # If positive moularity gain, then, (X->i->Y)
            if max_gain>0:
                partition[curr_comm].remove(nody)
                comm_map[nody] = max_com
                partition[max_com].append(nody)
                diff = 1
                # print(partition)
        # If no node was moved in this iteration, break the loop
        if diff == 0:
            break
    s = len(comm_map)
    cluster = np.ndarray((s,2),dtype=int)
    for i,val in comm_map.items():
        cluster[node_map[i]][0] = i
        cluster[node_map[i]][1] = val
        
    return cluster

if __name__ == "__main__":

    ############ Answer qn 1-4 for facebook data #################################################
    # Import facebook_combined.txt
    # nodes_connectivity_list is a nx2 numpy array, where every row 
    # is a edge connecting i<->j (entry in the first column is node i, 
    # entry in the second column is node j)
    # Each row represents a unique edge. Hence, any repetitions in data must be cleaned away.
    nodes_connectivity_list_fb = import_facebook_data("../data/facebook_combined.txt")

    # This is for question no. 1
    # fielder_vec    : n-length numpy array. (n being number of nodes in the network)
    # adj_mat        : nxn adjacency matrix of the graph
    # graph_partition: graph_partitition is a nx2 numpy array where the first column consists of all
    #                  nodes in the network and the second column lists their community id (starting from 0)
    #                  Follow the convention that the community id is equal to the lowest nodeID in that community.
    fielder_vec_fb, adj_mat_fb, graph_partition_fb = spectralDecomp_OneIter(nodes_connectivity_list_fb)
    plt.plot(np.sort(fielder_vec_fb))
    plt.show()

    # This is for question no. 2. Use the function 
    # written for question no.1 iteratetively within this function.
    # graph_partition is a nx2 numpy array, as before. It now contains all the community id's that you have
    # identified as part of question 2. The naming convention for the community id is as before.
     
    graph_partition_fb = spectralDecomposition(nodes_connectivity_list_fb)
    print("Number of community in facebook dataset using spectralDecomposition Algorithm:",len(np.unique(graph_partition_fb[:,1])))


    # This is for question no. 3
    # Create the sorted adjacency matrix of the entire graph. You will need the identified communities from
    # question 3 (in the form of the nx2 numpy array graph_partition) and the nodes_connectivity_list. The
    # adjacency matrix is to be sorted in an increasing order of communitites.
    clustered_adj_mat_fb = createSortedAdjMat(graph_partition_fb, nodes_connectivity_list_fb)
    plt.matshow(clustered_adj_mat_fb)
    plt.show()
    graph_plotter(graph_partition_fb, nodes_connectivity_list_fb)

    # This is for question no. 4
    # run one iteration of louvain algorithm and return the resulting graph_partition. The description of
    # graph_partition vector is as before.
     
    graph_partition_louvain_fb = louvain_one_iter(nodes_connectivity_list_fb)
    print("Number of community in facebook dataset using Louvain Algorithm:",len(np.unique(graph_partition_louvain_fb[:,1])))

    clustered_adj_mat_fb = createSortedAdjMat(graph_partition_louvain_fb, nodes_connectivity_list_fb)
    plt.matshow(clustered_adj_mat_fb)
    plt.show()
    graph_plotter(graph_partition_louvain_fb, nodes_connectivity_list_fb)


    # ############ Answer qn 1-4 for bitcoin data #################################################
    # # Import soc-sign-bitcoinotc.csv
    nodes_connectivity_list_btc = import_bitcoin_data("../data/soc-sign-bitcoinotc.csv")

    # # Question 1
    fielder_vec_btc, adj_mat_btc, graph_partition_btc = spectralDecomp_OneIter(nodes_connectivity_list_btc)
    plt.plot(np.sort(fielder_vec_btc))
    plt.show()

    # # Question 2
    graph_partition_btc = spectralDecomposition(nodes_connectivity_list_btc)
    print("Number of community in bitcoin dataset using spectralDecomposition Algorithm:",len(np.unique(graph_partition_fb[:,1])))


    # # Question 3
    clustered_adj_mat_btc = createSortedAdjMat(graph_partition_btc, nodes_connectivity_list_btc)
    plt.matshow(clustered_adj_mat_btc)
    plt.show()
    graph_plotter(graph_partition_btc, nodes_connectivity_list_btc)

    # Question 4
    graph_partition_louvain_btc = louvain_one_iter(nodes_connectivity_list_btc)
    print("Number of community in bitcoin dataset using Louvain Algorithm:",len(np.unique(graph_partition_louvain_btc[:,1])))


    clustered_adj_mat_btc = createSortedAdjMat(graph_partition_louvain_btc, nodes_connectivity_list_btc)
    plt.matshow(clustered_adj_mat_btc)
    plt.show()
    graph_plotter(graph_partition_louvain_btc, nodes_connectivity_list_btc)

