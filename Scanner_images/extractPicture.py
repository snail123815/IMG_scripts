import traceback
from concurrent.futures import ThreadPoolExecutor
import shutil
from PIL import Image
import platform
import os
from funcs import getScanTime, determinePrefixExtension, getPositions, createFolders
from funcs.changeName import genLogFile  # To get old file name when parsing multiple location data using old file name as reference
import pickle

discriptionText_extractPicture = '''
    Depends on Pillow (PIL Fork) https://pillow.readthedocs.io/en/latest/

    Picture of each plate will be extracted from original scanned picture.
    Each position will be stored in separate dir:
    Note the initial resolution and the position will vary with different scanners
    and plate setup.

    Measure the original file before removing the padding.
    Check `Bounding rectangle` in imageJ.

    !! Check Positions before you run this script!!!

    Example position file:

    CornerSize     x      y      size            # upper left corner position
    TL             420    350    1040
    TR             1460   350    1040
    ML             90     1390   1040
    MR             1100   1390   1040
    BL             420    2400   1040
    BR             1460   2400   1040
    TwoPositions   x     y     Width      Height      # upper left and lower right positions
    removePadding  52     360    2448    3080    # include this line if you need to remove certain padding
    end                                          # parse will stop here

    All original pictures will be compressed to smaller size and stored in 'resized'
    directory.

    This will be done with multithreading.
'''


