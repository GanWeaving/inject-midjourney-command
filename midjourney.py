import os
import shutil
import zipfile
import json
from PIL import Image
import pandas as pd
from pathlib import Path
import logging
import piexif

logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

DOWNLOADS_FOLDER = os.path.join(Path.home(), "Downloads")
DESTINATION_FOLDER = os.path.join(DOWNLOADS_FOLDER, 'MJ_temp')
JSON_FILENAME = 'archived_jobs.json'
FINAL_DESTINATION = "J:\\My Drive\\4 ARCHIVES\\Midjourney\\toCheck"

os.makedirs(DESTINATION_FOLDER, exist_ok=True)

def read_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    parsed_data = [{'Filename': item.get('_archived_files')[0], 'Prompt': item.get('full_command')} 
                   for item in data if item.get('_archived_files') and item.get('full_command')]
    return pd.DataFrame(parsed_data)

def process_zip_files(files_to_move):
    for file in files_to_move[:5]:
        try:
            shutil.move(os.path.join(DOWNLOADS_FOLDER, file), DESTINATION_FOLDER)
            logging.info(f"Moved {file} to MJ_temp folder")
        except Exception as e:
            logging.error("Error while moving files: ", exc_info=True)

def extract_zip_files():
    for file in os.listdir(DESTINATION_FOLDER):
        if file.endswith('.zip'):
            print(f"Extracting file: {file}")
            try:
                extraction_folder = os.path.join(DESTINATION_FOLDER, os.path.splitext(file)[0])
                os.makedirs(extraction_folder, exist_ok=True)
                with zipfile.ZipFile(os.path.join(DESTINATION_FOLDER, file), 'r') as zip_ref:
                    zip_ref.extractall(extraction_folder)
                    logging.info(f"Extracted {file}")
                zip_files_folder = os.path.join(DESTINATION_FOLDER, 'zip_files')
                os.makedirs(zip_files_folder, exist_ok=True)
                shutil.move(os.path.join(DESTINATION_FOLDER, file), zip_files_folder)
                logging.info(f"Moved {file} to 'zip_files' folder")
            except Exception as e:
                logging.error("Error while extracting/moving files: ", exc_info=True)

def convert_png_to_jpg_and_add_exif():
    for root, dirs, files in os.walk(DESTINATION_FOLDER):
        if JSON_FILENAME in files:
            try:
                image_data = read_json(os.path.join(root, JSON_FILENAME))
            except Exception as e:
                logging.error(f"Error reading JSON file at {os.path.join(root, JSON_FILENAME)}: {e}", exc_info=True)
                continue

            for file in files:
                if file.endswith('.png'):
                    try:
                        im = Image.open(os.path.join(root, file))
                        rgb_im = im.convert('RGB')
                        filename = file
                        if filename in image_data['Filename'].values:
                            prompt = image_data[image_data['Filename'] == filename]['Prompt'].values[0]
                            filename_without_extension = os.path.splitext(file)[0]
                            rgb_im.save(os.path.join(root, filename_without_extension + '.jpg'), 'JPEG', quality=90, icc_profile=im.info.get('icc_profile'))
                            exif_dict = {"Exif": {piexif.ExifIFD.UserComment: prompt.encode()}}
                            exif_bytes = piexif.dump(exif_dict)
                            piexif.insert(exif_bytes, os.path.join(root, filename_without_extension + '.jpg'))
                            os.remove(os.path.join(root, file))
                            logging.info(f"Converted {file} to JPG and added EXIF metadata")
                        else:
                            logging.warning(f"{filename} not found in the JSON file")
                    except Exception as e:
                        logging.error("Error while converting image and adding EXIF metadata: ", exc_info=True)
            print(f"Finished converting images in folder: {root}")

def move_folders():
    for folder in os.listdir(DESTINATION_FOLDER):
        folder_path = os.path.join(DESTINATION_FOLDER, folder)
        if os.path.isdir(folder_path) and folder != 'zip_files':
            if any(file.endswith('.jpg') for file in os.listdir(folder_path)):
                print(f"Moving folder: {folder}")
                try:
                    shutil.move(folder_path, FINAL_DESTINATION)
                    logging.info(f"Moved {folder} to the 'toCheck' folder")
                    print(f"Moved {folder} to the 'toCheck' folder")
                except Exception as e:
                    logging.error("Error while moving folders: ", exc_info=True)

if __name__ == '__main__':
    while True:
        files_to_move = [f for f in os.listdir(DOWNLOADS_FOLDER) if f.startswith('midjou') and f.endswith('.zip')]
        if not files_to_move:
            break
        process_zip_files(files_to_move)
        extract_zip_files()
    convert_png_to_jpg_and_add_exif()
    move_folders()
