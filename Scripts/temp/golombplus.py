#!/usr/bin/python3

import sys
import argparse

def zigzag(matrix, step=False):
    x = 0
    y = 0
    vector = []
    while((x != 7) or (y != 7)):
        vector.append(matrix[y][x])
        if step:
            x -= 1
            y += 1
            if (y == 8):
                y -= 1
                x += 2
                step = not step
            elif (x == -1):
                x += 1
                step = not step
        else:
            x += 1
            y -= 1
            if (x == 8):
                x -= 1
                y += 2
                step = not step
            elif (y == -1):
                y += 1
                step = not step
    vector.append(matrix[y][x])
    for i in range(len(vector)-1, -1, -1):
        if vector[i]:
            break
    vector = vector[:i+1]
    return vector

def antizigzag(vector, step=False):
    matrix = [[0 for i in range(8)] for j in range(8)]
    x = 0
    y = 0
    for i in vector:
        matrix[y][x] = i
        if step:
            x -= 1
            y += 1
            if (y == 8):
                y -= 1
                x += 2
                step = not step
            elif (x == -1):
                x += 1
                step = not step
        else:
            x += 1
            y -= 1
            if (x == 8):
                x -= 1
                y += 2
                step = not step
            elif (y == -1):
                y += 1
                step = not step
    return matrix

def golombplus(num):
    if not num:
        return '0'
    minus = '0' if (num < 0) else '1'
    num = abs(num) + 1
    num = bin(num)[2:]
    return '1' * (len(num)-1) + '0' + minus + num[1:]

def encode():
    matrix = [list(map(int, input().split())) for i in range(8)]
    vector = zigzag(matrix)
    length = bin(len(vector)-1)[2:]
    length = (6-len(length)) * '0' + length
    s = [length]
    for i in vector:
        s.append(golombplus(i))
    ss = ''.join(s)
    print(ss)

def antigolombplus(size, s):
    vector = []
    while (size):
        if s[0] == '0':
            vector.append(0)
            s = s[1:]
        else:
            i = 0
            while (s[i] != '0'):
                i += 1
            minus = -1 if (s[i+1] == '0') else 1
            num = int('1'+s[i+2:i+i+2], base=2) - 1
            num *= minus
            vector.append(num)
            s = s[i+i+2:]
        size -= 1
    return vector

def decode():
    s = input()
    length = int(s[:6], base = 2) + 1
    vector = antigolombplus(length, s[6:])
    matrix = antizigzag(vector)
    for i in matrix:
        for j in i:
            print(j, end=' ')
        print()



def main():
    if 'e' in sys.argv:
        encode()
    if 'd' in sys.argv:
        decode()

if __name__ == "__main__":
    main()