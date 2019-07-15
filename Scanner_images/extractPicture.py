from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import platform
import os
from changeName import getScanTime
discriptionText_extractPicture = '''
    Depends on Pillow (PIL Fork) https://pillow.readthedocs.io/en/latest/

    Picture of each plate will be extracted from origional scanned picture.
    Each position will be stored in separate dir:
    Note the initial resolution and the position will vary with different scanners
    and plate setup.

    !! Check Positions before you run this script!!!

    Example position file:

    CornerSize     x      y      size            # upper left corner position
    TL             420    350    1040
    TR             1460   350    1040
    ML             90     1390   1040
    MR             1100   1390   1040
    BL             420    2400   1040
    BR             1460   2400   1040
    TwoPositions   x1     y1     x2      y2      # upper left and lower right positions
    removePadding  90     350    2512    3454    # include this line if you need to remove certain padding
    end                                          # parse will stop here

    All origional pictures will be compressed to smaller size and stored in 'resized'
    directory.

    This will be done with multithreading.
'''


def getPositions(positionTsvPath):
    positionTypes = ['CornerSize', 'TwoPositions']
    posDict = {}
    type = ''
    removePadding = False

    def positionCorner(x, y, size):
        return x, y, x + size, y + size
    # positionCorner
    with open(positionTsvPath, 'r') as posFile:
        for line in posFile.readlines():
            elements = [elem.strip() for elem in line.split('\t')]
            if elements[0] == 'end':
                break
            elements = [elem for elem in elements if elem != '']
            elements = [elem for elem in elements if not elem.startswith('#')]

            if elements[0] in positionTypes:
                type = elements[0]
                posDict[type] = {}
            else:
                if type == '':
                    print('Error, no position type string found, check file.')
                    print('Current line')
                    print(line)
                    exit()
                posName = elements[0]
                position = tuple([int(elem) for elem in elements[1:]])
                if type == 'CornerSize':
                    position = positionCorner(*position)
                if posName == 'removePadding':
                    removePadding = True
                posDict[type][posName] = position
    return posDict, removePadding
# getPositions


def creatFolders(targetPath, folders):
    targetPaths = {}
    for folder in folders:
        newPath = os.path.join(targetPath, folder)
        if not os.path.isdir(newPath):
            os.mkdir(newPath)
        targetPaths[folder] = newPath
    return targetPaths
# creatFolders


def crop(picPath, posDict, targetPaths, removePadding=False, paddingPos=None, resizeFactor=None, useFileTime=True, isTest=False):
    picName = os.path.splitext(os.path.basename(picPath))[0]
    scanTime = getScanTime(picPath)
    atime, utime = (scanTime, scanTime)
    with Image.open(picPath) as im:
        iccProfile = im.info.get('icc_profile')
        if isTest:
            print(im.filename)
            print(iccProfile if iccProfile != None else 'No icc profiel')
            print(im.size)
            print(im.info)
        for posName in posDict:
            targetPath = targetPaths[posName]
            outFilePath = os.path.join(targetPath, f'{picName}_{posName}.bmp')
            im.crop(posDict[posName]).save(outFilePath,
                                           'bmp',
                                           icc_profile=iccProfile,
                                           )
            if useFileTime:
                os.utime(outFilePath, (atime, utime))
        if removePadding:
            if paddingPos == None:
                pass
            else:
                im = im.crop(paddingPos)
                # save cropped pictures
                croppedFilePath = os.path.join(targetPaths['cropped_ori'],
                                               f'{picName}_clean.bmp')
                im.save(croppedFilePath, 'bmp', icc_profile=iccProfile)
                if useFileTime:
                    os.utime(croppedFilePath, (atime, utime))
        if resizeFactor != None:
            resizeFilePath = os.path.join(targetPaths['resized'],
                                          f'{picName}_resized.jpg')
            newSize = tuple(int(size * resizeFactor) for size in im.size)
            im = im.resize(newSize)
            im.save(resizeFilePath,
                    'jpeg',
                    icc_profile=iccProfile,
                    progressive=True,
                    quality=85,
                    optimize=True)
            if useFileTime:
                os.utime(resizeFilePath, (atime, utime))
    return
# crop


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=discriptionText_extractPicture)
    parser.add_argument('picturesPath', help='Path with picutres to process')
    parser.add_argument('positionTsvPath', help='tsv file for positions')
    parser.add_argument('-r', '--resizeFactor', help='Factor of origional size (0-1), default 0.35',
                        type=float,
                        default=0.35,
                        metavar='FLOAT')
    parser.add_argument('-o', '--outputPath',
                        help='''Location to store processed picture,
                                same as picutrePath if not specified''',
                        metavar='PATH')
    parser.add_argument('--inputFmt',
                        help='imput picutre extension, default "jpg"',
                        metavar='FMT',
                        default='jpg')
    parser.add_argument('--noTimeFromFile',
                        help='Time from origional file will be stored in all new files if this is not set',
                        action='store_true')
    parser.add_argument('--test',
                        help='Only process the first image if set',
                        action='store_true')
    args = parser.parse_args()
    picturesPath = args.picturesPath.strip()
    positionTsvPath = args.positionTsvPath.strip()
    resizeFactor = args.resizeFactor
    outputPath = (picturesPath if args.outputPath == None else args.outputPath)
    inputExt = f'.{args.inputFmt}'
    useFileTime = (True if not args.noTimeFromFile else False)
    isTest = args.test

    if isTest:
        print(args)

    if not os.path.isdir(outputPath):
        os.mkdir(outputPath)

    allPosDict, removePadding = getPositions(positionTsvPath)
    folders = list(allPosDict['CornerSize'].keys())
    if removePadding:
        paddingPos = allPosDict['TwoPositions']['removePadding']
        folders.append('cropped_ori')
    else:
        paddingPos = None
    folders.append('resized')

    print('Creating folders...')
    targetPaths = creatFolders(outputPath, folders)

    print('Cropping...')
    fileList = sorted(list(file for file in
                           os.listdir(picturesPath) if file.endswith(inputExt)))
    filePathList = [os.path.join(picturesPath, file) for file in fileList]
    threadPool = ThreadPoolExecutor(max_workers=8)
    futures = []
    for i, file in enumerate(filePathList):
        future = threadPool.submit(crop, file, allPosDict['CornerSize'], targetPaths,
                                   removePadding=removePadding,
                                   paddingPos=paddingPos,
                                   resizeFactor=resizeFactor,
                                   useFileTime=useFileTime,
                                   isTest=isTest
                                   )
        print(f'Submitted {i}: {os.path.split(file)[-1]}')
        if i == 0:
            exception = future.exception()
            # this will wait the first implementation to finish, and check if
            # any exception happened
            if exception != None:
                print('There is exception in the first implementation:')
                print(exception)
                exit()
        futures.append(future)
        if isTest:
            print('Test run...')
            future.result()
            break
    print('All submitted! Waiting for finish.')
    exceptions = [future.exception() for future in futures]
    for i, excep in enumerate(exceptions):
        if excep != None:
            print(f'There is exception in run index {i}:')
            print(excep)
            break
    threadPool.shutdown()
    print('Finished!')
