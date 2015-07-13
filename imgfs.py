# Python standard imports
import base64
import struct
import sys
import urllib
import zlib

# External imports
import click
from PIL import Image
from imgurpython import ImgurClient


# imgur API keys
CLIENT_ID = '49a3539b974a943'
CLIENT_SECRET = 'c388111edc11a479283a03ed6fbe3522f52fa726'

MAX_SIZE = 1048548  # max num of bytes which can fit in one bmp
WIDTH = 708         # width of image - chosen to maxmize potential file size
OFFSET = 26         # number of bytes in the bmp header

# Encode a generic file at `path` as a bitmap, and return a path to the
# resulting file
# TODO
def encode_png(path):
    inpf = open(path, 'rb')
    data = inpf.read()
    inpf.close()

    l = len(data)
    size = l if l % WIDTH == 0 else l + WIDTH - (l % WIDTH)
    assert size < MAX_SIZE
    height = size / WIDTH

    # standard PNG file header
    f_head_bytes = bytearray(
            [0x89,                              # Leading bit set for image
             ord('P'), ord('N'), ord('G'),      # file type ('PNG')
             0x0D, 0x0A,                        # CRLF
             0x1A,                              # DOS end-of-file char
             0x0A])                             # LF

    # first heading chunk: IHDR
    ihdr_data = ('IHDR' +                       # IHDR identifier
            bytes(struct.pack('@i', width)) +   # width in pixels (int32)
            bytes(struct.pack('@i', height)) +  # height in pixels (int32)
            '\x08\x00' +                        # bit depth and color type
            '\x00\x00\x00')                     # padding

    ihdr_bytes = bytearray(
            struct.pack('@i', 13) +                     # size of this chunk
            ihdr_data +                                 # header and payload
            struct.pack('@i', zlib.crc32(ihdr_data)))   # checksum


    data_bytes = bytearray(size)
    data_bytes[:len(data)] = data

    # write the resulting byte stream to a file
    path = '/tmp/' + base64.b16encode(str(hash(path)))[-10:] + '.png'
    outf = open(path, 'wb')
    outf.write(f_head_bytes + dib_head_bytes + data_bytes)
    outf.close()
    return path

# Encode a generic file at `path` as a bitmap, and return a path to the
# resulting file
def encode(path):
    inpf = open(path, 'rb')
    data = inpf.read()
    inpf.close()

    l = len(data)
    size = l if l % WIDTH == 0 else l + WIDTH - (l % WIDTH)
    assert size < MAX_SIZE
    height = size / WIDTH

    # generate the image header
    f_head_bytes = bytearray(
            [ord('B'), ord('M')] +                # file type ('BitMap')
            list(struct.pack('@i', size)) +       # size of BMP file in bytes
            [0, 0, 0, 0] +                        # unused
            list(struct.pack('@i', OFFSET)))      # offset of pixel array starts

    dib_head_bytes = bytearray(
            struct.pack('@i', 12) +         # size of this header
            struct.pack('@h', WIDTH/3) +    # width in pixels (short int)
            struct.pack('@h', height) +     # width in pixels (short int)
            struct.pack('@h', 1) +          # number of color planes (1, short)
            struct.pack('@h', 24))          # number of bits per pixel

    data_bytes = bytearray(size)
    data_bytes[:4] = struct.pack('@i', len(data))
    data_bytes[4:4+len(data)] = data

    # write the resulting byte stream to a file
    path = '/tmp/' + base64.b16encode(str(hash(path)))[-10:] + '.bmp'
    outf = open(path, 'wb')
    outf.write(f_head_bytes + dib_head_bytes + data_bytes)
    outf.close()
    return path

# Decodes the data bitmap at `path` and returns a path to the plain text file
def decode(path):
    img = Image.open(path)
    newpath = path.replace('.png', '.bmp')
    img.save(newpath)

    # parse the data from
    offset = 40
    f = open(newpath, 'rb')
    data = f.read()[offset:]
    length = struct.unpack('@i', bytearray(data[:4]))[0]

    # write the relevant bytes to a plain text file
    outpath = 'result'
    outf = open(outpath, 'wb')
    outf.write(data[4:4+length])
    outf.close()

    return outpath

# Download and decode a plain text file stored as a bitmap at URL
def download(url):
    img_id = url.split('/')[-1].split('.')[0]
    path = '/tmp/' + img_id + '.png'
    urllib.urlretrieve(url, path)
    return decode(path)

# Encode and upload a generic file at `path` to imgur, and return the URL
def upload(client, path):
    ipath = encode(path)
    return client.upload_from_path(ipath)['link']

def main():
    client = ImgurClient(CLIENT_ID, CLIENT_SECRET)
    url = upload(client, sys.argv[1])
    print url
    print download(url)

if __name__ == '__main__':
    main()
