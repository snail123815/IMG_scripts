import os
import platform
from PIL import Image
# from threading import Thread
from concurrent.futures import ThreadPoolExecutor


def positionCenter(a, b, size):
    return a - size, b - size, a + size, b + size


def creatSubPlateFolders(path, plate, totalSubPos, subName='colony'):
    sourcePath = os.path.join(path, plate)
    subFolders = [f'{subName}_{i}' for i in range(totalSubPos)]
    listTargetPath = []
    for subFolder in subFolders:
        targetPath = os.path.join(sourcePath, subFolder)
        if not os.path.isdir(targetPath):
            os.mkdir(targetPath)
        listTargetPath.append(targetPath)
    return listTargetPath


def cropOneSource(sourceImagePath, listTargetPath, subCentPosPlate):
    with Image.open(sourceImagePath) as im:
        for targetPath, subCenterPos in zip(listTargetPath, subCentPosPlate):
            sourceImage = os.path.splitext(os.path.split(sourceImagePath)[1])[0]
            targetImage = os.path.split(targetPath)[1]
            if targetImage == '':
                targetImage = os.path.split(os.path.split(targetPath)[0])[1]
            targetImage = f'{sourceImage}_{targetImage}.jpg'
            targetImagePath = os.path.join(targetPath, targetImage)
            positions = positionCenter(*subCenterPos, 20)
            im.crop(positions).save(targetImagePath, 'jpeg',
                                    icc_profile=im.info.get('icc_profile'),
                                    progressive=True,
                                    quality=90,
                                    optimize=True)


def cropSubPlate(path, plate, subCentPosPlate):
    listTargetPath = creatSubPlateFolders(path, plate, len(subCentPosPlate))
    sourcePath = os.path.join(path, plate)
    listSourceImage = [file for file in os.listdir(sourcePath) if file.endswith('.jpg')]
    threadPool = ThreadPoolExecutor(max_workers=10)
    for sourceImage in listSourceImage:
        sourceImagePath = os.path.join(path, plate, sourceImage)
        threadPool.submit(cropOneSource,
                          sourceImagePath, listTargetPath, subCentPosPlate)
    threadPool.shutdown(wait=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='pass a directory as first argument')
    parser.add_argument('path', description='Full path of target dir')
    args = parser.parse_args()
    path = args.path

    # needs to change - read from imageJ output
    # subCentPosPlates = {
    #     # plate: [[x,y], [x,y], [x,y]]
    #     # positionCenter(*positions, size)
    #     'TL': [
    #         [360, 328], [545, 361], [742, 388],
    #         [331, 508], [539, 537], [735, 565],
    #         [307, 708], [508, 733], [716, 755]
    #     ],
    #     'TR': [
    #         [278, 343], [482, 329], [669, 299],
    #         [307, 541], [509, 509], [706, 489],
    #         [344, 745], [552, 710], [747, 676]
    #     ]
    # }

    for plate in subCentPosPlates:
        cropSubPlate(path, plate, subCentPosPlates[plate])

    print('Finished!')
