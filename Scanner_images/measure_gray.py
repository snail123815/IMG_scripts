import os
from skimage import draw
from skimage.io import imread
from skimage.draw import circle
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import pickle
from changeName import getScanTime, determineExtension
import re
import codecs  # for possible unicode character, not fully tested
from datetime import datetime
from shutil import copy2, move


def measureCenterCircle(filePathList, radPrecent, useFileTime=True, imgTimeDiff=0.5, minMaxNorm=True, startTiming=0):
    # folder name = position string
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
    results['time'] = startTiming + results['time'] / 3600  # convert seconds to hour
    results[pos] -= results[pos].iloc[0:10].min()
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


def measureOnePlate(path, minMaxNorm, radPrecent=0.7, startTiming=0):
    extension = determineExtension(path)
    filePathes = [os.path.join(path, file)
                  for file in os.listdir(path) if file.endswith(extension)]
    results = measureCenterCircle(
        filePathes,
        radPrecent=radPrecent,
        useFileTime=True,
        imgTimeDiff=0.5,
        minMaxNorm=minMaxNorm, startTiming=startTiming
    )
    return results


def plotMeasured(allPicsData, sampleInfo, fillBetween, outputPath, startTiming=0,
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
        if not isSatisified:
            for i, group in zip(range(len(groups)), groups):
                print(f'{i} - {group}')
        if groupSequence != None:
            newGroups = []
            for seq in groupSequence:
                newGroups.append(groups[seq])
            groups = newGroups
        # generate dictionary of group name -> positions
        groupPoses = {}
        for group in groups:
            groupPoses[group] = []
        for posName in sampleInfo:
            group = sampleInfo[posName][level]
            if group in groups:
                groupPoses[group].append(posName)

        means = {}  # for use of output
        stderrs = {}  # for use of output
        totalMax = 0
        for group in groups:
            means[group] = allPicsData[groupPoses[group]].mean(axis=1)
            stderrs[group] = allPicsData[groupPoses[group]].sem(axis=1)
            max = means[group].max() + stderrs[group].loc[means[group].idxmax()]
            if max > totalMax:
                totalMax = max

        for group in groups:
            means[group] = means[group] / totalMax
            stderrs[group] = stderrs[group] / totalMax
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
    xtickInter = timeSpan // 6
    ax.set_xticks(np.arange(startTiming, timeRange[1], xtickInter))
    timeRange = [timeRange[0] - timeSpan * 0.05, timeRange[1] + timeSpan * 0.05]
    ax.set_xlim(timeRange)
    yMin, yMax = ax.get_ylim()
    ax.set_ylim(0 - (yMax - yMin) * 0.05, yMax)
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
    parser.add_argument('--startTiming', help="The time of the first picutre",
                        type=int, default=-1)
    parser.add_argument('--radPrecent', default=0., type=float,
                        help='Measuring circle, this precent is to specify the precentage of the picture width to be considered')

    args = parser.parse_args()
    rootPath = args.rootPath.strip()
    sampleInfoTsvPath = args.sampleInfoTsvPath.strip()
    outputPath = args.outputPath
    outputPath = (rootPath if outputPath == None else outputPath.strip())
    fileExt = f'.{args.inputFmt}'
    fillBetween = args.noFillBetween
    timeFromFile = args.noTimeFromFile
    minMaxNorm = args.minMaxNorm
    startTiming = args.startTiming
    if startTiming == -1:
        startTiming = 0
    radPrecent = args.radPrecent
    if radPrecent == 0.:
        radPrecent = 0.7

    dataPickle = os.path.join(outputPath, 'data.pickle')
    isMeasured = False
    if os.path.isfile(dataPickle):
        with open(dataPickle, 'rb') as resultData:
            allPicsData, startTiming_old, radPrecent_old = pickle.load(resultData)
            if startTiming == startTiming_old and radPrecent == radPrecent_old:
                isMeasured = True
            else:
                isMeasured = False
    else:
        isMeasured = False

    if not os.path.isdir(rootPath):
        print(f'rootPath {rootPath} does not exist.')
        raise
    if not os.path.isfile(sampleInfoTsvPath):
        print(f'sample information table {sampleInfoTsvPath} does not exist.')
        raise
    sampleInfo = getInfo(sampleInfoTsvPath)
    folders = sampleInfo.keys()

    if not isMeasured:
        allPicsData = pd.DataFrame()
        threadPool = ThreadPoolExecutor(max_workers=8)
        futures = []
        for folder in folders:
            future = threadPool.submit(
                measureOnePlate,
                os.path.join(rootPath, folder),
                minMaxNorm,
                radPrecent=radPrecent,
                startTiming=startTiming
            )
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
        if not minMaxNorm:
            max = allPicsData.max(axis=0).max()
            for col in allPicsData:
                allPicsData[col] = allPicsData[col] / max
        with open(dataPickle, 'wb') as resultData:
            pickle.dump([allPicsData, startTiming, radPrecent], resultData)
        allPicsData.to_excel(f'{os.path.splitext(dataPickle)[0]}.xlsx')
################
    groupSequence = [10, 21]  # index of origional sequence, see print out for reference
    # groupSequence = None
    drawLines = []
    lineColor = []
    timeRange = [20, 155]
    plotMeasured(allPicsData, sampleInfo, fillBetween, outputPath, startTiming=startTiming,
                 drawLines=drawLines, timeRange=timeRange, groupSequence=groupSequence, lineColor=lineColor)

    # copy this script to outputPath for later references
    pathThisScript = os.path.realpath(__file__)
    isSatisified = input("Satisfied with the result? y/n:")
    if isSatisified == 'y':
        plotMeasured(allPicsData, sampleInfo, fillBetween, outputPath,
                     drawLines=drawLines, timeRange=timeRange, groupSequence=groupSequence, lineColor=lineColor,
                     isSatisified=True)
        outputNote = os.path.join(
            outputPath, f'{datetime.now().strftime("%Y.%m.%d-%H.%M.%S")}.txt')
        with open(outputNote, 'w') as handle:
            handle.write(str(args))
        copy2(pathThisScript, outputPath)
        # copy2(sampleInfoTsvPath, outputPath)
        print('Result saved.')
    else:
        print('Result ignored')
