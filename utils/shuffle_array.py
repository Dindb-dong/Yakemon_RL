# shuffle_array.py

import random

def shuffle_array(arr):
    arr_copy = arr.copy()
    random.shuffle(arr_copy)
    return arr_copy