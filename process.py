import enchant
import json
import sys

from PIL import Image
from time import perf_counter

from utils.bounding_boxes import get_bounding_boxes
from utils.bw import convert_to_bw
from utils.font_size import get_max_font_size
from utils.recognize import process_image
from utils.rect import find_rectangles
from utils.simplify import simplify_map
from utils.symbols import get_similarity_thresholds

start_time = perf_counter()

id = sys.argv[1]
READ_FROM = sys.argv[2]

IMAGE_SAVE_PATH = f"media/{id}/"
FILE_NAME = IMAGE_SAVE_PATH + READ_FROM
ALLOWED_ROOM_NAMES = enchant.request_pwl_dict("utils/potential_room_names.txt")
BW_THRESHOLD = 150 # Values less than this will become black
WEAK_CONFIDENCE = 75.0
HIGH_CONFIDENCE = 90.0
MAX_FONT_SIZE = get_max_font_size(FILE_NAME, ALLOWED_ROOM_NAMES, WEAK_CONFIDENCE, HIGH_CONFIDENCE)
POS_SYMBOLS = ["door", "stairs"]
SIMILARITY_THRESHOLDS = get_similarity_thresholds(POS_SYMBOLS)

original_image = Image.open(FILE_NAME).convert("RGB")
WIDTH, HEIGHT = original_image.size[0], original_image.size[1]

bw_image = convert_to_bw(original_image, BW_THRESHOLD)
bw_image.save(IMAGE_SAVE_PATH + f"black_and_white_{READ_FROM[:-4]}.png")


print("Max font size:", MAX_FONT_SIZE)
boxes, boxes_image = get_bounding_boxes(IMAGE_SAVE_PATH + f"black_and_white_{READ_FROM[:-4]}.png", MAX_FONT_SIZE)
boxes_image.save(IMAGE_SAVE_PATH + f"boxes_{READ_FROM[:-4]}.png")

print("Processing image...")
rooms, blank_image = process_image(boxes, bw_image, SIMILARITY_THRESHOLDS, ALLOWED_ROOM_NAMES, MAX_FONT_SIZE) 
blank_pixels = blank_image.load()

print("Getting rectangles...")
loaded_pixels, rectangles = set(), []
for x in range(WIDTH):
    for y in range(HEIGHT):
        if (x, y) in loaded_pixels or blank_pixels[x, y] == (255, 255, 255): # Skip over looked-at pixels or white pixels
            continue

        found, min_x, max_x, min_y, max_y = find_rectangles(blank_pixels, x, y, set(), x, x, y, y)
        x_len = max_x - min_x
        y_len = max_y - min_y

        loaded_pixels.update(found)
        rectangles.append([min_x, min_y, min_x, max_y, x_len])
            
blank_image.save(IMAGE_SAVE_PATH + f"blank_map_{READ_FROM[:-4]}.png")

print("Getting paths and doorways...")

blank_image, doorways = simplify_map(rooms, blank_image)
blank_pixels = blank_image.load()
blank_image.save(IMAGE_SAVE_PATH + f"pathways_{READ_FROM[:-4]}.png")

print("Saving paths...")
map = [[1 if blank_pixels[x, y] == (0, 0, 0) else 2 if blank_pixels[x, y] == (255, 255, 0) else 0 for y in range(HEIGHT)] for x in range(WIDTH)] # 1 is for everything that is not a path, 0 is for the paths, and 2 is for doorways            

with open(IMAGE_SAVE_PATH + f"render_{READ_FROM[:-4]}.json", "w") as f:
    json.dump({"rooms": rooms, "points": rectangles, "map": map, "doorways": doorways}, f, indent = 4) 
    
print("Entire program took", round(perf_counter() - start_time, 3), "seconds.")