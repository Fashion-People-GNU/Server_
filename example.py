import sys
import subprocess
from clothes_detector import detector

opt = detector.parse_opt()
a = detector.main(opt)

print(a)
b = a.keys()
print(b)
for i in b:
    print(a.get(i))
