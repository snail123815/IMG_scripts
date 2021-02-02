import codecs  # for possible unicode character, not fully tested


def getInfo(sampleInfoTsvPath):
    '''sampleInfo[posName][info] = elements[i + 1]'''
    sampleInfo = {}
    with codecs.open(sampleInfoTsvPath, encoding='utf-8', mode='r') as posFile:
        infoStarted = False
        sampleInfoHeader = []
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


def getPositions(positionTsvPath):
    """Example position file:

    CornerSize     x      y      size           # upper left corner position
    TL             420    350    1040
    TR             1460   350    1040
    ML             90     1390   1040
    MR             1100   1390   1040
    BL             420    2400   1040
    BR             1460   2400   1040
    WidthHeight    x      y      Width  Height  # upper left and lower right positions
    removePadding  52     360    2448   3080    # include this line if you need to remove certain padding
    TwoPositions   x1     y1     x2     y2
    end                                         # parse will stop here



    Args:
        positionTsvPath ([type]): [description]

    Returns:
        posDict: x1, y1, x2, y2 (designed for PIL.image.crop)
    """    
    positionTypes = ['CornerSize', 'WidthHeight', 'CenterSize', 'TwoPositions', 'removePadding']
    posDict = {}
    locType = ''
    with open(positionTsvPath, 'r') as posFile:
        for line in posFile.readlines():
            if line.startswith('#') or len(line) == 0:
                continue
            elements = [e.strip() for e in line.split('\t')]
            if elements[0] == 'END':
                break
            elements = [e for e in elements if e != '' and not e.startswith('#')]
            if len(elements) == 0:
                continue
            if elements[0] in positionTypes:
                # Type string found, initialise
                pLocType = locType
                locType = elements[0]
                posDict[locType] = {}
                # remove padding deal here, only allowing 'WidthHeight' and 'TwoPositions
                if locType == 'removePadding':
                    position = [int(elem) for elem in elements[1:]]
                    if pLocType == 'WidthHeight':
                        position = position[:2] + [sum(x) for x in zip(position[2:],position[:2])]
                    posDict['removePadding']['paddingPos'] = position[:4]
                continue
            # NOW start parsing positions
            if locType == '':
                raise ValueError(f'Error, no type string found, check file.\nAcceptable: {", ".join(positionTypes)}')
            posName = elements[0]
            position = [int(elem) for elem in elements[1:]]
            if locType == 'CornerSize':
                size = position[2]
                position = position[:2] + [x + size for x in position[:2]]
            if locType == 'CenterSize':
                r = int(position[2] / 2)
                position = [x - r for x in position[:2]] + [x + r for x in position[:2]]
            if locType == 'WidthHeight':
                position = position[:2] + [sum(x) for x in zip(position[2:],position[2:4])]
            if locType == 'TwoPositions':
                position = position[:4]
            #position = tuple(position)
            posDict[locType][posName] = position
    # Put None for removePadding if not found in the file
    if 'removePadding' not in posDict:
        posDict['removePadding']['paddingPos'] = None
    return posDict
# getPositions
