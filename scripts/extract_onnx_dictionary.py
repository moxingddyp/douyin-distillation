#!/usr/bin/env python3
"""Extract an existing recognition model's embedded dictionary locally; no download."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.model.is_file() or args.output.exists():
        raise ValueError('Existing model and new output required')
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(args.model), sess_options=options, providers=['CPUExecutionProvider'])
    character = session.get_modelmeta().custom_metadata_map.get('character', '')
    if not character.strip():
        raise ValueError('No embedded dictionary; explicitly obtain matching local dictionary')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(character, encoding='utf-8')
    print('Extracted dictionary from local model; no network, no model output generated.')


if __name__ == '__main__':
    main()
