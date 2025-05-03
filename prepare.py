import glob
import logging
import os
import sys
import shutil

KB = 1024
MAX_FILE_SIZE = 1990 * KB

logging.basicConfig(level=logging.INFO)

work_dir = '' if len(sys.argv) <= 1 else f'{sys.argv[1]}/'

print(sys.argv)


def move_files_from_build_to_root():
    source = f'{work_dir}Build'
    destination = f'{work_dir}'
    if not os.path.exists(source):
        logging.warning(f"{source} directory not found. skip file moving")
        return
    allfiles = os.listdir(source)
    for f in allfiles:
        src_path = os.path.join(source, f)
        dst_path = os.path.join(destination, f)
        shutil.move(src_path, dst_path)
    os.rmdir(source)


def split_file(path: str):
    with open(path, 'rb') as f:
        n = 0
        while True:
            buf = f.read(MAX_FILE_SIZE)
            if len(buf) == 0:
                break
            split_file_name = f"{path}.{str(n).rjust(2, '0')}"
            logging.info(f'create file {split_file_name}')
            with open(split_file_name, 'wb') as sp_f:
                sp_f.write(buf)
            n += 1


def try_split_file(file_pattern: str) -> list[str]:
    logging.info(f"split {file_pattern}")
    files: list[str] = glob.glob(file_pattern, root_dir=work_dir)
    source_files = [f for f in files if not f.split('.')[-1].isdigit()]
    if len(source_files) > 1:
        raise Exception(f"expected one '{file_pattern}' file, but found {len(source_files)}: {source_files}")
    already_split = [f for f in files if f.split('.')[-1].isdigit()]
    if len(source_files) == 1 and len(already_split) > 0:
        logging.info(f'found {len(already_split)} already split files. They will removed')
        for f in already_split:
            logging.info(f'remove {f}')
            os.remove(f'{work_dir}{f}')
    if len(source_files) == 1:
        source_file = source_files[0]
        if os.path.getsize(f'{work_dir}{source_file}') <= MAX_FILE_SIZE:
            logging.info('split not required')
            return [source_file]
        logging.info(f"split {source_file}")
        split_file(f'{work_dir}{source_file}')
        logging.info(f"remove {source_file}")
        os.remove(f'{work_dir}{source_file}')
        already_split = [f for f in glob.glob(f'{source_file}.*', root_dir=work_dir) if f.split('.')[-1].isdigit()]
    if len(already_split) == 0:
        raise Exception(f'not found original or split files for pattern {file_pattern}')
    return already_split


def split_binary_files_if_need() -> dict[str, list[str]]:
    return {
        'dataUrl': try_split_file("*.data.*"),
        'codeUrl': try_split_file("*.wasm.*")
    }


def replace_url(source: str, mapped_files: dict[str, list[str]], replaced_key) -> str:
    if replaced_key not in mapped_files:
        logging.warning(f'replace key `{replaced_key}` not found in mapper. Skip')
        return source
    replaced_value = mapped_files[replaced_key]
    l_index = source.find(f'{replaced_key}: ')
    if l_index == -1:
        logging.warning(f'position not found for replace {replaced_key}')
        return source
    r_index = source.find('\n', l_index)
    if r_index == -1:
        r_index = len(source)
    str_value = f'"{replaced_value[0]}"' if len(replaced_value) == 1 else str(replaced_value)
    logging.info(f'replace `{replaced_key}` on `{str_value}`')
    return source[:l_index] + f'{replaced_key}: {str_value},' + source[r_index:]


def modify_index_html(mapped_files: dict[str, list[str]]):
    logging.info('modify index.html')
    with open(f'{work_dir}index.html', 'r', encoding='utf-8') as f:
        source = f.read()
        source = source.replace('Build/', '')
        source = replace_url(source, mapped_files, 'dataUrl')
        source = replace_url(source, mapped_files, 'codeUrl')
    with open(f'{work_dir}index.html', 'w', encoding='utf-8') as f:
        f.write(source)


move_files_from_build_to_root()
mapped_files = split_binary_files_if_need()
modify_index_html(mapped_files)

logging.info('completed')
