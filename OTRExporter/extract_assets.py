#!/usr/bin/env python3
import argparse
import os
import signal
import sys
import shutil
import subprocess
import pathlib
from multiprocessing import Pool, Event


def SignalHandler(sig, frame):
    print(f'Signal {sig} received. Aborting...')
    mainAbort.set()
    # Don't exit immediately to update the extracted assets file.


def BuildOTR():
    shutil.copyfile("../soh/baserom/Audiobank", "Extract/Audiobank")
    shutil.copyfile("../soh/baserom/Audioseq", "Extract/Audioseq")
    shutil.copyfile("../soh/baserom/Audiotable", "Extract/Audiotable")

    shutil.copytree("assets", "Extract/assets")

    prog = pathlib.Path("x64\\Release\\ZAPD.exe" if sys.platform == "win32" else "../ZAPDTR/ZAPD.out").resolve()
    assert prog.exists()
    args = "botr -se OTR"
    execStr = "{} {}".format(prog, args)

    try:
        import ubelt as ub
        ub.cmd(execStr, shell=True, check=True, verbose=3)
        # subprocess.check_output(execStr, shell=True)
    except subprocess.CalledProcessError as ex:
        print(ex.stdout, os.sys.stdout)
        print(ex.stderr, os.sys.stderr)
        print("\n")
        print("Error when building the OTR file...", file=os.sys.stderr)
        print("Aborting...", file=os.sys.stderr)
        print("\n")
        raise


def ExtractFile(xmlPath, outputPath, outputSourcePath):
    xmlPath = pathlib.Path(os.path.normpath(pathlib.Path(xmlPath).absolute()))
    outputPath = pathlib.Path(os.path.normpath(pathlib.Path(outputPath).absolute()))
    outputSourcePath = pathlib.Path(os.path.normpath(pathlib.Path(outputSourcePath).absolute()))

    prog = pathlib.Path("x64\\Release\\ZAPD.exe" if sys.platform == "win32" else "../ZAPDTR/ZAPD.out").resolve()
    baseromPath = pathlib.Path(os.path.normpath(pathlib.Path('../soh/baserom/').resolve()))
    configXML = pathlib.Path('CFG/Config.xml').resolve()

    assert prog.exists()
    assert xmlPath.exists()
    assert baseromPath.exists()
    assert configXML.exists()

    assert outputPath.exists()
    assert outputSourcePath.exists()
    args = f"e -eh -i {xmlPath} -b {baseromPath} -o {outputPath} -osf {outputSourcePath} -gsf 1 -rconf {configXML} -se OTR"

    if "overlays" in str(xmlPath):
        args += " --static"

    execStr = "{} {}".format(prog, args)

    try:
        import ubelt as ub
        ub.cmd(execStr, shell=True, check=True, verbose=3)
        # subprocess.check_output(execStr, shell=True)
    except subprocess.CalledProcessError as ex:
        print(ex.stdout, os.sys.stdout)
        print(ex.stderr, os.sys.stderr)
        print("\n")
        print(f"Error when extracting from file {xmlPath}", file=os.sys.stderr)
        print("Aborting...", file=os.sys.stderr)
        print("\n")
        raise


def ExtractFunc(fullPath):
    *pathList, xmlName = fullPath.split(os.sep)
    objectName = os.path.splitext(xmlName)[0]

    outPath = os.path.join("../soh/assets/", *pathList[5:], objectName)
    os.makedirs(outPath, exist_ok=True)
    outSourcePath = outPath

    ExtractFile(fullPath, outPath, outSourcePath)


def initializeWorker(abort, test):
    global globalAbort
    globalAbort = abort


def main():
    parser = argparse.ArgumentParser(description="baserom asset extractor")
    parser.add_argument("-s", "--single", help="asset path relative to assets/, e.g. objects/gameplay_keep")
    parser.add_argument("-f", "--force", help="Force the extraction of every xml instead of checking the touched ones.", action="store_true")
    parser.add_argument("-u", "--unaccounted", help="Enables ZAPD unaccounted detector warning system.", action="store_true")
    parser.add_argument("-v", "--version", help="Sets game version.")
    args = parser.parse_args()

    global mainAbort
    mainAbort = Event()
    signal.signal(signal.SIGINT, SignalHandler)

    xmlVer = "GC_NMQ_D"

    if (args.version == "gc_pal_nmpq"):
        xmlVer = "GC_NMQ_PAL_F"
    elif (args.version == "dbg_mq"):
        xmlVer = "GC_MQ_D"

    asset_path = args.single
    if asset_path is not None:
        fullPath = os.path.join("../soh/assets", "xml", asset_path + ".xml")
        if not os.path.exists(fullPath):
            raise IOError(f"Error. File {fullPath} doesn't exists.")

        ExtractFunc(fullPath)
    else:
        extract_text_path = "assets/text/message_data.h"
        if os.path.isfile(extract_text_path):
            extract_text_path = None
        extract_staff_text_path = "assets/text/message_data_staff.h"
        if os.path.isfile(extract_staff_text_path):
            extract_staff_text_path = None

        xmlFiles = []
        for currentPath, _, files in os.walk(os.path.join("../soh/assets/xml/", xmlVer)):
            for file in files:
                fullPath = os.path.join(currentPath, file)
                if file.endswith(".xml"):
                    xmlFiles.append(fullPath)

        numCores = 0
        try:
            if numCores == 0:
                raise Exception
            print("Extracting assets with " + str(numCores) + " CPU cores.")
            with Pool(numCores, initializer=initializeWorker, initargs=(mainAbort, 0)) as p:
                p.map(ExtractFunc, xmlFiles)
        except Exception:
            print("Warning: Multiprocessing exception ocurred.", file=os.sys.stderr)
            print("Disabling mutliprocessing.", file=os.sys.stderr)

            initializeWorker(mainAbort, 0)
            for singlePath in xmlFiles:
                ExtractFunc(singlePath)

        BuildOTR()
        shutil.rmtree("Extract")

if __name__ == "__main__":
    main()
