# -*- coding: utf-8 -*-
import sys
from MainClass import MainClass


if __name__ == "__main__":
    if len(sys.argv) == 2:
        mc = MainClass(sys.argv[1])
        mc.debug()
        mc.processAllGroups()

    else:
        exit(1)
