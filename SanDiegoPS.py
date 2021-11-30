#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 29 19:37:44 2020

@author: simon
"""

import pandas as pd
import numpy as np
import math as m
import networkx as nx
import matplotlib.pyplot as plt
import random
import csv

    
####################################################################################
                            #BUILDING NETWORK (STEADY-STATE)
####################################################################################

def EstablishNetwork(NetworkFile,NumNodes):
    n=NumNodes
    print("Adding ",n," bus nodes to this transmission network...\n")
    data=np.array(NetworkFile)
    A = np.zeros([n,n])
    for i in range(len(data)):
        index1=data[i,0]
        index2=data[i,1]
        A[index1-1,index2-1]=1  #undirected graph
        A[index2-1,index1-1]=1
    G = nx.DiGraph(A)
    nx.draw(G, node_size= 60)
    return A  

def FindCentrality(A):
    print("Calculating centralities of network...")
    orderCentrality=[[]]
    for i in range(len(A)):
        centrality=sum(A[i])
        if(centrality<=len(orderCentrality)):
            orderCentrality[m.floor(centrality)-1].append(i)
        else:
            for j in range(m.floor(centrality)-len(orderCentrality)):
                orderCentrality.append([])
            orderCentrality[m.floor(centrality)-1].append(i)
    countVec=[]
    for i in range(len(orderCentrality)):
        countVec.append(len(orderCentrality[i]))
    print("Nodes have 1 through", len(orderCentrality), "edges with distribution: ", countVec,"\n")
    return orderCentrality

def addBaseCapacity(centralities,gen,total_base_capacity,numGenerators):
    #print("Constructing Landfill base generation...")
    added=0
    index=-1
    subindex=0
    nodesAdded=[]
    while(added<numGenerators):
        if(subindex<len(centralities[index])):
            gen[centralities[index][subindex]]=total_base_capacity/numGenerators
            nodesAdded.append(centralities[index][subindex])
            subindex=subindex+1
            added=added+1
        else:
            subindex=0
            index=index-1
            gen[centralities[index][subindex]]=total_base_capacity/numGenerators
            nodesAdded.append(centralities[index][subindex])
            subindex=subindex+1
            added=added+1
    print("Landfill base generation added on nodes: ", nodesAdded)
    return gen

def addWindCapacity(centralities,gen,base_capacity,ancillary_capacity,numFarms):
    added=0
    numBase=1
    index=-1
    subindex=0
    baseAdded=[]
    while(added<numBase):
        if(subindex<len(centralities[index])):
            if(gen[centralities[index][subindex]]==0):
                gen[centralities[index][subindex]]=base_capacity
                baseAdded.append(centralities[index][subindex])
                added=added+1
            subindex=subindex+1
            
        else:
            subindex=0
            index=index-1
            if(gen[centralities[index][subindex]]==0):
                gen[centralities[index][subindex]]=base_capacity
                baseAdded.append(centralities[index][subindex])
                added=added+1
            subindex=subindex+1         
    print("Wind base generation added on node: ", baseAdded)
    
    ancillaryTier=-6
    addTo=centralities[ancillaryTier]
    ancAdded=[]
    for i in range(m.floor(len(addTo)/(numFarms-numBase))+1):
        gen[addTo[i*(numFarms-numBase)]]=gen[addTo[i*(numFarms-numBase)]]+ancillary_capacity/(numFarms-numBase)
        ancAdded.append(addTo[i*(numFarms-numBase)])
    print("Ancillary wind generation added on nodes: ", ancAdded)
    return gen

def addSolarCapacity(centralities,gen,total_solar_capacity,numSolar):
    gen[centralities[0][0]]=total_solar_capacity/numSolar
    print("Utility solar generation added on node: ", [centralities[0][0]])
    return gen

def addGenerationCapacity(centralities,NumNodes):
    print("Building out generation capacity...\n")
    n=NumNodes
    gen=np.zeros(n)
    gen=addBaseCapacity(centralities,gen,30,3) #Base
    gen=addWindCapacity(centralities,gen,20,40,5) #Wind
    gen=addSolarCapacity(centralities,gen,60,1) #Solar
    print("All generation installed.\n")
    return gen



def addUtilityStorageCapacity(storage,ramp):
    storage[2]=40
    ramp[2]=16
    storage[4]=70 #seasonal
    ramp[4]=16
    print("Added 2 20MWH G. Vaults to node: [2]")
    print("Added 2 35MWH F. Vaults and 1 67Fuel-Cell to node: [4]")
    return storage,ramp

def addTeslaStorageCapacity(centralities,storage,ramp):
    storage[79]=21 #gravity or 7 teslas
    ramp[79]=10.5
    tier=centralities[-7]
    addedTo=[7]
    storage[7]=3
    storage[7]=1.5
    for i in range(1,len(tier)):
        if(i%2==0):
            storage[tier[i]]=3
            ramp[tier[i]]=1.5
            addedTo.append(tier[i])
    print("Added 3MWH Tesla Megapacks to nodes: ", addedTo)
    return storage,ramp

def addPumpedHydroCapacity(centralities,storage,ramp,hydro_capacity):
    hodges=3200
    tier=centralities[-4] 
    storage[tier[0]]=hodges
    storage[tier[-1]]=hydro_capacity-hodges  
    ramp[tier[0]]=40
    ramp[tier[-1]]=40
    print("Pumped Hydro added to nodes: ",[tier[0],tier[-1]])
    return storage,ramp



def addStorageCapacity(centralities,NumNodes):
    print("Building out storage capacity...\n")
    n=NumNodes
    storage=np.zeros(n)
    ramp=np.zeros(n)
    storage,ramp=addUtilityStorageCapacity(storage,ramp)
    storage,ramp=addTeslaStorageCapacity(centralities,storage,ramp)
    storage,ramp=addPumpedHydroCapacity(centralities,storage,ramp,6400) #check with this number it says 500 but idk
    print("All storage installed.\n")
    return storage,ramp



def buildNetwork(NetworkFile,IEEEsys):
    A=EstablishNetwork(pd.read_csv(NetworkFile, sep=','), IEEEsys)
    centralities=FindCentrality(A)
    gen=addGenerationCapacity(centralities, IEEEsys)
    storage,ramp=addStorageCapacity(centralities, IEEEsys)
    return gen,storage,ramp
    

####################################################################################
                                #DYNAMICS
####################################################################################

def chargeToStorage(amount,storage,storageCap,discharge):
    I=storage
    if((storage[7]+(amount/10))<storageCap[7]):
        giveEach=amount/10
        storage[7]=storage[7]+ giveEach
        storage[23]=storage[30]=storage[41]=storage[45]=storage[50]=storage[59]=storage[70]=storage[82]=storage[105]=storage[7]
        return storage
    elif(storage[7]<storageCap[7]):
        amount=storage[7]+(amount/10)-storageCap[7]
        storage[23]=storage[30]=storage[41]=storage[45]=storage[50]=storage[59]=storage[70]=storage[82]=storage[105]=storage[7]=storageCap[7]
    if(storage[4]+amount<storageCap[4]):
        storage[4]=storage[4]+amount
        return storage
    elif(storage[4]<storageCap[4]):
        amount=storage[4]+amount-storageCap[4]
        storage[4]=storageCap[4]
    if(storage[16]+amount<storageCap[16]):
        storage[16]=storage[16]+amount
        return storage
    elif(storage[16]<storageCap[16]):
        storage[16]=storageCap[16]
        amount=storage[16] + amount-storageCap[16]
    else:
        storage[91]=storage[91]+amount
    return storage

def dischargeFromStorage(amount,storage,discharge):
    initialStorage=storage
    if(10*storage[7]>amount):
        storage[7]=storage[7]-(amount/10)
        storage[23]=storage[30]=storage[41]=storage[45]=storage[50]=storage[59]=storage[70]=storage[82]=storage[105]=storage[7]
        return storage
    elif(storage[7]>0):
        amount=amount-(10*storage[7])
        storage[7]=0
        storage[23]=storage[30]=storage[41]=storage[45]=storage[50]=storage[59]=storage[70]=storage[82]=storage[105]=storage[7]
    if(storage[2]>amount):
        storage[2]=storage[2]-amount
        return storage
    elif(storage[2]>0):
        amount=amount-storage[2]
        storage[2]=0
    if(storage[4]>amount):
        storage[4]=storage[4]-amount
        return storage
    elif(storage[4]>0):
        amount=amount-storage[4]
        storage[4]=0
    if(storage[16]>amount):
        storage[16]=storage[16]-amount
        return storage
    elif(storage[16]>0):
        amount=amount-storage[16]
        storage[16]=0
    else:
        storage[91]=storage[91]-amount
    return storage

def addStorage2Gen(initialStorage,storage,genVec,correction):
    change=storage-initialStorage

    #change = [(i > 0) * i for i in change] ##################################################################Maybe uncomment
    genVec=genVec+change
    genVec[79]=correction

    return genVec

def RegTimeStep(load,solar,w0,w1,w2,w3,storageCap,discharge,gen,storage):
    #Baseload
    initialStorage=storage
    genVec=0*genCap
    genVec[48]=genVec[99]=genVec[11]=genVec[79]=10
    genVec[10]=w1
    genVec[29]=w2
    genVec[61]=w2
    genVec[88]=w3
    genVec[0]=solar
    
    baseWindDifference=w0-10
    storage[79]=storage[79]+baseWindDifference
    if(storage[79]>storageCap[79]):
        storage[79]=storageCap[79]
    elif(storage[79]<0):
        need=abs(storage[79])
        genVec[79]=genVec[79]-need
        load=load+need
        storage[79]=0
   
    correction=genVec[79]
    if(30+genVec[79]>=load):
        diff=(30+genVec[79])-load
        storage[79]=storage[79]+diff
        if(storage[79]>storageCap[79]):
            storage[79]=storageCap[79]
        if(storage[2]+solar<storageCap[2]):
            storage[2]=storage[2]+solar
        elif(storage[2]<storageCap[2]):
            #genVec[0]=storageCap[2]-storage[2]
            diffSolar=storageCap[2]-storage[2]
            storage[2]=storageCap[2]
            storage=chargeToStorage(diffSolar, storage, storageCap, discharge)
        else:
            #genVec[0]=storageCap[2]-storage[2]
            storage[2]=storageCap[2]
            storage=chargeToStorage(solar, storage, storageCap, discharge)
        genVec=addStorage2Gen(initialStorage,storage,genVec,correction)
        gen.append(genVec)
        storage=chargeToStorage(w1+2*w2+w3, storage, storageCap, discharge) 
        return storage,gen 
    load=load-(30+genVec[79])
    #RES GEN
    totWind=w1+2*w2+w3
    if(load<=totWind):
        diff=totWind-load
        storage=chargeToStorage(diff,storage,storageCap,discharge)
        if(storage[2]+solar<storageCap[2]):
            storage[2]=storage[2]+solar
        elif(storage[2]<storageCap[2]):
            #genVec[0]=storageCap[2]-storage[2]
            diffSolar=storageCap[2]-storage[2]
            storage[2]=storageCap[2]
            storage=chargeToStorage(diffSolar, storage, storageCap, discharge)
        else:
            #genVec[0]=storageCap[2]-storage[2]
            storage[2]=storageCap[2]
            storage=chargeToStorage(solar, storage, storageCap, discharge)
        genVec=addStorage2Gen(initialStorage,storage,genVec,correction)
        gen.append(genVec)
        return storage,gen
    load=load-totWind
    if(load<=solar):
        diff=solar-load
        #storage=chargeToStorage(diff,storage,storageCap,discharge)
        if(storage[2]+diff<storageCap[2]):
            storage[2]=storage[2]+diff
        elif(storage[2]<storageCap[2]):
            diffSolar=storageCap[2]-storage[2]
            storage[2]=storageCap[2]
            storage=chargeToStorage(diffSolar, storage, storageCap, discharge)
        else:
            #genVec[0]=storageCap[2]-storage[2]
            storage[2]=storageCap[2]
            storage=chargeToStorage(diff, storage, storageCap, discharge)
        genVec=addStorage2Gen(initialStorage,storage,genVec,correction)
        gen.append(genVec)
        return storage,gen
    load=load-solar
    storage=dischargeFromStorage(load,storage,discharge)
    genVec=addStorage2Gen(initialStorage,storage,genVec,correction)
    gen.append(genVec)
    
    return storage,gen

genCap,storageCap,discharge=buildNetwork('/Users/simon/Desktop/NetworkMatrix.csv',118)
plt.show()

data = pd.read_excel("/Users/simon/Desktop/LoadProfile.xlsx", sheet_name="Sheet1")
load=data['Load (MW)']
data = pd.read_excel("/Users/simon/Desktop/RES.xlsx", sheet_name="Sheet1")
w0=np.repeat(np.array(data['Wind0']) /1000,12)
w1= np.repeat(np.array(data['Wind1'])/500,12)
w2= np.repeat(np.array(data['Wind2'])/500,12)
w3= np.repeat(np.array(data['Wind3'])/500,12)
solar=np.repeat(np.array(data['Solar'])/(1000000),12)

storage=storageCap*.5
#storage[16]=3200
gen=[]
print("\nBEGINNING SIMULATION")
plotLoad=[]
storageThing=[]
tVec=[]
forecast=[]
totalDischarge=0
first=0
last=0
storageCalc=0
var=0
rocStorage=np.zeros(118)
duplicate=np.array([])

for t in range(len(solar)):#34000,36000):
    #print(t)
    tVec.append(5*t)
    tempStorage=storage
    plotLoad.append(load[t])
    forecast.append(load[t]*random.uniform(0.95,1.05))
    storage,gen=RegTimeStep(load[t],solar[t],w0[t],w1[t],w2[t],w3[t],storageCap,discharge,gen,storage)
    
    total=sum(gen[-1])
    if(t==0):
        first=load[t]-total
    elif(t==len(solar)-1):
        last=load[t]-total
    if((load[t]-total)<storageCalc):
        totalDischarge=totalDischarge+storageCalc-(load[t]-total)
    storageCalc=load[t]-total
    storageThing.append(storageCalc)
    
    if(t!=0):
        up=abs(np.array(storage)-duplicate)
        rocStorage=rocStorage+up
        var=var+sum(abs(duplicate-np.array(storage)))
    else:
        innit=storage
    duplicate=np.array(storage)
    

upStorage=rocStorage/(2)
differenceVec=duplicate-innit
print("Yearly Hydro Discharge Total: ",upStorage[16])
upStorage[16]=upStorage[91]=0
print("Yearly Gravity Discharge Total: ", upStorage[4]+upStorage[2])
upStorage[4]=upStorage[2]=0
print("Yearly Battery Discharge Total: ", sum(upStorage))
print(' ')
print("Yearly Hydro NET Total: ",differenceVec[16])
differenceVec[16]=differenceVec[91]=0
print("Yearly Gravity NET Total: ", differenceVec[4]+differenceVec[2])
differenceVec[4]=differenceVec[2]=0
print("Yearly Battery NET Total: ", sum(differenceVec))
gen=np.array(gen)
storage=np.array(storageThing)
#plt.plot(load)
landfill=gen[:,48]*3+storage
baseWind=gen[:,79]+landfill
wind=gen[:,10]+gen[:,29]+gen[:,61]+gen[:,88]+baseWind
solar=gen[:,0]+wind


UtilStorage=gen[:,2]
Seasonal=gen[:,4]
batteries=gen[:,7]*10
hodge=gen[:,16]
lake=gen[:,91]

print("SIMULATION COMPLETE")


#plt.fill_between(tVec,storageThing, label= 'storage')
#plt.plot(tVec,plotLoad, color='k',label='Load Demand')
#plt.plot(tVec,forecast, '-',color='r',label='Forecast')
plt.fill_between(tVec,solar,color='orange', label= 'Utility solar')
plt.fill_between(tVec,wind,color='c', label= 'Utility wind')
plt.fill_between(tVec,baseWind,color='b', label= 'base Wind')
plt.fill_between(tVec,landfill,color='g', label= 'Landfill' )
plt.fill_between(tVec,storage,color='m', label= 'storage')

plt.title("Generation Stack With Storage ")
plt.xlabel("Time (minutes)")
plt.ylabel("Power (MW)")
plt.legend()
plt.show()
'''
plt.plot(UtilStorage, label= 'Solar Storage')
plt.plot(Seasonal, label= 'Seasonal Storage')
plt.plot(batteries, label='Battery Storage')
plt.plot(hodge,label='Lake hodge')
plt.legend()
'''
    
    
    
gen=np.array(gen)
storage=np.array(storageThing)
#plt.plot(load)
landfill=gen[:,48]*3
baseWind=gen[:,79]+landfill
wind=gen[:,10]+gen[:,29]+gen[:,61]+gen[:,88]+baseWind
solar=gen[:,0]+wind


UtilStorage=gen[:,2]
Seasonal=gen[:,4]
batteries=gen[:,7]*10
hodge=gen[:,16]
lake=gen[:,91]

generation=[landfill,baseWind,wind,solar,storage]


#plt.fill_between(tVec,storageThing, label= 'storage')
plt.fill_between(tVec,solar,color='orange', label= 'Utility solar')
plt.fill_between(tVec,wind,color='c', label= 'Utility wind')
plt.fill_between(tVec,baseWind,color='b', label= 'base Wind')
plt.fill_between(tVec,landfill,color='g', label= 'Landfill' )
#plt.fill_between(tVec,storage,color='m', label= 'storage')
plt.plot(tVec,plotLoad, color='k',label='Load Demand')
plt.title("Generation Stack Without Storage (Peak Load)")
plt.xlabel("Time (minutes)")
plt.ylabel("Power (MW)")
plt.legend()
plt.show()
    

np.savetxt("/Users/simon/Desktop/FinalMix.csv", generation, delimiter=",")
    

print(totalDischarge)

print(last-first)

    
    