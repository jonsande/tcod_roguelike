from __future__ import annotations

from typing import List, Tuple

import numpy as np
import random

WALL = False
FLOOR = True


def generate_noise_map(width: int, height: int, fill_probability: float) -> np.ndarray:
    rng = np.random.default_rng()
    return rng.random((width, height)) < fill_probability


def simulate_ca_step(map_array: np.ndarray, birth_limit: int, death_limit: int) -> np.ndarray:
    wall_count = np.zeros_like(map_array, dtype=np.int8)

    width, height = map_array.shape
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            shifted = np.roll(map_array, shift=(dx, dy), axis=(0, 1))

            if dx == -1:
                shifted[-1, :] = WALL
            if dx == 1:
                shifted[0, :] = WALL
            if dy == -1:
                shifted[:, -1] = WALL
            if dy == 1:
                shifted[:, 0] = WALL

            wall_count += shifted == WALL

    new_map = np.where(wall_count > death_limit, WALL, FLOOR)
    new_map = np.where(wall_count < birth_limit, FLOOR, new_map)
    return new_map


def generate_cavern_map(
    width: int,
    height: int,
    steps: int = 4,
    fill_probability: float = 0.45,
    birth_limit: int = 4,
    death_limit: int = 4,
) -> np.ndarray:
    noise = generate_noise_map(width, height, fill_probability=fill_probability)

    for _ in range(steps):
        noise = simulate_ca_step(noise, birth_limit, death_limit)

    noise[0, :] = WALL
    noise[-1, :] = WALL
    noise[:, 0] = WALL
    noise[:, -1] = WALL

    return noise


def flood_fill(map_array: np.ndarray, start: Tuple[int, int]) -> List[Tuple[int, int]]:
    width, height = map_array.shape
    visited = np.zeros_like(map_array, dtype=bool)
    to_visit = [start]
    region: List[Tuple[int, int]] = []

    while to_visit:
        x, y = to_visit.pop()
        if not (0 <= x < width and 0 <= y < height):
            continue
        if visited[x, y]:
            continue
        if map_array[x, y] == WALL:
            continue

        visited[x, y] = True
        region.append((x, y))

        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            to_visit.append((x + dx, y + dy))

    return region


def connect_cavern_regions(map_array: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int], Tuple[int, int]]:
    width, height = map_array.shape
    visited = np.zeros_like(map_array, dtype=bool)
    regions: List[List[Tuple[int, int]]] = []

    for x in range(width):
        for y in range(height):
            if map_array[x, y] == FLOOR and not visited[x, y]:
                region = flood_fill(map_array, (x, y))
                for rx, ry in region:
                    visited[rx, ry] = True
                if region:
                    regions.append(region)

    if not regions:
        return map_array, (width // 2, height // 2), (width // 2 + 1, height // 2 + 1)

    regions.sort(key=len, reverse=True)
    main_region = set(regions[0])

    for region in regions[1:]:

        closest_main = None
        closest_region = None
        best_distance = None

        for x1, y1 in region:
            for x2, y2 in main_region:
                distance = abs(x1 - x2) + abs(y1 - y2)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    closest_main = (x2, y2)
                    closest_region = (x1, y1)

        if closest_main and closest_region:
            x1, y1 = closest_region
            x2, y2 = closest_main
            cx, cy = x1, y1
            while (cx, cy) != (x2, y2):
                if cx < x2:
                    cx += 1
                elif cx > x2:
                    cx -= 1
                elif cy < y2:
                    cy += 1
                elif cy > y2:
                    cy -= 1
                map_array[cx, cy] = FLOOR
                main_region.add((cx, cy))

        main_region |= set(region)

    floor_tiles = list(main_region)
    player_start = random.choice(floor_tiles)
    stairs_location = random.choice(floor_tiles)

    return map_array, player_start, stairs_location
