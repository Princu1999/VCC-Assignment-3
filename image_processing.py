import base64
import io
import time
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def remove_background(image):
    """
    Uses GrabCut to remove the background. This is a naive approach:
    it assumes the main object is roughly centered.
    """
    mask = np.zeros(image.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)

    # Define a rectangle that covers almost the entire image
    rect = (1, 1, image.shape[1] - 2, image.shape[0] - 2)

    # Run GrabCut
    cv2.grabCut(image, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)

    # Create a mask where sure and likely backgrounds set to 0, otherwise 1
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

    # Multiply the mask to the input image to remove the background
    removed_bg = image * mask2[:, :, np.newaxis]
    return removed_bg

def blur_image(image):
    """
    Applies a Gaussian blur to the image.
    Increase the kernel size to make it blurrier.
    """
    return cv2.GaussianBlur(image, (25, 25), 0)

def mark_edges(image):
    """
    Uses Canny to detect edges, then marks those edges in red on the original image.
    """
    edges = cv2.Canny(image, 100, 200)
    edge_marked = image.copy()
    # Mark edges in red
    edge_marked[edges != 0] = [0, 0, 255]
    return edge_marked


def highlight_border(image):
    """
    Draws a green rectangle around the border of the image.
    """
    border_img = image.copy()
    rows, cols = border_img.shape[:2]
    cv2.rectangle(border_img, (0, 0), (cols - 1, rows - 1), (0, 255, 0), 5)
    return border_img


def mirror_image(image):
    """
    Flips the image horizontally (mirror effect).
    """
    return cv2.flip(image, 1)  # 1 => horizontal flip

def kaleidoscope_effect(image):
    """
    Creates a simple kaleidoscope effect by mirroring
    the top-left quadrant into the other quadrants.
    """
    rows, cols = image.shape[:2]
    mid_row = rows // 2
    mid_col = cols // 2

    # Top-left quadrant
    top_left = image[:mid_row, :mid_col]

    # Mirror horizontally -> top_right
    top_right = cv2.flip(top_left, 1)

    # Mirror vertically -> bottom_left
    bottom_left = cv2.flip(top_left, 0)

    # Mirror both horizontally & vertically -> bottom_right
    bottom_right = cv2.flip(bottom_left, 1)

    # Combine quadrants
    top_half = np.concatenate((top_left, top_right), axis=1)
    bottom_half = np.concatenate((bottom_left, bottom_right), axis=1)
    kaleido_img = np.concatenate((top_half, bottom_half), axis=0)

    return kaleido_img

def encode_to_base64(image):
    """
    Encodes an image (NumPy array) to base64 PNG string.
    Returns None if encoding fails.
    """
    success, buffer = cv2.imencode('.png', image)
    if not success:
        return None
    return base64.b64encode(buffer).decode('utf-8')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_images():
    """
    Receives multiple images from the front end, applies the 6 operations
    to each image, and returns a JSON response containing all results.
    Each image has its own section of results.
    """
    files = request.files.getlist('images')
    if not files or len(files) == 0:
        return jsonify({'error': 'No images uploaded'}), 400

    all_results = []

    for file in files:
        # Decode image
        file_bytes = np.frombuffer(file.read(), np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if image is None:
            continue  # Skip if decoding failed

        # Track how long it takes to process (optional)
        start_time = time.time()

        # Perform all requested operations on the ORIGINAL image
        bg_removed_img = remove_background(image)
        blurred_img = blur_image(image)
        edges_img = mark_edges(image)
        border_img = highlight_border(image)
        mirror_img = mirror_image(image)
        kaleido_img = kaleidoscope_effect(image)

        processing_time = time.time() - start_time
        print(f"Processing time for one image: {processing_time:.2f} seconds")

        # Encode each result to Base64
        results_for_this_image = {
            'removed_bg': encode_to_base64(bg_removed_img),
            'blur': encode_to_base64(blurred_img),
            'edges': encode_to_base64(edges_img),
            'border': encode_to_base64(border_img),
            'mirror': encode_to_base64(mirror_img),
            'kaleido': encode_to_base64(kaleido_img)
        }

        all_results.append(results_for_this_image)

    # Return JSON with all images' results
    return jsonify({'processed_images': all_results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
