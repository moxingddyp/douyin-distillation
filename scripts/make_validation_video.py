#!/usr/bin/env python3
"""Create an original silent LOCAL DEMO video for real OCR verification."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--font', type=Path, required=True, help='Existing local font, not bundled')
    args = parser.parse_args()
    if args.output.exists() or not args.font.is_file():
        raise ValueError('New output and existing font required')
    import av
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (640, 240), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((50, 75), 'LOCAL DEMO 123', font=ImageFont.truetype(str(args.font), 54), fill='black')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(args.output), 'w') as container:
        stream = container.add_stream('mpeg4', rate=10)
        stream.width, stream.height, stream.pix_fmt = 640, 240, 'yuv420p'
        for _ in range(30):
            frame = av.VideoFrame.from_image(image)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    print('Created original 3-second silent video; no ASR/OCR inference performed by generator.')


if __name__ == '__main__':
    main()
