from PIL import Image

def bitstream(data, n):
    bits = "0100" + f"{len(data.encode('utf-8')):08b}" #byte mode in level L (od wersji 10 musi być :16b)
    bits += "".join(f"{byte:08b}" for byte in data.encode('utf-8')) + "0000" #konwertujemy dane do 8 bitowych codeków, od wersji 10 CHYBA muszą być 16 bitowe...
    for _ in range((8 - (len(bits) % 8)) % 8): #uzupełniamy do pełnego bajtu
        bits += "0"

    a = True
    for i in range(n+2 - len(bits)//8): #uzupełnić do n bajtów
        if a:
            bits += "11101100" #0xEC
        else:
            bits += "00010001" #0x11
        a = not a
    return bits

def gf(data, n, bytes): #dodać, żeby dzielił to jakoś na grupy, jak w bytes
    def gf_mul(a, b):
        if a == 0 or b == 0:
            return 0
        return alog[log[a] + log[b]]

    log = [0] * 256
    alog = [0] * 512

    x = 1
    for i in range(255):
        alog[i] = x
        log[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11d
    for i in range(255, 512):
        alog[i] = alog[i - 255]

    g = [1]
    for i in range(n):
        gen = [gf_mul(c, 1) for c in g] + [0]
        for j in range(len(g)):
            gen[j + 1] = gen[j + 1] ^ gf_mul(g[j], alog[i])
        g = gen[:]

    msg = data + [0] * n
    for i in range(len(data)):
        coef = msg[i]
        if coef != 0:
            for j in range(1, n+1):
                msg[i + j] = msg[i + j] ^ gf_mul(g[j], coef)

    return msg[-n:]

def ECC(data, n, g, bytes):
    bits = bitstream(data, n)

    b = [int(bits[i:i+8], 2) for i in range(0, len(bits), 8)]

    ecc = "".join(f"{byte:08b}" for byte in b + gf(b, g, bytes))

    return ecc

def put_finders(qr, size, n):
    pat = [
        "1111111",
        "1000001",
        "1011101",
        "1011101",
        "1011101",
        "1000001",
        "1111111",
    ]
    for dy in range(7):
        for dx in range(7):
            qr[dy][dx] = pat[dy][dx]
            qr[size-7 + dy][dx] = pat[dy][dx]
            qr[dy][size-7 + dx] = pat[dy][dx]

    for i in range(8):
        qr[7][i] = "0"
        qr[i][7] = "0"
    for i in range(8):
        qr[7][size-8 + i] = "0"
        qr[i][size-8] = "0"
    for i in range(8):
        qr[size-8][i] = "0"
        qr[size-8 + i][7] = "0"

    pat2 = [
        "11111",
        "10001",
        "10101",
        "10001",
        "11111",
    ]

    loc = [
        [],
        [6],
        [6, 18],
        [6, 22],
        [6, 26],
        [6, 30],
        [6, 34],
        [6, 22, 38],
        [6, 24, 42],
        [6, 26, 46],
        [6, 28, 50],
        [6, 30, 54],
        [6, 32, 58],
        [6, 34, 62]
    ]

    l = len(loc[n])
    for i in range(l):
        for j in range(l):
            if not((i==0 and j==0) or (i==0 and j==l-1) or (i==l-1 and j==0)):
                for dx in range(5):
                    for dy in range(5):
                        qr[dy + loc[n][j] - 2][dx + loc[n][i] - 2] = pat2[dy][dx]

def put_timing(qr, size):
    for i in range(8, size - 8):
        a = "1" if i % 2 == 0 else "0"
        qr[i][6] = a
        qr[6][i] = a

def put_format(qr, size):
    fmt = 0b111011111000100
    bits = [str((fmt >> (14 - i)) & 1) for i in range(15)]

    for i in range(6):
        qr[8][i] = bits[i]

    qr[8][7] = bits[6]
    qr[8][8] = bits[7]
    qr[7][8] = bits[8]

    for i in range(6):
        qr[5 - i][8] = bits[9 + i]

    for i in range(7):
        qr[size-1 - i][8] = bits[i]
    qr[size - 8][8] = "1"

    for i in range(8):
        qr[8][size - 8 + i] = bits[7 + i]

def fill(qr, size, data):
    i = 0
    x = y = size-1
    direction = -1
    err = 0

    while x > 0:
        if x == 6:
            x -= 1
        while True:
            for dx in (0, -1):
                xx = x + dx

                if qr[y][xx] == "-":
                    if i >= len(data):
                        qr[y][xx] = "0"
                        err += 1
                    else:
                        if (y + xx) % 2 == 0:
                            qr[y][xx] = "1" if data[i] == "0" else "0"
                        else:
                            qr[y][xx] = data[i]
                        i += 1
            y += direction
            if y < 0 or y >= size:
                y -= direction
                direction *= -1
                break
        x -= 2
    assert i == len(data)
    if err > 0:
        print(f"{err} bitów puste")

def QR(data):
    lengths = [17, 32, 53, 78, 106, 134, 154, 192, 230, 271]
    sizes = [21 + i*4 for i in range(10)]
    errs = [7, 10, 15, 20, 26, [18, 18]]
    bytes = [19, 34, 55, 80, 108, [68, 68]]
    isDone = False

    size=n=0
    ecc=""
    for i in range(5):
        if len(data) <= lengths[i]:
            n = i+1
            size = sizes[i]
            ecc = ECC(data, lengths[i], errs[i], bytes[i])
            isDone = True
            break

    if not isDone:
        print("zbyt długi napis")
        return ["0"]

    print(ecc)
    qr = [["-" for _ in range(size)] for _ in range(size)]

    put_finders(qr, size, n)
    put_timing(qr, size)
    put_format(qr, size)

    # slots = sum(1 for r in qr for c in r if c == "-")

    # for i in qr:
    #     for j in i:
    #         print(j, end="")
    #     print()

    fill(qr, size, ecc)
    return qr

def png(qr, outfile="qr.png", scale=10):
    size = len(qr)
    img = Image.new("L", (size, size), 255)  # 255 = białe
    px = img.load()

    for y in range(size):
        for x in range(size):
            px[x, y] = 0 if qr[y][x] == "1" else 255

    img = img.resize((size * scale, size * scale), Image.Resampling.NEAREST)
    img.save(outfile)

if __name__ == '__main__':
    #data = "".join(" " if i % 10 == 9 else "a" for i in range(106))
    data = input("podaj ciąg do zmiany na qr: ")
    png(QR(data))