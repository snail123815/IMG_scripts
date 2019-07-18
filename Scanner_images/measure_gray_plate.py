import os
from skimage import draw
from skimage.io import imread
from skimage.draw import circle
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import pickle
from changeName import getScanTime
import re
import codecs  # for possible unicode character, not fully tested
from datetime import datetime
from shutil import copy2


def findPositions(digStr):
    position = []
    column = ['L', 'R']
    row = ['T', 'M', 'B']
    for i, l in enumerate(digStr):
        if l != '0':
            position.append(row[i] + column[int(l) - 1])
    return position


def measureCenterCircle(filePathList, radPrecent, useFileTime=True, imgTimeDiff=0.5, minMaxNorm=True):
    pos = os.path.split(os.path.split(filePathList[0])[0])[1]
    results = pd.DataFrame(columns=['time', pos])
    for filePath in filePathList:
        if useFileTime:
            time = getScanTime(filePath)
        else:
            time = int(re.findall(r'[0-9]+', filePath)[-1]) * imgTimeDiff * 3600
        # print(f'Processing {os.path.split(filePath)[1]}')
        im = imread(filePath, as_gray=True)
        center = (tuple(a / 2 for a in im.shape))
        radius = im.shape[0] / 2 * radPrecent
        rr, cc = circle(*center, radius)
        roi = im[rr, cc]
        newRow = pd.DataFrame({'time': time, pos: np.average(roi)}, index=[0])
        results = results.append(newRow, ignore_index=True)
    results = results.sort_values('time').reset_index(drop=True)
    results['time'] -= results['time'][0]
    results['time'] = results['time'] / 3600  # convert seconds to hour
    results[pos] -= results[pos].min()
    # Normalization
    if minMaxNorm:
        results[pos] = results[pos] / results[pos].max()
    results.index = results['time']
    results = results.drop('time', axis=1)
    return results


def draw_line(ax, li, cl, yMax=1):
    '''draw virtical lines on the position in li
    color in list cl'''
    ymin, ymax = ax.get_ylim()
    yspan = ymax - ymin
    for x, line in enumerate(li):
        if li[x] == 24:
            ax.axvline(li[x], color=cl[x], ymin=yspan * 0.05, ymax=yspan * 0.2)
        else:
            ax.axvline(li[x], color=cl[x], ymin=yspan * 0.8, ymax=yspan * 0.99)
            ax.text(li[x], ymax * 1.01, f'{li[x]}h', color=cl[x],
                    horizontalalignment='center', fontsize=7)


def getInfo(sampleInfoTsvPath):
    '''sampleInfo[posName][info] = elements[i + 1]'''
    sampleInfo = {}
    with codecs.open(sampleInfoTsvPath, encoding='utf-8', mode='r') as posFile:
        infoStarted = False
        for line in posFile.readlines():
            elements = [elem.strip() for elem in line.split('\t')]
            elements = [elem for elem in elements if elem != '']
            elements = [elem for elem in elements if not elem.startswith('#')]
            if len(elements) == 0:
                continue
            if elements[0] == 'sampleInfo':
                infoStarted = True
                sampleInfoHeader = [elem for elem in elements[1:]]
                continue
            if not infoStarted:
                continue
            posName = elements[0]
            if posName == 'end_info':
                break
            sampleInfo[posName] = {}
            for i, info in enumerate(sampleInfoHeader):
                sampleInfo[posName][info] = elements[i + 1]
    return sampleInfo


def measureOnePlate(path, fileExt):
    filePathes = [os.path.join(path, file)
                  for file in os.listdir(path) if file.endswith(fileExt)]
    results = measureCenterCircle(filePathes, 0.7)
    return results


