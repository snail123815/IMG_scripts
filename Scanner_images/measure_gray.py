import os
import pickle

from datetime import datetime
from shutil import copy2, copytree
from concurrent.futures import ThreadPoolExecutor

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from funcs import getInfo, getPositions, measureImgs, plotMeasured
from funcs.changeName import genLogFile

# TODO
# - [x] Add colour in the description csv
# - [x] `change_name` script, make it to recognise unusual names
# - [x] extractPicture script, need to know which location base comes from: from origin image? or cropped image?
# - [x] Make the changes of line drawing reflect on the fly (well, return to command line and draw again)
# - [ ] Make all functions can be called from one script


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument('rootPath', help='Path to root dir with sub folders for each plate')
    parser.add_argument('sampleInfoTsvPath',
                        help='tsv file for sample information, same name will be averaged, when multiple location files are needed, use the first one for this mandatory argument')
    parser.add_argument('--forceNoFillBetween',
                        help='fill between stderr if not set',
                        action='store_true')
    parser.add_argument('--noTimeFromFile',
                        help='Time from original file will be used in plotting if not set, else, use the numbers in file name, gapped by --imageInterval',
                        action='store_true')
    parser.add_argument('--imageInterval',
                        help='Hours, only affect if --noTimeFromFile is set or the creation time cannot be obtained from file',
                        default=1.0, type=float)
    parser.add_argument('--normType', help="Specify how the normalisation is done",
                        choices=['None', 'Each', 'Combined'], default='Combined')
    parser.add_argument('--startImageTiming', help="The timing of the first picture, in hours",
                        type=float, default=0.)
    parser.add_argument('--endTiming', help="The time of the last picture to plot, in hours",
                        type=float)
    parser.add_argument('--percentage', default=1.0, type=float,
                        help='This precent is to specify the precentage of the picture width to be considered')
    parser.add_argument('--reMeasure', action='store_true',
                        help='Force re-measure')
    parser.add_argument('--diffPos',
                        nargs='*',
                        help='''If your plates was moved during experiment, then you need multiple
                        position files.
                        This argument allows you to do:
                        [start file] [positionTsvPath] [start file] [positionTsvPath]...
                        DO NOT add the first file (start from 0) again.
                        The START FILE is the file name of the original file name. Check the log file for the old name.
                        ''')

    args = parser.parse_args()
    rootPath = args.rootPath.strip()
    sampleInfoTsvPath = args.sampleInfoTsvPath.strip()
    forceNoFillBetween = args.forceNoFillBetween
    noTimeFromFile = args.noTimeFromFile
    imageInterval = args.imageInterval
    normType = args.normType
    startImageTiming = args.startImageTiming
    timeZ = args.endTiming
    percentage = args.percentage
    reMeasure = args.reMeasure
    diffPos = args.diffPos

    assert os.path.isdir(rootPath), f'rootPath {rootPath} does not exist.'
    assert os.path.isfile(sampleInfoTsvPath), f'sample information table {sampleInfoTsvPath} does not exist.'
    sampleInfo = getInfo(sampleInfoTsvPath)

    args_static = [sampleInfo, noTimeFromFile, imageInterval, normType, percentage]
    allPicsData = pd.DataFrame()

    # Check if dataFile exists
    measure = True
    dataPickle = os.path.join(rootPath, 'data.pickle')
    if not reMeasure and os.path.isfile(dataPickle):
        if os.stat(dataPickle).st_size > 0:
            with open(dataPickle, 'rb') as resultData:
                allPicsData, args_static_old = pickle.load(resultData)
                if args_static_old == args_static:  # arguments affect measured data
                    measure = False

    # Read file names from log file
    renameLogFile = genLogFile(rootPath)
    oldFiles, newFiles = ([], [])
    with open(renameLogFile, 'rb') as f:
        dictOld2New, _, _ = pickle.load(f)
    for of in dictOld2New:
        oldFiles.append(of)
        newFiles.append(dictOld2New[of])
    # sort oldFiles based on newFiles
    oldFiles = [f for _, f in sorted(zip(newFiles, oldFiles))]
    # sort newFiles after oldFiles is sorted
    newFiles.sort()

    # parse diffPos argument if present
    diffPosNums = [0, ]
    diffPosFiles = [sampleInfoTsvPath, ]
    if diffPos != None:
        if len(diffPos) % 2 != 0:
            parser.error('The --diffPos argument requires both number and file')
        # PARSE args
        for imgfile, posFile in zip(diffPos[0::2], diffPos[1::2]):
            if imgfile not in oldFiles:
                raise ValueError(f'File {imgfile} missing from the original file names')
            diffPosNums.append(oldFiles.index(imgfile))
            diffPosFiles.append(posFile)

    if measure:

        threadPool = ThreadPoolExecutor(max_workers=8)
        futures = []

        for folder in sampleInfo:
            measureType = sampleInfo[folder]['measure']
            assert measureType in ['centreDisk', 'square', 'polygon'], \
                f'Error found in sample information file, "measure" should be in [\'centreDisk\', \'square\', \'polygon\'], {measureType} found.'

            polygons = [(0, 0, 1, 0, 0, 1), ]  # polygon initiation for non-polygon measurments
            if measureType == 'polygon':  # needs to go back to posDict to find location

                # Generate polygon locations
                polygons = []  # reset this to start with 0
                for i, (num, positionTsvPath) in enumerate(zip(diffPosNums, diffPosFiles)):
                    try:
                        nextGroupStart = diffPosNums[i + 1]
                    except IndexError:  # reach the end
                        nextGroupStart = diffPosNums[i] + 1
                    posDict = getPositions(diffPosFiles[0])
                    polygon = posDict['Polygon_poly'][folder]
                    n = nextGroupStart - num
                    polygons.extend([polygon] * n)

            # Submit measurement to thread pool
            future = threadPool.submit(
                measureImgs,
                os.path.join(rootPath, 'subImages', folder),
                measureType,
                polygons=polygons,
                percentage=percentage,
                forceUseFileNumber=noTimeFromFile
            )
            futures.append(future)
            print(f'Submitted {folder} for processing.')

        # Exception handle
        exceptions = [future.exception() for future in futures]
        for i, excep in enumerate(exceptions):
            if excep != None:
                print(f'There is exception in run index {i}:')
                print(excep)
                break

        threadPool.shutdown()  # wait for every thread to complete

        # get results
        for future in futures:
            path, data = future.result()
            posName = os.path.split(path)[-1]
            # data processing according to arguments

            # rebase time to the first picture (if 3 (hours), then the data will start with 3)
            # Now the data should be actual hours (after the experimental time zero)
            data[:, 0] -= (data[:, 0].min() - startImageTiming)
            # sort on time
            timeSort = np.argsort(data[:, 0])
            data = data[timeSort, :]
            # Normalization
            if normType == 'Each':
                # use first 3 hours data as zero point
                zeroPoint = data[:3, 1].mean()
                values = data[:, 1] - zeroPoint
                data[:, 1] = values/values.max()

            # Put into data frame
            toDf = pd.DataFrame(data[:, 1], index=data[:, 0], columns=[posName])
            allPicsData = pd.concat((allPicsData, toDf), axis=1)

        if normType == 'Combined':
            min = allPicsData.iloc[:3].values.mean()  # will convert to nparray and calculate mean of everything
            values = allPicsData.values - min
            newData = values/values.max()
            # put data back
            allPicsData = pd.DataFrame(newData, index=allPicsData.index, columns=allPicsData.columns)

        with open(dataPickle, 'wb') as resultData:
            pickle.dump([allPicsData, args_static], resultData)
        allPicsData.to_excel(f'{os.path.splitext(dataPickle)[0]}.xlsx')

