'''
Image names from scanner:

Aim is to change the numbering of the file to obay certain rule:
first image is img_000.jpg    img_001.jpg    img_002.jpg    ...
Then the file names will be easily connected with the scanned time point.
The script is also able to preserve the file creation time in a pickle file,
and able to restore all names and times with a second run of this script on
the same directory
'''


import os
import pickle
import platform
from datetime import datetime
import re

# If the script is located in the folder:
# path = os.path.dirname(os.path.realpath(__file__))

recognizableImageExtensions = ['.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.png']


def determineExtension(path):
    # find extension
    extList = []
    for file in os.listdir(path):
        name, ext = os.path.splitext(file)
        extList.append(ext)

    allExts = list(set(extList))
    mostExts = []
    occurrences = []
    for ext in allExts:
        occurrences.append(extList.count(ext))
    maxOcc = max(occurrences)
    for i, occ in enumerate(occurrences):
        if occ == maxOcc:
            mostExts.append(allExts[i])
    while len(mostExts) != 1:
        # remove none image extensions
        remove = False
        for ext in mostExts:
            if ext not in recognizableImageExtensions:
                mostExts.remove(ext)
                remove = True
        if len(mostExts) == 0:
            print(f"I didn't recognize any image files in this path.\n{path}")
            return None, None
        if not remove:  # means there are two image format with equal amount, ask for help
            isSet = False
            while not isSet:
                ext = input(
                    f"I don't know which extension is correct, please choose one:\n{mostExts}\n")
                if ext in mostExts:
                    mostExts = [ext, ]
                    isSet = True
                else:
                    print('Please type in ".***" (including the dot)')
    extension = mostExts[0]
    return extension


def determinePrefixExtension(path):
    """
    Find extension first, by the most aboundant and picture ones,
    Find prefix second, by remove numbering of files with found extension.
    """
    extension = determineExtension(path)
    # find prefix
    prefixList = []
    totalNum = 0
    for file in os.listdir(path):
        name, ext = os.path.splitext(file)
        if ext == extension:
            totalNum += 1
            nums = re.findall(r'[0-9]+', name)
            if len(nums) != 0:
                num = nums[-1]
                prefix = name[:-len(num)]
            else:
                continue
            prefixList.append(prefix)
    # dereplication
    prefixList = list(set(prefixList))
    while len(prefixList) != 1:  # ask for help
        isSet = False
        while not isSet:
            prefix = input(
                f"I don't know which prefix is correct, please choose one:\n{prefixList}\n")
            if prefix in prefixList:
                prefixList = [prefix, ]
                isSet = True
            else:
                print('Please type in any of the above.')
    prefix = prefixList[0]

    if totalNum < 100:
        digits = 2
    elif totalNum < 10000:
        digits = 3
    elif totalNum < 100000:
        digits = 4
    else:
        print(f'Are you sure, {totalNum} of files? (I quit)')
        exit()

    return prefix, extension, totalNum, digits
# determinePrefixExtension


def getScanTime(filePath):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        timeCreation = os.path.getctime(filePath)
    else:
        stat = os.stat(filePath)
        # the file is from windows, so I can not get ctime from MacOS or linux. mtime is enough
        timeCreation = stat.st_mtime
    return timeCreation
# getScanTime


def changeToNew(path, dictOld2New, dictOldScanTime, logFile):
    """Pass empty dict for dictOld2New and dictOldScanTime if fresh"""
    isFresh = False
    # if empty dict is passed, then I know file names are intact
    if len(dictOld2New) == 0:
        isFresh = True
        prefix, extension, totalNum, digits = determinePrefixExtension(path)
        files = [file for file in os.listdir(path) if file.endswith(extension)]
    else:
        files = dictOld2New.keys()

    nameChangeDict = {}
    for oldName in files:
        oldFilePath = os.path.join(path, oldName)
        if isFresh:
            foundNo1 = False
            nums = re.findall(r'[0-9]+', oldName)
            if len(nums) != 0:
                num = int(nums[-1]) - 1  # scanner starts numbering from 2
            else:
                num = 0
                if foundNo1:
                    print('Another file with no numbering?')
                    exit()
                else:
                    foundNo1 = True
            if not oldName.startswith(prefix[:-1]):
                print(f'{oldName} not starts with {prefix}')
            newName = f'{prefix}{str(num).zfill(digits)}{extension}'
            dictOld2New[oldName] = newName
            dictOldScanTime[newName] = getScanTime(oldFilePath)
        else:
            newName = dictOld2New[oldName]
        newFilePath = os.path.join(path, newName)
        if os.path.isfile(newFilePath):
            newFilePath = f"{newFilePath}_temp"
        nameChangeDict[oldFilePath] = newFilePath
    # If above loop is finished with no error, then do change name
    counter = 0
    for oldFilePath in nameChangeDict:
        newFilePath = nameChangeDict[oldFilePath]
        os.rename(oldFilePath, newFilePath)
    for file in os.listdir(path):
        if file.endswith('_temp'):
            name = file[:-5]
            tempPath = os.path.join(path, file)
            correctPath = os.path.join(path, name)
            os.rename(tempPath, correctPath)
    isNew = True
    # write info to new file
    with open(logFile, 'wb') as fileNameLog:
        pickle.dump((dictOld2New, dictOldScanTime, isNew), fileNameLog)
