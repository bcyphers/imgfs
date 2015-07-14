# Python standard imports
import base64
import os
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

MAX_SIZE = 708000   # max num of bytes which can fit in one bmp
WIDTH = 708         # width of image - must be divisible by 12
OFFSET_UP = 26      # number of bytes in the bmp header
OFFSET_DOWN = 54    # number of bytes in the bmp header

@click.group
def imgfs():
    pass

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
    print iid
    return iid


# Transform data from a file at path into 1MB chunks, and upload them to imgur
@imgfs.command()
@click.option('--file')
def store(client, file):
    client = ImgurClient(CLIENT_ID, CLIENT_SECRET)
    inpf = open(file, 'rb')
    data = inpf.read()
    inpf.close()

    # store file name and size at the head of the stream
    data_bytes = bytearray()
    name_len = len(os.path.basename(file))
    assert name_len <= 255
    data_bytes.extend([name_len] + [ord(c) for c in os.path.basename(file)])

    # make the recursive call to store everything
    return pack_data(client, data, data_bytes)

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

# Decode a file stored as a bitmap rooted at the imgur file 'url'
@imgfs.command()
@click.option('--url')
@click.option('--id')
def get(url, id=None):
    if id:
        url =
    raw = download(url)                     # input
    outfile = open('/tmp/imgfs_out', 'wb')  # output

    # while there are more chunks waiting, load them and extend the data
    while True:
        # parse out file name
        name_len = ord(raw[0])
        if name_len:
            name = raw[1:name_len+1]
            print name
        pos = name_len + 1

        # parse out length of file
        file_len = struct.unpack('@i', bytearray(raw[pos:pos+4]))[0]
        pos += 4
        space_left = MAX_SIZE - pos

        next_url = None
        # parse id of next file, if necessary
        if file_len > space_left:
            next_url = 'http://i.imgur.com/%s.png' % raw[pos:pos+7]
            pos += 7

        print pos, file_len
        print next_url

        # write to the output file
        outfile.write(raw[pos:])

        # get the next chunk
        if next_url:
            raw = download(next_url)
            print [ord(r) for r in raw[:10]]
        else:
            break

    outfile.close()
    os.rename('/tmp/imgfs_out', name)
    return name

def main():
    img_id = store(client, sys.argv[1])
    url = 'http://i.imgur.com/%s.png'%img_id
    print url
    print fetch(url)

if __name__ == '__main__':
    main()
