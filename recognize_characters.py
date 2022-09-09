import colorsys 
import pickle
import pytesseract
import random
import sys
import time
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont

USING_TESSERACT = True

sys.setrecursionlimit(10000) # We don't talk about this line

if USING_TESSERACT:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract"
    box_stats = {}
else:
    with open('boxes.pickle', 'rb') as handle:
        box_stats = pickle.load(handle)

root = tk.Tk()

def flood(x, y, found, min_x, max_x, min_y, max_y):
    # print(f"Flooding on ({x}, {y})")
    try: # Crude way of making sure pixel is not outside of image
        pixels[x, y]
    except:
        return found, min_x, max_x, min_y, max_y

    if pixels[x, y] == (0, 0, 0) and (x, y) not in found: # Found unvisited black pixel
        found.add((x, y))

        if x < min_x:
            min_x = x
        elif x > max_x:
            max_x = x

        if y < min_y:
            min_y = y
        elif y > max_y:
            max_y = y

        for x1 in range(-1, 2):
            for y1 in range(-1, 2):
                # print(f"({x}, {y}) calling:", (x + x1, y + y1))
                found, min_x, max_x, min_y, max_y = flood(x + x1, y + y1, found, min_x, max_x, min_y, max_y)

    return found, min_x, max_x, min_y, max_y


def draw_line(p, x1, x2, y1, y2, r, g, b):
    
    for x in range(x1, x2 + 1):
        for y in range(y1, y2 + 1):
            try: # Crude way of making sure pixel is not outside of image
                p[x, y] = (r, g, b)
            except:
                pass


file_name = "map5.jpg"

image = Image.open(file_name)
pixels = image.load()
width, height = image.width, image.height

# Convert to black and white

for x in range(width):
    for y in range(height):
        r, g, b = pixels[x, y]
        if 0.2126*r + 0.7152*g + 0.0722*b < 150:
            pixels[x, y] = (0, 0, 0)
        else:
            pixels[x, y] = (255, 255, 255)

image.save("black_and_white.png")

# Drawing boxes around potential candidates

loaded_pixels = set()
boxes = set()
for x in range(width):
    # print(width - x, "x left")
    for y in range(height):
        if (x, y) in loaded_pixels or pixels[x, y] == (255, 255, 255): # Skip over looked-at pixels or white pixels
            continue

        found, min_x, max_x, min_y, max_y = flood(x, y, set(), x, x, y, y)
        x_len = max_x - min_x
        y_len = max_y - min_y

        loaded_pixels.update(found)

        if 10 < len(found) and len(found) < 500 and x_len < 30 and y_len > 5 and y_len < 30: # Is appropriate size for character
            # print(f"Drawing box, {x_len} by {y_len} ==> {len(found)}")
            min_x -= 1
            max_x += 1
            min_y -= 1 
            max_y += 1
            boxes.add((min_x, max_x, min_y, max_y))
            h,s,l = random.random(), 0.5 + random.random()/2.0, 0.4 + random.random()/5.0
            r,g,b = [int(256*i) for i in colorsys.hls_to_rgb(h,l,s)]            
            draw_line(pixels, min_x, max_x, min_y, min_y, r, g, b)
            draw_line(pixels, max_x, max_x, min_y, max_y, r, g, b)
            draw_line(pixels, min_x, max_x, max_y, max_y, r, g, b)
            draw_line(pixels, min_x, min_x, min_y, max_y, r, g, b)
       
# image.show()
image.save("custom_boxes.png")

# Save & Replace Characters

def save_and_replace_char(x1, x2, y1, y2):
    padding = 3
    image2 = Image.new("RGB", (x2 - x1 + 1 + 2*padding, y2 - y1 + 1 + 2*padding), color = "white")
    pixels2 = image2.load()
    for x in range(x1 + 1, x2):
        for y in range(y1 + 1, y2):
            pixels2[x - x1 + padding, y - y1 + padding] = pixels[x, y]
    image2 = image2.convert("L")
    if USING_TESSERACT:
        predict = pytesseract.image_to_data(
            image2, config=("-c tessedit"
                            "_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                            " --psm 10"
                            " -l osd"
                            " "), output_type="data.frame")
        predict = predict[predict.conf != -1]
        try:
            detected_char = str(predict["text"].iloc[0])[0]
            confidence = predict["conf"].iloc[0]   
        except:
            detected_char = ""
            confidence = -1 
    else:
        detected_char = box_stats[(x1, x2, y1, y2)][0]
        confidence = box_stats[(x1, x2, y1, y2)][1]
    # tk_image = ImageTk.PhotoImage(image2.resize((250, 250)))
    # image_label.configure(image = tk_image)
    # caption_label.configure(text=f"{detected_char}, {confidence}% confidence")
    # image_label.pack()
    # caption_label.pack()
    # root.update()

    return detected_char, confidence


