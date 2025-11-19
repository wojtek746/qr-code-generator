from PIL import Image

def bitstream(data, n):
    bits = "0100" + f"{len(data):08b}" #byte mode in level L (od wersji 10 musi być :16b)
    bits += "".join(f"{byte:08b}" for byte in data.encode('utf-8')) + "0000" #konwertujemy dane do 8 bitowych codeków, od wersji 10 CHYBA muszą być 16 bitowe...
    for _ in range((8 - (len(bits) % 8)) % 8): #uzupełniamy do pełnego bajtu
        bits += "0"

    a = True
    for i in range(n - len(bits)//8): #uzupełnić do n bajtów
        if a:
            bits += "11101100" #0xEC
        else:
            bits += "00010001" #0x11
        a = not a
    return bits

def ECC(data, n): #zakładam, że n = 19
    alog = [1]
    for i in range(1, 256):
        x = alog[-1] << 1
        if x & 0x100:
            x ^= 0x11D
        alog.append(x)

    log = [0] * 256
    for i in range(255):
        log[alog[i]] = i

    def gf_mul(a, b):
        if a == 0 or b == 0:
            return 0
        return alog[(log[a] + log[b]) % 255]

    def gf_poly_div(data, gen):
        buf = data[:]
        for i in range(len(data) - len(gen) + 1):
            coef = buf[i]
            if coef != 0:
                for j in range(1, len(gen)):
                    buf[i + j] ^= gf_mul(gen[j], coef)
        return buf[-(len(gen) - 1):]

    gen = [1, 87, 229, 146, 149, 238, 102, 21]

    bits = bitstream(data, n)
    b = [int(bits[i:i+8], 2) for i in range(0, len(bits), 8)]

    gf = gf_poly_div(b, gen)
    ecc = "".join(f"{byte:08b}" for byte in b + gf)

    return ecc

def QR(data):
    def put_finder(x, y):
        if n == 1:
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
                    qr[y + dy][x + dx] = pat[dy][dx]

            if x==y==0:
                for i in range(8):
                    qr[y + 7][x + i] = "0"
                    qr[y + i][x + 7] = "0"
            elif x>0:
                for i in range(8):
                    qr[y + 7][x + i - 1] = "0"
                    qr[y + i][x - 1] = "0"
            elif y>0:
                for i in range(8):
                    qr[y - 1][x + i] = "0"
                    qr[y + i - 1][x + 7] = "0"

    def put_timing():
        for i in range(8, 21 - 8):
            a = "1" if i % 2 == 0 else "0"
            qr[i][6] = a
            qr[6][i] = a

    def put_format(len):
        fmt = 0b001011010001001
        bits = [str((fmt >> (14 - i)) & 1) for i in range(15)]

        for i in range(6):
            qr[8][i] = bits[i]

        qr[8][7] = bits[6]
        qr[8][8] = bits[7]
        qr[7][8] = bits[8]

        for i in range(6):
            qr[5 - i][8] = bits[9 + i]

        for i in range(7):
            qr[len - i][8] = bits[i]
        qr[len - 7][8] = "1"

        for i in range(8):
            qr[8][len - 7 + i] = bits[7 + i]

    def fill():
        nonlocal a
        nonlocal b
        i = 0
        max = 0
        if n == 1:
            max = 20
        x = y = max
        direction = -1

        while x > 0:
            if x == 6:
                x -= 1
            while True:
                for dx in (0, -1):
                    xx = x + dx

                    if qr[y][xx] == "-":
                        if i >= len(ecc):
                            print("error, za małe ecc")
                            qr[y][xx] = "0"
                        else:
                            if (y + xx) % 2 == 0:
                                qr[y][xx] = "1" if ecc[i] == "0" else "0"
                            else:
                                qr[y][xx] = ecc[i]
                            i += 1
                y += direction
                if y < 0 or y > max:
                    y -= direction
                    direction *= -1
                    break
            x -= 2

    if len(data) <= 17:
        a = b = 0
        n = 1
        ecc = ECC(data, 19)
        print(ecc)
        qr = [["-" for _ in range(21)] for _ in range(21)]

        put_finder(0, 0)
        put_finder(0, 14)
        put_finder(14, 0)
        put_timing()
        put_format(20)
        slots = sum(1 for r in qr for c in r if c == "-")
        assert slots == 208, slots
        fill()
        # for i in qr:
        #     for j in i:
        #         print(j, end="")
        #     print()
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
    data = input("podaj ciąg do zmiany na qr: ")
    png(QR(data))