# changeToNew


def changeToOld(path, dictOld2New, dictOldScanTime, logFile):
    nameChangeDict = {}
    for oldName in dictOld2New:
        oldFilePath = os.path.join(path, oldName)
        newName = dictOld2New[oldName]
        newFilePath = os.path.join(path, newName)
        if not os.path.isfile(newFilePath):
            print(f'File not found {newFilePath}')
            raise
        if os.path.isfile(oldFilePath) and newFilePath != oldFilePath:
            # the origional file name is being occupied by a different file
            oldFilePath = f'{oldFilePath}_temp'
        atime = dictOldScanTime[newName]
        mtime = dictOldScanTime[newName]
        nameChangeDict[oldFilePath] = (newFilePath, atime, mtime)
    for oldFilePath in nameChangeDict:
        newFilePath, atime, mtime = nameChangeDict[oldFilePath]
        os.rename(newFilePath, oldFilePath)
        os.utime(oldFilePath, (atime, mtime))
    for file in os.listdir(path):
        if file.endswith('_temp'):
            name = file[:-5]
            tempPath = os.path.join(path, file)
            correctPath = os.path.join(path, name)
            os.rename(tempPath, correctPath)
    isNew = False
    # refresh info file
    with open(logFile, 'wb') as fileNameLog:
        pickle.dump((dictOld2New, dictOldScanTime, isNew), fileNameLog)
# changeToOld


def changeFileName(path):
    """Require changeToNew and changeToOld"""
    logFile = os.path.join(path, 'name&timeLog')

    if os.path.isfile(logFile):
        with open(logFile, 'rb') as fileNameLog:
            dictOld2New, dictOldScanTime, isNew = pickle.load(fileNameLog)
        if not isNew:
            changeToNew(path, dictOld2New, dictOldScanTime, logFile)
        else:  # then we need to change back
            changeToOld(path, dictOld2New, dictOldScanTime, logFile)
    else:
        dictOld2New = {}
        dictOldScanTime = {}
        changeToNew(path, dictOld2New, dictOldScanTime, logFile)
    return logFile
# changeFileName


def writeTable(path, logFile):
    '''
    TSV file is written separately
    path can be a different directory
    logFile is the full path to the logFile
    '''
    with open(logFile, 'rb') as fileNameLog:
        dictOld2New, dictOldScanTime, isNew = pickle.load(fileNameLog)

    for newName in dictOldScanTime:
        timeCreation = dictOldScanTime[newName]
    maxTime = max(dictOldScanTime.values())
    minTime = min(dictOldScanTime.values())
    maxDate = datetime.fromtimestamp(
        maxTime).strftime("%A, %d %B %Y, %H:%M:%S").split(', ')[1]
    minDate = datetime.fromtimestamp(
        minTime).strftime("%A, %d %B %Y, %H:%M:%S").split(', ')[1]
    logTsv = os.path.join(path, f'scanLog{minDate}-{maxDate}.tsv'.replace(' ', '_'))

    if os.path.isfile(logTsv):
        print(f'Already a file {logTsv}')
        pass
    else:
        with open(logTsv, 'w') as logTsv:
            lines = []
            for oldName in dictOld2New:
                newName = dictOld2New[oldName]
                timeCreation = dictOldScanTime[newName]
                timeStr = datetime.fromtimestamp(
                    timeCreation).strftime("%A, %d %B %Y, %H:%M:%S")
                weekDay = timeStr.split(', ')[0]
                scanDate = timeStr.split(', ')[1]
                scanTime = timeStr.split(', ')[2]
                lines.append(
                    f'{oldName}\t{newName}\t{weekDay}\t{scanDate}\t{scanTime}\n')
            lines.sort(key=lambda line: line.split('\t')[1])
            lines.insert(0, 'old_name\tnew_name\tweek_day\tdate\tscan_time\n')
            logTsv.writelines(lines)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='pass a directory as first argument')
    parser.add_argument('path')
    args = parser.parse_args()
    path = args.path

    logFile = changeFileName(path)
    writeTable(path, logFile)
