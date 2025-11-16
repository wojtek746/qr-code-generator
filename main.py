from PIL import Image

def bitstream(data, n):
    bits = "0100" + "".join(f"{byte:08b}" for byte in data.encode('utf-8')) + "0000" #zamienić na bity z 0100 na początku i 0000 na końcu
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
        if n <= 19:
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

    def put_timing():
        for i in range(8, 21 - 8):
            a = "1" if i % 2 == 0 else "0"
            qr[i][6] = a
            qr[6][i] = a

    def put_format():
        fmt = 0b111011111000100
        bits = [str((fmt >> (14 - i)) & 1) for i in range(15)]

        qr[8][7] = bits[6]
        qr[8][8] = bits[7]
        qr[7][8] = bits[8]

        for i in range(6):
            qr[8][i] = bits[i]
        for i in range(6):
            qr[i][8] = bits[9 + i]
        for i in range(8):
            qr[20 - i][8] = bits[i]
        for i in range(7):
            qr[8][20 - i] = bits[7 + i]

    def fill():
        i = 0
        x = y = 20
        direction = -1

        while x > 0:
            if x == 6:
                x -= 1
            for _ in range(21):
                for dx in (0, -1):
                    xx = x + dx
                    yy = y

                    if qr[yy][xx] == "-":
                        if i >= len(ecc):
                            qr[yy][xx] = "0" #ostatecznie ma być 0
                        else:
                            if (yy + xx) % 2 == 0:
                                qr[yy][xx] = "1" if ecc[i] == "0" else "0"
                            else:
                                qr[yy][xx] = ecc[i]
                        i += 1
                y += direction
                if y < 0 or y > 20:
                    y -= direction
                    direction *= -1
                    break
            x -= 2

    if len(data) < 19:
        n = 19
        ecc = ECC(data, n)
        qr = [["-" for _ in range(21)] for _ in range(21)]

        put_finder(0, 0)
        put_finder(0, 14)
        put_finder(14, 0)
        put_timing()
        put_format()
        fill()
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