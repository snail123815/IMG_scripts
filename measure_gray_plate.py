import os
from skimage import draw
from skimage.io import imread
from skimage.draw import circle
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import threading
import pickle

root = os.path.dirname(os.path.realpath(__file__))
folders = ('TL','TR','ML','MR','BL','BR')
timeLimit = 90
fillBetween = True
hi   = '011'
lo   = '022'

doMeasurementAll = True
minMaxNorm = False

def findPositions(digStr):
    position = []
    column = ['L', 'R']
    row = ['T', 'M', 'B']
    for i, l in enumerate(digStr):
        if l != '0':
            position.append(row[i]+column[int(l)-1])
    return position

hiPositions = findPositions(hi)
loPositions = findPositions(lo)


def measure(position, dataDFs):
    path = os.path.join(root, position)
    files = sorted([file for file in os.listdir(path) if file.endswith('.jpg')])

    data = pd.Series(name = position)
    for file in files:
        time = int(os.path.splitext(file)[0].split('_')[1])/2
        filePath = os.path.join(path, file)
        print(f'Processing {file}')
        im = imread(filePath, as_gray = True)
        center = (tuple(a/2 for a in im.shape))
        rr, cc = circle(*center, 400)
        roi = im[rr,cc]
        data.loc[time] = np.average(roi)
        # Normalization

        if minMaxNorm:
            dataNorm = (data - data.min())/(data.max() - data.min())
        else:
            dataNorm = data - data.min()
    dataDFs[position] = dataNorm

if doMeasurementAll:
    dataDFs = {}
    allPicsData = pd.DataFrame()
    threads = {}
    for folder in folders:
        threads[folder] = threading.Thread(target = measure, args = (folder, dataDFs))
        threads[folder].start()
    for folder in folders:
        threads[folder].join()
        allPicsData = pd.concat((allPicsData, dataDFs[folder]), axis = 1)
    timeIndex = allPicsData.index
    with open(os.path.join(root, 'result'),'wb') as resultData:
        pickle.dump(allPicsData, resultData)
else:
    with open(os.path.join(root, 'result'),'rb') as resultData:
        allPicsData = pickle.load(resultData)
        timeIndex = allPicsData.index
allPicsData.to_excel('/Users/durand.dc/Desktop/Scanner_images_Sanne/plate.xlsx')

fig, ax = plt.subplots(1,1)

if fillBetween:
    averageHi = pd.Series(np.average(allPicsData[hiPositions], axis = 1), index = timeIndex)
    stdWT = np.std(allPicsData[hiPositions], axis = 1)

    averageLo = pd.Series(np.average(allPicsData[loPositions], axis = 1), index = timeIndex)
    stdAtra = np.std(allPicsData[loPositions], axis = 1)

    ax.plot(averageHi, color = 'b', label = '0.5% glycerol')
    ax.fill_between(averageHi.index, averageHi+stdWT, averageHi-stdWT, color = 'b', alpha = 0.3)
    ax.plot(averageLo, color = 'r', label = '0.05% glycerol')
    ax.fill_between(averageHi.index, averageLo+stdAtra, averageLo-stdAtra, color = 'r', alpha = 0.3)
else:
    for position in hiPositions:
        ax.plot(timeIndex, allPicsData[position], label = f'0.05%_{position.lower()}')
    for position in loPositions:
        ax.plot(timeIndex, allPicsData[position], label = f'0.5%_{position.lower()}')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.xaxis.set_ticks_position('bottom')
ax.yaxis.set_ticks_position('left')
ax.set_xticks(np.arange(0,timeLimit,6))

ax.set_xlim(xmax = timeLimit)
yMax = ax.get_ylim()[1]
def draw_line(ax,li, cl):
    for x in range(len(li)):
        if li[x] == 24:
            ax.axvline(li[x], color = cl[x], ymin = 0.1, ymax = 0.3)
        else:
            ax.axvline(li[x], color = cl[x], ymin = 0.8, ymax = 0.99)
            ax.text(li[x],yMax,f'{li[x]}h', color = cl[x], horizontalalignment = 'center', fontsize = 7)

draw_line(ax, [54, 59], ['b', 'r'])
plt.xlabel('time (h)')
plt.ylabel('brightness')
plt.title('Growth pattern', y = 1.04)
plt.legend(ncol = 1, fontsize = 8, framealpha = 0.3)
plt.tight_layout()
# plt.legend(bbox_to_anchor=(1.04,1), loc="upper left", ncol = 1, fontsize = 6, framealpha = 0.3)
plt.show()