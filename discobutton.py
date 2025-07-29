#!/usr/bin/python3
import time
import os
import pygame
import sys
import random
import csv
from datetime import datetime
from gpiozero import LED, Button

def get_next_track(path, queue):
    # Refill & reshuffle when empty
    if not queue:
        queue.extend([
            f for f in os.listdir(path)
            if f.endswith('.mp3') and not f.startswith('._')
        ])
        random.shuffle(queue)
    return queue.pop()

# Setup GPIO using gpiozero
disco_lights = LED(22)
red_button_input = Button(23, bounce_time=0.01)
door_closed_input = Button(24, pull_up=True, bounce_time=0.1)
alan_playing = False
disco_playing = False
music_paused = False
alan_queue = []

# Initialize Pygame mixer
pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()
pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)

folder_path = "/home/jim/shared/alan"
disco_path = "/home/jim/shared/disco"
metal_path = "/home/jim/shared/metal"

def log_event(event_type, detail=''):
    with open('event_log.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), event_type, detail])

def play_random_alan_watts(alan_path):
    global alan_playing, disco_playing, music_paused, alan_queue
    disco_lights.off()

    if not music_paused:
        # get one track from the queue, reshuffling under the hood
        next_file = get_next_track(alan_path, alan_queue)
        mp3_path = os.path.join(alan_path, next_file)
        pygame.mixer.music.load(mp3_path)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play()
        alan_playing = True
        disco_playing = False
        music_paused = False
    else:
        pygame.mixer.music.unpause()
        alan_playing = True
        disco_playing = False
        music_paused = False


def play_disco(disco_path):
    global disco_playing, alan_playing, music_paused
    disco_lights.on()
    disco_mp3s = [file for file in os.listdir(disco_path) if file.endswith('.mp3') and not file.startswith('._')]
    random.shuffle(disco_mp3s)
    if disco_mp3s:
        disco_file_path = os.path.join(disco_path, disco_mp3s[0])
        pygame.mixer.music.stop()
        pygame.mixer.music.load(disco_file_path)
        pygame.mixer.music.set_volume(1)
        pygame.mixer.music.play()
        disco_playing = True
        alan_playing = False
        music_paused = False
    else:
        print("No MP3 files found in the directory.")

def on_button_press():
    global disco_playing, alan_playing, music_paused
    print("Button Pressed!")
    log_event('Button Pressed')
    door_closed = door_closed_input.is_pressed
    if not disco_playing and door_closed:
        if alan_playing:
            pygame.mixer.music.pause()
            music_paused = True
            play_disco(disco_path)
        else:
            play_disco(disco_path)
    elif disco_playing and door_closed:
        pygame.mixer.music.stop()
        music_paused = False
        play_random_alan_watts(folder_path)

def door_opened():
    global alan_playing, disco_playing, music_paused
    print("Door Opened!")
    log_event('Door Opened')
    disco_lights.off()
    if alan_playing:
        pygame.mixer.music.pause()
        music_paused = True

def on_door_close():
    global alan_playing, disco_playing, music_paused
    print("Door Closed!")
    log_event('Door Closed')
    if music_paused and alan_playing:
        pygame.mixer.music.unpause()
    else:
        play_random_alan_watts(folder_path)
        
def handle_events():
    for event in pygame.event.get():
        if event.type == pygame.USEREVENT + 1 and disco_playing == False:  # Music end event
            play_random_alan_watts(folder_path)  # Play the next random mp3 

if __name__ == "__main__":
    red_button_input.when_pressed = on_button_press
    door_closed_input.when_pressed = on_door_close
    door_closed_input.when_released = door_opened

    try:
        while True:
            time.sleep(0.1)
            handle_events()
    except KeyboardInterrupt:
        print("Stopping playback...")
        pygame.mixer.music.stop()

    # Clean up on exit
    disco_lights.off()
