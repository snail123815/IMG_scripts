'''
Image names from scanner:
img_.jpg    img_1.jpg    ...    img_10    ...    img_100    ...

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

# If the script is located in the folder:
# path = os.path.dirname(os.path.realpath(__file__))

path = input('Please specify the directory:\n').strip()


prefix = 'img_'
extension = '.jpg'
digits = 3

logFile = os.path.join(path, 'fileNameLog')


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
    isFresh = False
    if len(dictOld2New) == 0:
        isFresh = True
        files = [file for file in os.listdir(path) if file.endswith(extension)]
        for oldName in files:
            dictOld2New[oldName] = ''

    for oldName in dictOld2New:
        oldFilePath = os.path.join(path, oldName)
        if isFresh:
            try:
                num = int(oldName.split('_')[-1].split('.')[0]) - 1
            except:
                num = 0
            newName = f'{prefix}{str(num).zfill(digits)}{extension}'
            dictOld2New[oldName] = newName
            dictOldScanTime[oldName] = getScanTime(oldFilePath)
        else:
            newName = dictOld2New[oldName]
        newFilePath = os.path.join(path, newName)
        os.rename(oldFilePath, newFilePath)
    with open(logFile, 'wb') as fileNameLog:
        pickle.dump((dictOld2New, dictOldScanTime, True), fileNameLog)
# changeToNew


def changeToOld(path, dictOld2New, dictOldScanTime):
    for oldName in dictOld2New:
        oldFilePath = os.path.join(path, oldName)
        newName = dictOld2New[oldName]
        newFilePath = os.path.join(path, newName)
        os.rename(newFilePath, oldFilePath)
        '''Then the timestamp of the file needs to be changed back: '''
        atime = dictOldScanTime[oldName]
        mtime = dictOldScanTime[oldName]
        os.utime(oldFilePath, (atime, mtime))
    isChanged = False
    with open(logFile, 'wb') as fileNameLog:
        pickle.dump((dictOld2New, dictOldScanTime, isChanged), fileNameLog)


def changeFileName(path, logFile):
    if os.path.isfile(logFile):
        with open(logFile, 'rb') as fileNameLog:
            dictOld2New, dictOldScanTime, isChanged = pickle.load(fileNameLog)
        if not isChanged:
            changeToNew(path, dictOld2New, dictOldScanTime, logFile)
        else:  # then we need to change back
            changeToOld(path, dictOld2New, dictOldScanTime)
    else:
        dictOld2New = {}
        dictOldScanTime = {}
        changeToNew(path, dictOld2New, dictOldScanTime, logFile)
# changeFileName


changeFileName(path, logFile)


'''
TSV file is written separately for only once:
'''
logTsv = os.path.join(path, 'fileNameLog.tsv')
if os.path.isfile(logTsv):
    pass
else:
    with open(logFile, 'rb') as fileNameLog:
        dictOld2New, dictOldScanTime, isChanged = pickle.load(fileNameLog)
    with open(logTsv, 'w') as logTsv:
        lines = []
        for oldName in dictOld2New:
            newName = dictOld2New[oldName]
            timeCreation = dictOldScanTime[oldName]
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
