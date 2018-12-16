'''
Depends on Pillow (PIL Fork) https://pillow.readthedocs.io/en/latest/

Picture of each plate will be extracted from origional scanned picture.
Each position will be stored in separate dirs:
Note the initial resolution and the position will vary with different scanners
and plate setup.

!! Check Positions before you run this script!!!

TL = top left, TR = top right
ML = middle left, MR = middle right
BL = bottom left, BR = bottom right

All origional pictures will be compressed to smaller size and stored in 'resized'
directory.

This will be done with multithreading.
'''


import os
import platform
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

# If the script is located in the folder:
# path = os.path.dirname(os.path.realpath(__file__))
path = input('Please specify the directory:\n').strip()


def position(a, b, size):
    return a, b, a + size, b + size


def creatFolders(path):
    folders = ('TL', 'TR', 'ML', 'MR', 'BL', 'BR', 'resized')
    for folder in folders:
        if not os.path.isdir(os.path.join(path, folder)):
            os.mkdir(os.path.join(path, folder))


print('Creating folders')
creatFolders(path)

boxDict = {'TL': position(420, 350, 1040),
           'TR': position(1460, 350, 1040),
           'ML': position(90, 1390, 1040),
           'MR': position(1100, 1390, 1040),
           'BL': position(420, 2400, 1040),
           'BR': position(1460, 2400, 1040)}


fileList = sorted(list(file for file in os.listdir(path) if file.endswith('.jpg')))


def cropping(filePath):
    fileName = os.path.splitext(os.path.basename(filePath))[0]
    with Image.open(filePath) as im:
        for box in boxDict:
            outputPath = os.path.join(path, box)
            im.crop(boxDict[box]).save(os.path.join(outputPath, f'{fileName}_{box}.jpg'), 'jpeg',
                                       icc_profile=im.info.get('icc_profile'),
                                       progressive=True,
                                       quality=90,
                                       optimize=True)
        overAll = im.crop((90, 350, 2512, 3454))
        newSize = tuple(int(size * 0.35) for size in overAll.size)
        overAll.resize(newSize).save(os.path.join(path, 'resized', f'{fileName}_resized.jpg'), 'jpeg',
                                     icc_profile=im.info.get('icc_profile'),
                                     progressive=True,
                                     quality=90,
                                     optimize=True)
    return True


# crops = {}
threadPool = ThreadPoolExecutor(max_workers=8)
for i, file in enumerate(fileList):
    filePath = os.path.join(path, file)
    future = threadPool.submit(cropping, filePath)

threadPool.shutdown(wait=True)
print('Finished!')
