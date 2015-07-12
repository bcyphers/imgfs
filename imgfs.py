import sys

from imgurpython import ImgurClient

client_id = ''
client_secret = ''

def int_to_bytes(inp):
    return [(inp>>24)&8, (inp>>16)&8, (inp>>8)&8, inp&8]

def encode_file(path):
    inpf = open(path, 'rb')
    data = f.read()
    inpf.close()

    l = len(data)
    width = 708
    size = l if l % width == 0 else l + width - (l % width)
    assert size < 1048548
    height = size / width
    offset = 14 + 12

    f_head_bytes = bytearray(
            [ord('B'), ord('M')] +  # file type ('BitMap')
            int_to_bytes(size) +    # size of BMP file in bytes
            [0, 0, 0, 0] +          # unused
            int_to_bytes(offset))   # offset of byte where pixel arr starts

    dib_head_bytes = bytearray(
            [0, 0, 0, 12] +             # size of this header
            int_to_bytes(width)[2:] +   # width in pixels (2B)
            int_to_bytes(height)[2:] +  # height in pixels (2B)
            [0, 1] +                    # number of color planes (1, 2B)
            [0, 8])                     # number of bitsbytes per pixel

    data_bytes = bytearray(size)
    data_bytes[:len(data)] = data

    path = '/tmp/' + base64.b32encode(hash(path))
    outf = open(path, 'wb')
    outf.write(f_head_bytes + dib_head_bytes + data_bytes)
    outf.close()
    return path

def upload_file(client, path):
    path = encode_file(path)
    client.upload_from_path(path)

def decode_image(client, image_id):
    img = client.get_image(image_id)

def main():
    client = ImgurClient(client_id, client_secret)

if __name__ == '__main__':
    main()