def crop(picPath, posDict, targetPaths, paddingPos=None, resizeFactor=None, useFileTime=True, isTest=False):
    picName, extension = os.path.splitext(os.path.basename(picPath))
    if extension not in ['.bmp', '.tif', '.tiff', '.png']:
        outputFmt = 'jpeg'
        outputExt = '.jpg'
        # no need to save as bmp for already lossy pictures
    else:
        outputFmt = 'bmp'
        outputExt = '.bmp'
        # bmp files will be easier for compression latter
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
            targetPath = targetPaths[os.path.join('subImages', posName)]
            outFilePath = os.path.join(targetPath, f'{picName}_{posName}{outputExt}')
            im.crop(posDict[posName]).save(outFilePath,
                                           outputFmt,
                                           icc_profile=iccProfile,
                                           )
            if useFileTime:
                os.utime(outFilePath, (atime, utime))
        if paddingPos != None and not 'cropped_ori' in picPath:
            im = im.crop(paddingPos)
            # save cropped pictures
            croppedFilePath = os.path.join(targetPaths['cropped_ori'],
                                           f'{picName}_clean{outputExt}')
            im.save(croppedFilePath, outputFmt, icc_profile=iccProfile)
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
    parser.add_argument('path', help='Path to process, with original_images dir')
    parser.add_argument('infoTsvPath', help='metadata tsv file, only positions will be used')
    parser.add_argument('-r', '--resizeFactor', help='Factor of original size (0-1), default 0.35',
                        type=float,
                        default=0.35,
                        metavar='FLOAT')
    parser.add_argument('-o', '--outputPath',
                        help='''Location to store processed picture,
                                same as picutrePath if not specified''',
                        metavar='PATH')
    parser.add_argument('--inputFmt',
                        help='input picutre extension. Acceptable: [".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".png"]. Default to auto detection.',
                        metavar='FMT',
                        default='.auto')
    parser.add_argument('--noTimeFromFile',
                        help='Time from original file will be stored in all new files if this is not set',
                        action='store_false')
    parser.add_argument('--test',
                        help='Only process the first image if set',
                        action='store_true')
    parser.add_argument('--diffPos',
                        nargs='*',
                        help='''If your plates was moved during experiment, then you need multiple
                        position files.
                        This argument allows you to do:
                        [start file] [positionTsvPath] [start file] [positionTsvPath]...
                        You do not need to add the first part again.
                        The START FILE is the file name of the original file name. Check the log file for the old name.
                        ''')
    parser.add_argument('--locationFromCropped',
                        help='Set if the locations are measured from images in "cropped_ori" folder. Will only take effect if "original_images" folder is gone.',
                        action='store_true')
    args = parser.parse_args()
    path = args.path.strip()
    positionTsvPath = args.infoTsvPath.strip()
    resizeFactor = args.resizeFactor
    outputPath = (path if args.outputPath == None else args.outputPath)
    inputExt = args.inputFmt
    useFileTime = args.noTimeFromFile
    isTest = args.test
    diffPos = args.diffPos
    locFromCropped = args.locationFromCropped

    renameLogFile = genLogFile(path)
    oldFiles, newFiles = ([], [])
    with open(renameLogFile, 'rb') as f:
        dictOld2New, _, _ = pickle.load(f)
    for of in dictOld2New:
        oldFiles.append(of)
        newFiles.append(dictOld2New[of])
    # sort oldFiles based on newFiles
    oldFiles = [f for _, f in sorted(zip(newFiles, oldFiles))]
    # sort newFIles after oldFiles is sorted
    newFiles.sort()

    # If the targets moved during time lapse experiment
    diffPosNums = [0, ]
    diffPosFiles = [positionTsvPath, ]
    if diffPos != None:
        if len(diffPos) % 2 != 0:
            parser.error('The --diffPos argument requires both number and file')
        # PARSE args
        for imgfile, posFile in zip(diffPos[0::2], diffPos[1::2]):
            if imgfile not in oldFiles:
                raise ValueError(f'File {imgfile} missing from the original file names')
            diffPosNums.append(oldFiles.index(imgfile))
            diffPosFiles.append(posFile)

    # Determine extension (TODO remove this function. Because the files has been renamed,
    # correct names can be found in the pickled log file)
    useCroppedImg = False
    imgPath = os.path.join(path, 'original_images')
    if not os.path.isdir(imgPath):
        imgPath = os.path.join(path, 'cropped_ori')
        print(f'original_images folder not found, use cropped_ori folder for source images')
        assert os.path.isdir(imgPath), f'cropped_ori folder not found in {path}.'
        useCroppedImg = True
    extension = os.path.splitext(newFiles[0])[-1]
    if inputExt != '.auto' and extension != inputExt:
        ext = ''
        while ext not in [extension, inputExt]:
            ext = input(f'''{extension} determined from the input folder,
            it is different from default or input .{inputExt}, which one?
            "{extension}"/".{inputExt}":''')
        extension = ext

    if isTest:
        print(args)

    if not os.path.isdir(outputPath):
        os.mkdir(outputPath)

    # Generate file paths to process
    if useCroppedImg:
        newFiles = [os.path.splitext(f) for f in newFiles]
        newFiles = [f'{n[0]}_clean{n[1]}' for n in newFiles]
    fileList = [os.path.join(imgPath, f) for f in newFiles]

    for i, (num, positionTsvPath) in enumerate(zip(diffPosNums, diffPosFiles)):
        try:
            nextGroupStart = diffPosNums[i + 1]
        except IndexError:
            nextGroupStart = len(fileList)

        # Get position info out from posDict
        posDict = getPositions(diffPosFiles[0])
        paddingPos = posDict['removePadding']['paddingPos']  # Should equal to None when remove padding is not specified
        posToCrop = {}
        for posType in posDict:
            if posType in ['removePadding', 'Polygon_poly']:
                continue
            if len(posDict[posType]) == 0:
                continue
            for posName in posDict[posType]:
                position = posDict[posType][posName]
                if useCroppedImg and not locFromCropped: # change to new coordinate
                    position = [x[0]-x[1] for x in zip(position[:4], paddingPos[:2] * 2)]
                posToCrop[posName] = position

        # Create folder for each sample (posName)
        targetPaths = {}
        if i == 0:
            folders = [os.path.join('subImages', f) for f in list(posToCrop.keys())]

            # Add additional folder for cropped and resized pictures
            # Resized folder will store resized cropped images
            if paddingPos != None and not useCroppedImg:
                folders.append('cropped_ori')
            folders.append('resized')

            assert len(set(folders)) == len(folders), f'There are duplications in the sample IDs:\n{[i for i in folders if folders.count(i) > 1]}'

            if os.path.isdir(os.path.join(path, 'resized')):
                print('Clearing existing folders...')
                for p, _, _ in os.walk(path):
                    if p == path:
                        continue
                    dname = os.path.split(p)[-1]
                    if dname == 'original_images':
                        continue
                    if dname == 'cropped_ori' and useCroppedImg == True:
                        continue
                    shutil.rmtree(p)
            print('Creating folders...')
            targetPaths = createFolders(outputPath, folders, reset=True)

        # Prepare cropping files
        print(f'Cropping group {i+1}/{len(diffPosNums)}...')
        subFileList = fileList[diffPosNums[i]:nextGroupStart]
        # RUN. Submit cropping threads
        filePathList = [os.path.join(imgPath, file) for file in subFileList]
        threadPool = ThreadPoolExecutor(max_workers=os.cpu_count())
        futures = []
        for i, file in enumerate(filePathList):
            future = threadPool.submit(
                crop, file, posToCrop, targetPaths,
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
                    traceback.print_tb(exception.__traceback__)
                    print(exception.__class__, exception)
                    exit()
            futures.append(future)
            if isTest:
                print('Test run...')
                future.result()
                break
        print('All submitted! Waiting for finish.')
        exceptions = [future.exception() for future in futures]
        for i, exception in enumerate(exceptions):
            if exception != None:
                print(f'There is exception in run index {i}:')
                traceback.print_tb(exception.__traceback__)
                print(type(exception), exception)
                break
        threadPool.shutdown()
    print('Finished!')