image_label = tk.Label(root)
caption_label = tk.Label(root)
caption_label.config(font =("Arial", 60))
image_label.pack()
caption_label.pack()
root.update()

def generate_names(cur_box, used_boxes, detected_name):
    used_boxes.append(cur_box)
    ax1, ax2, ay1, ay2 = cur_box
    detected_char, confidence = save_and_replace_char(ax1, ax2, ay1, ay2)
    global box_stats
    box_stats[cur_box] = (detected_char, confidence)
    if confidence > 69:
        detected_name.append((cur_box, detected_char))

        for box in boxes:
            if box in used_boxes:
                continue
                
            bx1, bx2, by1, by2 = box

            if abs(ay2 - by2) <= y_threshold and abs(ax2 - bx1) <= dist_between_letters: # Part of same word
                used_boxes, detected_name = generate_names(box, used_boxes, detected_name)
                break
    
    return used_boxes, detected_name

used_boxes = []
boxes = sorted(list(boxes), key = lambda b: (b[0], b[3]))
dist_between_letters = 5
y_threshold = 4

for box in boxes:    
    if box in used_boxes:
        continue

    used_boxes, detected_name = generate_names(box, used_boxes, [])
    if not detected_name:
        continue

    label = "".join([i[1] for i in detected_name])

    # Change l's to 1's in room names
    change = True
    is_start = True
    for i in range(len(label)):
        if label[i] == "l":
            continue
        elif label[i].isnumeric() and is_start:
            is_start = False
        elif not is_start and not label[i].isnumeric():
            change = False
    if change:
        label = "".join([i if i != "l" else "1" for i in label])

    print("Found room:", label)
    
    # image3 = Image.open(file_name)
    # pixels3 = image3.load()
    # for i in detected_name:
    #     x1, x2, y1, y2 = i[0]
    #     font = ImageFont.truetype("arial", 45)
        
    #     draw_line(pixels3, x1, x2, y1, y1, 255, 0, 0)
    #     draw_line(pixels3, x2, x2, y1, y2, 255, 0, 0)
    #     draw_line(pixels3, x1, x2, y2, y2, 255, 0, 0)
    #     draw_line(pixels3, x1, x1, y1, y2, 255, 0, 0)
    # ImageDraw.Draw(image3).text((0, 0), f"{label}", (255, 0, 0), font = font)
    # image3.show()
    # tk_image = ImageTk.PhotoImage(image3.resize((1000, 600)))
    # image_label.configure(image = tk_image)
    # image_label.pack()
    # root.update()
    # time.sleep(3)
    

with open('boxes.pickle', 'wb') as handle:
    pickle.dump(box_stats, handle, protocol=pickle.HIGHEST_PROTOCOL)

"""
BEFORE identifying boxes for characters, go through key
In example image, this includes:
- Restroom
- Elevator
- Signage
- Door

Maybe ask user to take another picture of key if applicable?

Go through image and crop image of same size to compare
If within certain threshold, save those coordinates and crop out of original image
- Should help deal with the annoyingness of it later

Save coordinates of each box identified to be a character
Go through each set of coordinates

    PERHAPS DO THIS AS PART OF THE LOOP BEFORE?

    Check if there are any coordinates to the right within a few pixels,
    and approximately on the same y-level:

    These should be part of the same word / room number
    Combine these to form room tag

    TRY TO DIFFERENTIATE BETWEEN SINGULAR ROOM NUMBERS LIKE 8 AND MISCLASSIFIED PIXELS

    TRY TO REMOVE DOTS ABOVE I's

    If it is a word
        Check if it is actually a word, if it isn't a word
            Check pixels in between letters and pixels along the side

            For example, in practice image:
            - Doesn't identify the first "i" in Einstein
            - Doesn't identify "N" and "o" in Neuro since those letters are connected to walls
            - Doesn't identify "h" in Chem since h is connected to wall

            POSSSIBLY CREATE A LIST OF "OFFICE" WORDS TO COMPARE WITH?
             
            For example, in practice image:
            - Doesn't identify "A" and "d" in Admin, but catches "min"
"""

    
                    