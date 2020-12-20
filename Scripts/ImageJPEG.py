#!/usr/bin/python3
import os
import struct

def strbytes(b):
    r = ""
    for i in b:
        s = hex(i)[2:]
        s = s if (len(s)-1) else "0" + s
        r += "\\x" + s
    return r

class ReadFile():
    def __init__(self, filename):
        self.filename = filename
        self.buffers = [
            b"",
            b"",
            b""
        ]
        self.buffersize = 512
        self.curentblock = -3
        with open(filename, "rb") as fin:
            fin.seek(0, os.SEEK_END)
            self.size = fin.tell()
        self.lastblock = self.size // self.buffersize

    def loadBlock(self, nb):
        if self.curentblock != nb:
            for i in range(3):
                if -1 <= nb + i - 1 - self.curentblock <= 1:
                    self.buffers[i] = self.buffers[nb + i - self.curentblock]
                else:
                    temp = min(max(0, nb + i - 1), self.lastblock)
                    with open(self.filename, "rb") as fin:
                        fin.seek(temp * self.buffersize, os.SEEK_SET)
                        self.buffers[i] = fin.read(self.buffersize)
        self.curentblock = nb

    def getBytes(self, start, length):
        start = max(start, 0)
        end = min(self.size, start + length)
        block = start // self.buffersize
        endblock = end // self.buffersize
        end -= self.buffersize * endblock
        start -= self.buffersize * block
        self.loadBlock(block)
        if block == endblock:
            r = self.buffers[1][start:end]
        else:
            r = self.buffers[1][start:]
            block += 1
            while block != endblock:
                self.loadBlock(block)
                r += self.buffers[1]
                block += 1
            r += self.buffers[2][:end]
        return r