################# PLOTTING ##############

    # groupSequence = [2, 5]  # index of original sequence, see print out for reference
    vlines = []
    vlineColours = []
    timeRange = (startImageTiming, timeZ)
    lowerVlines = [24, ]
    allLevels = [k for k in list(list(sampleInfo.values())[0].keys()) if k not in ['measure', 'colour']]
    level = allLevels[0]  # use the first one

    #colours = [sampleInfo[s]['colour'].strip() for s in sampleInfo]

    # copy this script to outputPath for later references
    isSatisified = 'n'
    fig, plotData = (None, None)
    while isSatisified != 'y':
        fig, plotData = plotMeasured(allPicsData, sampleInfo, level, forceNoFillBetween,
                                     vlines=vlines, vlineColours=vlineColours, lowerVlines=lowerVlines, timeRange=timeRange)
        isSatisified = input("Satisfied with the result? y/n:")
        if isSatisified == 'y':
            break

        # Get values for the next plot
        newVlines = input("Vertical lines? Separate using spaces eg. '24 46 70'\n")
        try:
            newVlines = [int(i) for i in newVlines.split()]
            if len(newVlines) != 0:
                newVlineColours = input("Colours? Separate using spaces eg. 'k r b'\n")
                newVlineColours = [c.strip() for c in newVlineColours.split()]
                assert len(newVlineColours) == len(newVlines)
                vlines = newVlines
                vlineColours = newVlineColours
            newLowerVlines = input("Vertical lines that will plot at bottom? eg. '24 46'\n")
            try:
                newLowerVlines = [int(i) for i in newLowerVlines.split()]
                assert len(newLowerVlines) >= 1
                lowerVlines = newLowerVlines
            except:
                print(f'Lower vertical lines setup failed, use existing {lowerVlines}')
        except:
            print(f'Vertical line drawing setup failed, use existing {vlines}')
        newTimeRange = input("Time range? Separate using spaces eg. '0 72'\n")
        try:
            newTimeRange = [float(i) for i in newTimeRange.split()]
            assert len(newTimeRange) == 2 and newTimeRange[1] > newTimeRange[0]
            timeRange = newTimeRange
        except:
            print(f'Time range setup failed, use existing {timeRange}')
        newLevel = input(f"New level? {allLevels}\n")
        try:
            newLevel = newLevel.strip()
            assert newLevel in allLevels
            level = newLevel
        except:
            print(f'Level setup failed, use existing {level}')

    resultDir = os.path.join(rootPath, f'result_{datetime.now().strftime("%Y.%m.%d-%H.%M.%S")}')
    os.mkdir(resultDir)
    plotData.to_csv(os.path.join(resultDir, 'plotData.tsv'), sep='\t')
    plotData.to_excel(os.path.join(resultDir, 'plotData.xlsx'))
    argumentTxt = os.path.join(resultDir, 'arguments.txt')
    fig.savefig(os.path.join(resultDir, 'figure.svg'))
    with open(argumentTxt, 'w') as f:
        f.write(str(args))
        f.write(f'\n{" ".join([str(i) for i in vlines])}\t# Vertical lines')
        f.write(f'\n{" ".join(vlineColours)}\t# Vertical line colours')
        f.write(f'\n{" ".join([str(i) for i in lowerVlines])}\t# Lower vertical lines')
        f.write(f'\n{" ".join([str(i) for i in timeRange])}\t# Time range')
        f.write(f'\n{level}\t# Level')
    pathThisScript = os.path.realpath(__file__)
    copy2(pathThisScript, resultDir)
    for f in diffPosFiles:
        copy2(f, resultDir)
    pathFuncs = os.path.join(os.path.split(pathThisScript)[0], 'funcs')
    destFuncs = os.path.join(resultDir, 'funcs')
    copytree(pathFuncs, destFuncs)
    print('Result saved.')
