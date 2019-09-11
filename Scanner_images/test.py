from measure_gray_plate import measureCenterCircle
import os
testDir = '/Users/durand.dc/Documents/works/Local_files/20190708_sco1839_cropped/p2/'
filePathes = [os.path.join(testDir, file) for file in os.listdir(testDir)][:30]


results = measureCenterCircle(filePathes, 0.7)
print(results)
