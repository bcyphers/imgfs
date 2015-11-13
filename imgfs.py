# Python standard imports
import argparse
import base64
import os
import struct
import sys
import urllib
import zlib

# External imports
from PIL import Image
from imgurpython import ImgurClient

# argparse
parser = argparse.ArgumentParser(description='Upload or or download files from imgur.com')
parser.add_argument('--file', dest='path', help='path of file to upload')
parser.add_argument('--url', dest='url', help='url of file to download')
parser.add_argument('--id', dest='img_id', help='imgur id of file to download')
parser.add_argument('--password', dest='password',
                    help='encrypt or decrypt the file with the provided password')

args = parser.parse_args()

# imgur API keys
CLIENT_ID = os.environ('IMGUR_CLIENT')
CLIENT_SECRET = os.environ('IMGUR_SECRET')

MAX_SIZE = 708000   # max num of bytes which can fit in one bmp
WIDTH = 708         # width of image - must be divisible by 12
OFFSET_UP = 26      # number of bytes in the bmp header
OFFSET_DOWN = 54    # number of bytes in the bmp header
URL_TEMPLATE = 'http://i.imgur.com/%s.png'

# Encode data_bytes as a bitmap, and return a path to the resulting file
def encode(data_bytes):
    size = len(data_bytes)
    height = size / WIDTH

    # generate the image header
    f_head_bytes = bytearray(
            [ord('B'), ord('M')] +                # file type ('BitMap')
            list(struct.pack('@i', size)) +       # size of BMP file in bytes
            [0, 0, 0, 0] +                        # unused
            list(struct.pack('@i', OFFSET_UP)))   # offset of pixel array starts

    dib_head_bytes = bytearray(
            struct.pack('@i', 12) +         # size of this header
            struct.pack('@h', WIDTH/3) +    # width in pixels (short int)
            struct.pack('@h', height) +     # width in pixels (short int)
            struct.pack('@h', 1) +          # number of color planes (1, short)
            struct.pack('@h', 24))          # number of bits per pixel

    # write the resulting byte stream to a file
    path = '/tmp/imgfs_tmp.bmp'
    outf = open(path, 'wb')
    outf.write(f_head_bytes + dib_head_bytes + data_bytes)
    outf.close()
    return path

# generate bitmaps in 1MB chunks until all of the data have been stored
def pack_data(client, data, data_bytes=None):
    # if this is the first chunk of a file, data_bytes will come pre-packed
    # with the filename at the head. Otherwise, start with a null byte.
    if not data_bytes:
        data_bytes = bytearray([0])

    # store the size of the remaining file at the head
    data_bytes.extend(struct.pack('@i', len(data)))
    space_left = MAX_SIZE - len(data_bytes)

    next_img = None
    # check if the chunk is too big to fit into one file
    if len(data) > space_left:
        # If so, we need 7 bytes to store the next image id
        space_left -= 7
        # recurse with the rest of the data
        next_img = pack_data(client, data[space_left:])
        # link to this chunk's successor
        data_bytes.extend(str(next_img))
        data = data[:space_left]

    # now fill the rest of the space in the file with our bytes
    data_bytes.extend(data)
    l = len(data_bytes)
    size = l if l % WIDTH == 0 else l + WIDTH - (l % WIDTH)
    data_bytes.extend([0] * (size - l))
    assert len(data_bytes) <= MAX_SIZE

    # store the bytes in a bmp and upload it
    ipath = encode(data_bytes)
    iid = client.upload_from_path(ipath)['id']
    return iid


# Download an image and return the raw byte stream payload
def download(url):
    img_id = url.split('/')[-1].split('.')[0]
    path = '/tmp/' + img_id + '.png'
    urllib.urlretrieve(url, path)

    # convert png to bmp
    img = Image.open(path)
    newpath = path.replace('.png', '.bmp')
    img.save(newpath)

    # read in relevant bytes
    with open(newpath, 'rb') as f:
        return f.read()[OFFSET_DOWN:]


def encrypt(stream, pwd):
    aes = AES.new(pwd, AES.MODE_CBC, iv)
    return aes.encrypt(stream)


def decrypt(stream, pwd):
    aes = AES.new(pwd, AES.MODE_CBC, iv)
    return aes.decrypt(stream)


# Transform data from a file at path into 1MB chunks, and upload them to imgur
def up(filename, passwd=None):
    client = ImgurClient(CLIENT_ID, CLIENT_SECRET)
    inpf = open(filename, 'rb')
    data = inpf.read()
    inpf.close()

    # store file name and size at the head of the stream
    data_bytes = bytearray()
    name_len = len(os.path.basename(filename))
    assert name_len <= 255
    data_bytes.extend([name_len] + [ord(c) for c in os.path.basename(filename)])

    # make the recursive call to store everything
    return pack_data(client, data, data_bytes)


# Decode a file stored as a bitmap rooted at the imgur file 'url'
def down(url=None, img_id=None, passwd=None):
    if img_id:
        url = URL_TEMPLATE % img_id
    if not url:
        exit(1)

    raw = download(url)                     # input
    outfile = open('/tmp/imgfs_out', 'wb')  # output

    # while there are more chunks waiting, load them and extend the data
    while True:
        # parse out file name
        name_len = ord(raw[0])
        if name_len:
            name = raw[1:name_len+1]
            print 'downloading file', name,
        pos = name_len + 1

        # parse out length of file
        file_len = struct.unpack('@i', bytearray(raw[pos:pos+4]))[0]
        pos += 4
        space_left = MAX_SIZE - pos

        next_url = None
        # parse id of next file, if necessary
        if file_len > space_left:
            next_url = URL_TEMPLATE % raw[pos:pos+7]
            pos += 7

        print 'unpacking file', file_len, 'bytes'

        # write to the output file
        outfile.write(raw[pos:])

        # get the next chunk
        if next_url:
            raw = download(next_url)
        else:
            break

    outfile.close()
    os.rename('/tmp/imgfs_out', name)
    return name


def main():
    # download things
    if args.url:
        print down(url=args.url, passwd=args.password)
        sys.exit(0)
    if args.img_id:
        print down(img_id=args.img_id, passwd=args.password)
        sys.exit(0)

    # upload things
    if args.path:
        img_id = up(args.path, passwd=args.password)
        print 'imgur id:', img_id
        print 'url:', URL_TEMPLATE % img_id
        sys.exit(0)

    print 'No command provided! Exiting.'
    sys.exit(1)


if __name__ == '__main__':
    main()