class JPEG():
    ZIGZAG = [
        [ 0,  1,  5,  6, 14, 15, 27, 28],
        [ 2,  4,  7, 13, 16, 26, 29, 42],
        [ 3,  8, 12, 17, 25, 30, 41, 43],
        [ 9, 11, 18, 24, 31, 40, 44, 53],
        [10, 19, 23, 32, 39, 45, 52, 54],
        [20, 22, 33, 38, 46, 51, 55, 60],
        [21, 34, 37, 47, 50, 56, 59, 61],
        [35, 36, 48, 49, 57, 58, 62, 63]
    ]

    MARKERS = {
        b"\xFF\xD8": lambda x: x.markerSOI(),
        b"\xFF\xD9": lambda x: x.markerEOI(),
        b"\xFF\xC4": lambda x: x.markerDHT(),
        b"\xFF\xDB": lambda x: x.markerDQT(),
        b"\xFF\xDA": lambda x: x.markerSOS(),
        b"\xFF\xC0": lambda x: x.markerSOF()
    }

    SKIPMARKERS = [
        b"\x00",
        b"\xD0",
        b"\xD1",
        b"\xD2",
        b"\xD3",
        b"\xD4",
        b"\xD5",
        b"\xD6",
        b"\xD7"
    ]

    COMPONENTSID = {
        1: "Y",
        2: "Cb",
        3: "Cr",
        4: "I",
        5: "Q"
    }

    def __init__(self, filename):
        self.filename = filename
        self.file = ReadFile(self.filename)
        self.start = False
        self.end = False
        self.cursor = 0
        self.huffmantables = {}
        self.qttable = {}
        self.decode()

    @staticmethod
    def zigzag(table):
        vector = [0 for i in range(64)]
        for i in range(8):
            for j in range(8):
                vector[JPEG.ZIGZAG[i][j]] = table[i][j]
        return vector

    @staticmethod
    def rezigzag(vector):
        table = [[0 for j in range(8)] for i in range(8)]
        for i in range(8):
            for j in range(8):
                table[i][j] = vector[JPEG.ZIGZAG[i][j]]
        return table

    def decode(self):
        self.cursor = 0
        self.savecursor = self.cursor
        marker = self.file.getBytes(self.cursor, 2)
        if marker in JPEG.MARKERS:
            JPEG.MARKERS[marker](self)
        if not self.start:
            raise ValueError("Marker \"Start of Image\" not found!")
        while not self.end:
            marker = self.file.getBytes(self.cursor, 2)
            if marker in JPEG.MARKERS:
                JPEG.MARKERS[marker](self)
            elif marker[:1] == b"\xFF":
                self.ignoreMarker()
            else:
                self.findNextMarker()

    def markerSOI(self):
        print("Marker \"Start of Image\" found! on {}".format(hex(self.cursor)))
        self.start = True
        self.cursor += 2
    
    def markerEOI(self):
        print("Marker \"End of Image\" found! on {}".format(hex(self.cursor)))
        self.end = True
        self.cursor += 2

    def ignoreMarker(self):
        print("Marker ({}) found! on {}".format(strbytes(self.file.getBytes(self.cursor, 2)), hex(self.cursor)))
        self.cursor += 2
        self.savecursor = self.cursor
        length = struct.unpack(">H", self.file.getBytes(self.cursor, 2))[0]
        print("\tLength: {}".format(length))
        self.cursor += length

    def findNextMarker(self):
        self.cursor = self.savecursor
        while (self.file.getBytes(self.cursor, 1) != b'\xFF') or (self.file.getBytes(self.cursor + 1, 1) in JPEG.SKIPMARKERS):
            self.cursor += 1

    def markerDHT(self):
        print("Marker \"Define Huffman Table\" found! on {}".format(hex(self.cursor)))
        self.cursor += 2
        length = struct.unpack(">H", self.file.getBytes(self.cursor, 2))[0]
        endcursor = self.cursor + length
        self.cursor += 2
        while self.cursor != endcursor:
            inform = self.file.getBytes(self.cursor, 1)[0]
            inform = ( inform & 0x0F,"AC" if (0x10 & inform) else "DC")
            print("\tNum: {} Type: {}".format(*inform))
            self.cursor += 1
            amount = struct.unpack("B" * 16, self.file.getBytes(self.cursor, 16))
            print("\tAmount: {}".format(amount))
            self.cursor += 16
            table = [0 for i in range(65536)]
            code = 0
            step = 65536>>1
            i = 0
            p = 0
            while i < len(amount):
                if amount[i] != p:
                    table[code] = (self.file.getBytes(self.cursor, 1)[0], i + 1)
                    cd = code
                    code += step
                    if table[cd]:
                        for j in range(cd+1, code):
                            table[j] = table[cd]
                    self.cursor += 1
                    p += 1
                else:
                    i += 1
                    step >>= 1
                    p = 0
            self.huffmantables[inform] = table

    def markerDQT(self):
        print("Marker \"Define Quantization Table\" found! on {}".format(hex(self.cursor)))
        self.cursor += 2
        length = struct.unpack(">H", self.file.getBytes(self.cursor, 2))[0]
        endcursor = self.cursor + length
        self.cursor += 2
        while self.cursor != endcursor:
            inform = self.file.getBytes(self.cursor, 1)[0]
            inform = ( inform & 0x0F, 2 if (0xF0 & inform) else 1)
            tp = ">H" if inform[1] == 2 else "B"
            print("\tNum: {} Precision: {} bytes".format(*inform))
            self.cursor += 1
            dqt = []
            for i in range(64):
                dqt.append(struct.unpack(tp, self.file.getBytes(self.cursor, inform[1]))[0])
                self.cursor += inform[1]
            self.qttable[inform[0]] = dqt
            print("\tTable: ")
            dqt = JPEG.rezigzag(dqt)
            for i in dqt:
                for j in i:
                    print(j, '\t', end="")
                print()

    def markerSOF(self):
        print("Marker \"Start of Frame\" found! on {}".format(hex(self.cursor)))
        self.cursor += 2
        length = struct.unpack(">H", self.file.getBytes(self.cursor, 2))[0]
        self.cursor += 2
        prec = self.file.getBytes(self.cursor, 1)[0]
        self.cursor += 1
        print("\tPrecision: {}".format(prec))
        self.height = struct.unpack(">H", self.file.getBytes(self.cursor, 2))[0]
        self.cursor += 2
        self.width = struct.unpack(">H", self.file.getBytes(self.cursor, 2))[0]
        self.cursor += 2
        print("\tSize: {}h x {}w".format(self.height, self.width))
        self.numofcomp = self.file.getBytes(self.cursor, 1)[0]
        self.cursor += 1
        print("\tNumber of Components: {}".format(self.numofcomp))
        self.qtnumber = {}
        for i in range(self.numofcomp):
            compid = self.file.getBytes(self.cursor, 1)[0]
            self.cursor += 1
            sample = self.file.getBytes(self.cursor, 1)[0]
            sample = ((sample & 0xF0) >> 4, (sample & 0x0F))
            self.cursor += 1
            tablenum = self.file.getBytes(self.cursor, 1)[0]
            self.qtnumber[JPEG.COMPONENTSID[compid]] = tablenum
            print("\tComponent: \"{}\"\n\tQTTable: {}\n\tSample: {}".format(JPEG.COMPONENTSID[compid], tablenum, sample))
            self.cursor += 1

    def markerSOS(self):
        print("Marker \"Start of Scan\" found! on {}".format(hex(self.cursor)))
        self.cursor += 2
        self.savecursor = self.cursor
        length = struct.unpack(">H", self.file.getBytes(self.cursor, 2))[0]
        self.cursor += 2
        compnum = struct.unpack("B", self.file.getBytes(self.cursor, 1))[0]
        print("\tNumber of components: {}".format(compnum))
        self.cursor += 1
        self.components = []
        for i in range(compnum):
            compid = self.file.getBytes(self.cursor, 1)[0]
            inform = self.file.getBytes(self.cursor + 1, 1)[0]
            acdc = (JPEG.COMPONENTSID[compid], inform & 0x0F, (0xF0 & inform) >> 4)
            print("\tComponent: \"{}\"\n\tAC Table: {}\n\tDC Table: {}".format(*acdc))
            self.components.append(acdc)
            self.cursor += 2
        print(strbytes(self.file.getBytes(self.cursor, 3)))
        self.cursor += 3
        self.deHuffman()

    def deHuffman(self):
        DC = [0 for i in range(len(self.components))]

def main():
    JPEG("test1.jpg")

if __name__ == "__main__":
    main()