import hashlib


b = 256
q = 2 ** 255 - 19
l = 2 ** 252 + 27742317777372353535851937790883648493


def H(m):
    return hashlib.sha512(m).digest()


def pow2(x, p):
    """== pow(x, 2**p, q)"""
    while p > 0:
        x = x * x % q
        p -= 1
    return x

def powcyclo(x, p, k):
    """== pow(x, 1 + 2**p + ... + 2**((k-1)*p), q)"""
    c = x
    while k > 1:
        c = x * pow2(c, p) % q
        k -= 1
    return c

def inv(x):
    """$= x^{-1} \mod q$, for x != 0"""
    # q-2 == 32*(2**250 - 1) + 11
    i = pow(x, 32*31, q)         # == x**(32 * (2**5 - 1))
    i = powcyclo(i, 5, 5)        # == x**(32 * (2**25 - 1))
    i = powcyclo(i, 25, 5)       # == x**(32 * (2**125 - 1))
    i = powcyclo(i, 125, 2)      # == x**(32 * (2**250 - 1))
    return i * pow(x, 11, q) % q # == x**(q-2)


d = -121665 * inv(121666)
I = pow(2, (q - 1) / 4, q)


def xrecover(y):
    xx = (y * y - 1) * inv(d * y * y + 1)
    x = pow(xx, (q + 3) / 8, q)

    if (x * x - xx) % q != 0:
        x = (x * I) % q

    if x % 2 != 0:
        x = q-x

    return x


By = 4 * inv(5)
Bx = xrecover(By)
B = (Bx % q, By % q)


def edwards(P, Q):
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * inv(1 + d * x1 * x2 * y1 * y2)
    y3 = (y1 * y2 + x1 * x2) * inv(1 - d * x1 * x2 * y1 * y2)

    return (x3 % q, y3 % q)


def scalarmult(P, e):
    if e == 0:
        return (0, 1)

    Q = scalarmult(P, e / 2)
    Q = edwards(Q, Q)

    if e & 1:
        Q = edwards(Q, P)

    return Q


def encodeint(y):
    bits = [(y >> i) & 1 for i in range(b)]
    return ''.join([
        chr(sum([bits[i * 8 + j] << j for j in range(8)]))
        for i in range(b/8)
    ])


def encodepoint(P):
    x = P[0]
    y = P[1]
    bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
    return ''.join([
        chr(sum([bits[i * 8 + j] << j for j in range(8)]))
        for i in range(b/8)
    ])


def bit(h, i):
    return (ord(h[i / 8]) >> (i % 8)) & 1


def publickey(sk):
    h = H(sk)
    a = 2 ** (b - 2) + sum(2 ** i * bit(h, i) for i in range(3, b - 2))
    A = scalarmult(B, a)
    return encodepoint(A)


def Hint(m):
    h = H(m)
    return sum(2 ** i * bit(h, i) for i in range(2 * b))


def signature(m, sk, pk):
    h = H(sk)
    a = 2 ** (b - 2) + sum(2 ** i * bit(h, i) for i in range(3, b - 2))
    r = Hint(''.join([h[j] for j in range(b / 8, b / 4)]) + m)
    R = scalarmult(B, r)
    S = (r + Hint(encodepoint(R) + pk + m) * a) % l
    return encodepoint(R) + encodeint(S)


def isoncurve(P):
    x, y = P
    return (-x * x + y * y - 1 - d * x * x * y * y) % q == 0


def decodeint(s):
    return sum(2 ** i * bit(s, i) for i in range(0, b))


def decodepoint(s):
    y = sum(2 ** i * bit(s, i) for i in range(0, b - 1))
    x = xrecover(y)

    if x & 1 != bit(s,  b-1):
        x = q-x

    P = (x, y)

    if not isoncurve(P):
        raise Exception("decoding point that is not on curve")

    return P


def checkvalid(s, m, pk):
    if len(s) != b / 4:
        raise Exception("signature length is wrong")

    if len(pk) != b / 8:
        raise Exception("public-key length is wrong")

    R = decodepoint(s[:b / 8])
    A = decodepoint(pk)
    S = decodeint(s[b / 8:b / 4])
    h = Hint(encodepoint(R) + pk + m)

    if scalarmult(B, S) != edwards(R, scalarmult(A, h)):
        raise Exception("signature does not pass verification")
