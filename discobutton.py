#!/usr/bin/python3
import time
import os
import pygame
import sys
import random
import csv
from datetime import datetime, date
from gpiozero import LED, Button

# Setup GPIO using gpiozero
disco_lights = LED(22)
red_button_input = Button(23, bounce_time=0.1)
door_closed_input = Button(24, pull_up=True, bounce_time=0.1)
alan_playing = False
disco_playing = False
music_paused = False

# Queues for true shuffle playback
alan_queue = []
disco_queue = []
# Track last reset to clear queues at midnight
last_reset_date = date.today()

def get_next_track(path, queue):
    """
    Return the next track from the queue; refill & reshuffle when empty.
    """
    if not queue:
        queue.extend([
            f for f in os.listdir(path)
            if f.endswith('.mp3') and not f.startswith('._')
        ])
        random.shuffle(queue)
    return queue.pop()

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
    print("play_random_alan_watts")
    global alan_playing, disco_playing, music_paused, alan_queue
    disco_lights.off()
    if not music_paused:  # Play next shuffled track
        print("not music_paused")
        next_file = get_next_track(alan_path, alan_queue)
        mp3_path = os.path.join(alan_path, next_file)
        pygame.mixer.music.load(mp3_path)
        print('Now Playing', mp3_path)
        pygame.mixer.music.play()
        pygame.mixer.music.set_volume(0.2)
        alan_playing = True
        disco_playing = False
        music_paused = False
    else:  # Resume playback if paused
        print("music_paused")
        pygame.mixer.music.unpause()
        alan_playing = True
        disco_playing = False
        music_paused = False


def play_disco(disco_path):
    print("play_disco")
    global disco_playing, alan_playing, music_paused, disco_queue
    disco_lights.on()
    # Play next shuffled disco track
    next_file = get_next_track(disco_path, disco_queue)
    disco_file_path = os.path.join(disco_path, next_file)
    pygame.mixer.music.stop()
    pygame.mixer.music.load(disco_file_path)
    pygame.mixer.music.set_volume(1)
    pygame.mixer.music.play()
    disco_playing = True
    alan_playing = False
    music_paused = False


def on_button_press():
    global disco_playing, alan_playing, music_paused
    print("-------------")
    print("Button Pressed!  State before press:")
    print(f"alan_playing={alan_playing}, disco_playing={disco_playing}, music_paused={music_paused}")
    print("-------------")
    log_event('Button Pressed')
    door_closed = door_closed_input.is_pressed
    if door_closed:
        if not disco_playing:
            if alan_playing:
                pygame.mixer.music.pause()
                music_paused = True
                play_disco(disco_path)
            else:
                play_disco(disco_path)
        else:
            pygame.mixer.music.stop()
            music_paused = False
            play_random_alan_watts(folder_path)


def door_opened():
    global alan_playing, disco_playing, music_paused
    print("-------------")
    print("Door Opened!  State before open:")
    print(f"alan_playing={alan_playing}, disco_playing={disco_playing}, music_paused={music_paused}")
    print("-------------")
    log_event('Door Opened')
    if alan_playing:
        pygame.mixer.music.pause()
        music_paused = True
    else:
        pygame.mixer.music.stop()
        disco_lights.off()
        disco_playing = False


def on_door_close():
    global alan_playing, disco_playing, music_paused
    print("-------------")
    print("Door Closed!  State before close:")
    print(f"alan_playing={alan_playing}, disco_playing={disco_playing}, music_paused={music_paused}")
    print("-------------")
    log_event('Door Closed')
    if music_paused and alan_playing:
        pygame.mixer.music.unpause()
        music_paused = False
        print("Unpaused Alan Watts")
    else:
        play_random_alan_watts(folder_path)


def handle_events():
    global disco_playing
    for event in pygame.event.get():
        if event.type == pygame.USEREVENT + 1:  # Music end event
            if not disco_playing:
                print("Music End Event")
                play_random_alan_watts(folder_path)


def reset_queues_daily():
    """
    Clear both queues once per day at midnight.
    """
    global last_reset_date, alan_queue, disco_queue
    today = date.today()
    if today != last_reset_date:
        alan_queue.clear()
        disco_queue.clear()
        last_reset_date = today
        print(f"Queues reset for {today}")


if __name__ == "__main__":
    red_button_input.when_pressed = on_button_press
    door_closed_input.when_pressed = on_door_close
    door_closed_input.when_released = door_opened

    try:
        while True:
            reset_queues_daily()
            time.sleep(0.1)
            handle_events()
    except KeyboardInterrupt:
        print("Stopping playback...")
        pygame.mixer.music.stop()

    # Clean up on exit
    disco_lights.off()