def plotMeasured(allPicsData, sampleInfo, fillBetween, outputPath,
                 drawLines=[24, 48, 96], lineColor=['k', 'b', 'r'], timeRange=[0, 96], level=None, groupSequence=None, isSatisified=False):
    # calculate average and stderr
    if level == None:
        level = next(iter(next(iter(sampleInfo.values())).keys()))
        # else level = level

    fig, ax = plt.subplots(1, 1)

    if fillBetween:
        # dereplicate group keys under this level
        groups = []
        for posName in sampleInfo:
            groups.append(sampleInfo[posName][level])
        groups = list(set(groups))
        groups.sort()
        if groupSequence != None:
            newGroups = ['' for group in groups]
            for i, seq in enumerate(groupSequence):
                newGroups[seq] = groups[i]
            groups = newGroups
        # generate dictionary of group name -> positions
        groupPoses = {}
        for group in groups:
            groupPoses[group] = []
        for posName in sampleInfo:
            groupPoses[sampleInfo[posName][level]].append(posName)

        means = {}  # for use of output
        stderrs = {}  # for use of output
        for group in groups:
            means[group] = allPicsData[groupPoses[group]].mean(axis=1)
            stderrs[group] = allPicsData[groupPoses[group]].sem(axis=1)
            ax.plot(means[group], label=group)
            ax.fill_between(means[group].index, means[group] + stderrs[group],
                            means[group] - stderrs[group], alpha=0.3)
        # output
        outputFile = os.path.join(outputPath, f'data_statistic.xlsx')
        if not os.path.isfile(outputFile):
            dataOutput = pd.DataFrame()
            for group in groups:
                singleGroupStatistic = pd.concat((means[group], stderrs[group]), axis=1)
                singleGroupStatistic.columns = [f'{group}_mean', f'{group}_stderr']
                dataOutput = pd.concat((dataOutput, singleGroupStatistic), axis=1)
                dataOutput.to_excel(os.path.join(outputPath, f'data_statistic.xlsx'))
    else:
        lineNames = list(sampleInfo.keys())  # convert unordered dict to list
        if groupSequence != None:
            newLineNames = ['' for info in lineNames]
            for i, seq in enumerate(groupSequence):
                newLineNames[seq] = lineNames[i]
            lineNames = newLineNames
        for posName in lineNames:
            ax.plot(allPicsData[posName], label=sampleInfo[posName][level])
    # plot beautify
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    timeSpan = timeRange[1] - timeRange[0]
    ax.set_xticks(np.arange(0, timeSpan + 1, 6))
    timeRange = [timeRange[0] - timeSpan * 0.05, timeRange[1] + timeSpan * 0.05]
    ax.set_xlim(timeRange)
    yMax = ax.get_ylim()[1]
    draw_line(ax, drawLines, lineColor, yMax=yMax)
    plt.xlabel('time (h)')
    plt.ylabel('brightness')
    plt.title('Growth pattern', y=1.04)
    plt.legend(ncol=1, fontsize=8, framealpha=0.3)
    plt.tight_layout()
    if not isSatisified:
        plt.show()
    else:
        outputFig = os.path.join(outputPath, f'{datetime.now().strftime("%Y.%m.%d-%H.%M.%S")}.svg')
        plt.savefig(outputFig)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument('rootPath', help='Path to root dir with sub folders for each plate')
    parser.add_argument('sampleInfoTsvPath',
                        help='tsv file for sample information, same name will be averaged')
    parser.add_argument('-o', '--outputPath',
                        help='''Location to store processed picture,
                                    same as rootPath if not specified''',
                        metavar='PATH')
    parser.add_argument('--inputFmt',
                        help='imput picutre extension, default "jpg"',
                        metavar='FMT',
                        default='jpg')
    parser.add_argument('--noFillBetween',
                        help='fill between stderr if not set',
                        action='store_false')
    parser.add_argument('--noTimeFromFile',
                        help='Time from origional file will be used in plotting if not set',
                        action='store_false')
    parser.add_argument('--minMaxNorm', help="Do normalization if set",
                        action='store_true')

    args = parser.parse_args()
    rootPath = args.rootPath.strip()
    sampleInfoTsvPath = args.sampleInfoTsvPath.strip()
    outputPath = args.outputPath
    outputPath = (rootPath if outputPath == None else outputPath.strip())
    fileExt = f'.{args.inputFmt}'
    fillBetween = args.noFillBetween
    timeFromFile = args.noTimeFromFile
    minMaxNorm = args.minMaxNorm

    if not os.path.isdir(rootPath):
        print(f'rootPath {rootPath} does not exist.')
        raise
    if not os.path.isfile(sampleInfoTsvPath):
        print(f'sample information table {sampleInfoTsvPath} does not exist.')
        raise
    sampleInfo = getInfo(sampleInfoTsvPath)
    folders = sampleInfo.keys()

    dataPickle = os.path.join(outputPath, 'data.pickle')
    isMeasured = False
    if os.path.isfile(dataPickle):
        isMeasured = True
    if not isMeasured:
        allPicsData = pd.DataFrame()
        threadPool = ThreadPoolExecutor(max_workers=8)
        futures = []
        for folder in folders:
            future = threadPool.submit(measureOnePlate,
                                       os.path.join(rootPath, folder),
                                       fileExt)
            futures.append(future)
            print(f'Submited {folder}.')

        exceptions = [future.exception() for future in futures]
        for i, excep in enumerate(exceptions):
            if excep != None:
                print(f'There is exception in run index {i}:')
                print(excep)
                break
        threadPool.shutdown()  # wait for every thread to complete
        for future in futures:
            results = future.result()
            allPicsData = pd.concat((allPicsData, results), axis=1)
        with open(dataPickle, 'wb') as resultData:
            pickle.dump(allPicsData, resultData)
        allPicsData.to_excel(f'{os.path.splitext(dataPickle)[0]}.xlsx')
    else:
        with open(dataPickle, 'rb') as resultData:
            allPicsData = pickle.load(resultData)
################
    groupSequence = [0, 3, 1, 2]  # index of origional sequence
    drawLines = [24, 52, 52.5, 56]
    lineColor = ['k', 'C1', 'C0', 'C2']
    timeRange = [0, 68.5]
    plotMeasured(allPicsData, sampleInfo, fillBetween, outputPath,
                 drawLines=drawLines, timeRange=timeRange, groupSequence=groupSequence, lineColor=lineColor)

    # copy this script to outputPath for later references
    pathThisScript = os.path.realpath(__file__)
    isSatisified = input("Satisfied with the result? y/n:")
    if isSatisified == 'y':
        plotMeasured(allPicsData, sampleInfo, fillBetween, outputPath,
                     drawLines=drawLines, timeRange=timeRange, groupSequence=groupSequence, lineColor=lineColor,
                     isSatisified=True)
        copy2(pathThisScript, outputPath)
        print('Result saved.')
    else:
        print('Result ignored')
