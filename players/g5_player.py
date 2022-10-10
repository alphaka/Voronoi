import os
import pickle
import numpy as np
import sympy
import logging
from typing import Tuple
import sympy


def sympy_p_float(p: sympy.Point2D):
    return np.array([float(p.x), float(p.y)])

class Player:
    def __init__(self, rng: np.random.Generator, logger: logging.Logger, total_days: int, spawn_days: int,
                 player_idx: int, spawn_point: sympy.geometry.Point2D, min_dim: int, max_dim: int, precomp_dir: str) \
            -> None:
        """Initialise the player with given skill.

            Args:
                rng (np.random.Generator): numpy random number generator, use this for same player behavior across run
                logger (logging.Logger): logger use this like logger.info("message")
                total_days (int): total number of days, the game is played
                spawn_days (int): number of days after which new units spawn
                player_idx (int): index used to identify the player among the four possible players
                spawn_point (sympy.geometry.Point2D): Homebase of the player
                min_dim (int): Minimum boundary of the square map
                max_dim (int): Maximum boundary of the square map
                precomp_dir (str): Directory path to store/load pre-computation
        """

        # precomp_path = os.path.join(precomp_dir, "{}.pkl".format(map_path))

        # # precompute check
        # if os.path.isfile(precomp_path):
        #     # Getting back the objects:
        #     with open(precomp_path, "rb") as f:
        #         self.obj0, self.obj1, self.obj2 = pickle.load(f)
        # else:
        #     # Compute objects to store
        #     self.obj0, self.obj1, self.obj2 = _

        #     # Dump the objects
        #     with open(precomp_path, 'wb') as f:
        #         pickle.dump([self.obj0, self.obj1, self.obj2], f)

        self.rng = rng
        self.logger = logger
        self.player_idx = player_idx
        if self.player_idx == 0:
            self.homebase = np.array([0.5, 0.5])
        elif self.player_idx == 1:
            self.homebase = np.array([0.5, 99.5])
        elif self.player_idx == 2:
            self.homebase = np.array([99.5, 99.5])
        else:
            self.homebase = np.array([99.5, 0.5])
    
    def force_vec(self, p1, p2):
        v = p1 - p2
        mag = np.linalg.norm(v)
        unit = v / mag
        return unit, mag

    def to_polar(self, p):
        x, y = p
        return np.sqrt(x ** 2 + y ** 2), np.arctan2(y, x)

    def normalize(self, v):
        return v / np.linalg.norm(v)

    def repelling_force(self, p1, p2):
        dir, mag = self.force_vec(p1, p2)
        # Inverse magnitude: closer things apply greater force
        return dir * 1 / (mag)

    def attractive_force(self, p1, p2):
        return -self.repelling_force(p1, p2)


    def initial_strategy(self, unit_id, unit_pos, map_states, current_scores, total_scores, own_units, enemy_units_locations):
        ENEMY_INFLUENCE = 1
        HOME_INFLUENCE = 20
        ALLY_INFLUENCE = 0.6
        BOUNDARY_INFLUENCE = 1
        BOUNDARY_THRESHOLD = 1
        BOUNDARY_FACTOR = 10

        
        enemy_unit_forces = [
            self.attractive_force(unit_pos, enemy_pos)
            for _, enemy_pos in enemy_units_locations
        ]
        enemy_force = np.add.reduce(enemy_unit_forces)

        ally_force = [
            self.repelling_force(unit_pos, ally_pos)
            for ally_id, ally_pos in own_units
            if ally_id != unit_id
        ]
        ally_force = np.add.reduce(ally_force)

        boundary_force = np.array([0.0, 0.0])
        top_repelling_force = np.array([0.0, 1.0])
        bottom_repelling_force = np.array([0.0, -1.0])
        left_repelling_force = np.array([1.0, 0.0])
        right_repelling_force = np.array([-1.0, 0.0])
        if unit_pos[0] < BOUNDARY_THRESHOLD:
            if unit_pos[0] > 0:
                boundary_force += left_repelling_force * (1.0 / unit_pos[0])
            else:
                boundary_force += left_repelling_force * BOUNDARY_FACTOR
        if unit_pos[0] > 100 - BOUNDARY_THRESHOLD:
            if unit_pos[0] < 100:
                boundary_force += right_repelling_force * (1.0 / (100.0 - unit_pos[0]))
            else:
                boundary_force += right_repelling_force * BOUNDARY_FACTOR
        if unit_pos[1] < BOUNDARY_THRESHOLD:
            if unit_pos[1] > 0:
                boundary_force += top_repelling_force * (1.0 / unit_pos[1])
            else:
                boundary_force += top_repelling_force * BOUNDARY_FACTOR
        if unit_pos[1] > 100 - BOUNDARY_THRESHOLD:
            if unit_pos[1] < 100:
                boundary_force += bottom_repelling_force * (1.0 / (100.0 - unit_pos[1]))
            else:
                boundary_force += bottom_repelling_force * BOUNDARY_FACTOR
        
        if unit_pos[0] == self.homebase[0] and unit_pos[1] == self.homebase[1]:
            home_force = np.array([0.0, 0.0])
        else:
            home_force = self.repelling_force(unit_pos, self.homebase)
        

        total_force = self.normalize(
            (enemy_force * ENEMY_INFLUENCE)
            + (home_force * HOME_INFLUENCE)
            + (ally_force * ALLY_INFLUENCE)
            + (boundary_force * BOUNDARY_INFLUENCE)
        )

        return self.to_polar(total_force)

    def cluster_strategy(self, unit_id, unit_pos, map_states, current_scores, total_scores, own_units, enemy_units_locations, closest_cluster, closest_cluster_distance):
        row, col, ids = closest_cluster
        ENEMY_INFLUENCE = 1
        HOME_INFLUENCE = 20
        ALLY_INFLUENCE = 0.2
        CLUSTER_ENEMY_INFLUENCE = 5 * (1 / closest_cluster_distance)
        BOUNDARY_INFLUENCE = 1
        BOUNDARY_THRESHOLD = 1
        BOUNDARY_FACTOR = 10
        
        cluster_enemy_unit_forces = [
            self.repelling_force(unit_pos, enemy_pos)
            for enemy_id, enemy_pos in enemy_units_locations
            if enemy_id in ids
        ]
        cluster_enemy_force = np.add.reduce(cluster_enemy_unit_forces)

        other_enemy_unit_forces = [
            self.attractive_force(unit_pos, enemy_pos)
            for enemy_id, enemy_pos in enemy_units_locations
            if enemy_id not in ids
        ]
        other_enemy_force = np.add.reduce(other_enemy_unit_forces)

        ally_force = [
            self.repelling_force(unit_pos, ally_pos)
            for ally_id, ally_pos in own_units
            if ally_id != unit_id
        ]
        ally_force = np.add.reduce(ally_force)

        boundary_force = np.array([0.0, 0.0])
        top_repelling_force = np.array([0.0, 1.0])
        bottom_repelling_force = np.array([0.0, -1.0])
        left_repelling_force = np.array([1.0, 0.0])
        right_repelling_force = np.array([-1.0, 0.0])
        if unit_pos[0] < BOUNDARY_THRESHOLD:
            if unit_pos[0] > 0:
                boundary_force += left_repelling_force * (1.0 / unit_pos[0])
            else:
                boundary_force += left_repelling_force * BOUNDARY_FACTOR
        if unit_pos[0] > 100 - BOUNDARY_THRESHOLD:
            if unit_pos[0] < 100:
                boundary_force += right_repelling_force * (1.0 / (100.0 - unit_pos[0]))
            else:
                boundary_force += right_repelling_force * BOUNDARY_FACTOR
        if unit_pos[1] < BOUNDARY_THRESHOLD:
            if unit_pos[1] > 0:
                boundary_force += top_repelling_force * (1.0 / unit_pos[1])
            else:
                boundary_force += top_repelling_force * BOUNDARY_FACTOR
        if unit_pos[1] > 100 - BOUNDARY_THRESHOLD:
            if unit_pos[1] < 100:
                boundary_force += bottom_repelling_force * (1.0 / (100.0 - unit_pos[1]))
            else:
                boundary_force += bottom_repelling_force * BOUNDARY_FACTOR
        
        if unit_pos[0] == self.homebase[0] and unit_pos[1] == self.homebase[1]:
            home_force = np.array([0.0, 0.0])
        else:
            home_force = self.repelling_force(unit_pos, self.homebase)
        

        total_force = self.normalize(
            + (cluster_enemy_force * CLUSTER_ENEMY_INFLUENCE)
            + (other_enemy_force * ENEMY_INFLUENCE)
            + (home_force * HOME_INFLUENCE)
            + (ally_force * ALLY_INFLUENCE)
            + (boundary_force * BOUNDARY_INFLUENCE)
        )

        return self.to_polar(total_force)



    def play(self, unit_id, unit_pos, map_states, current_scores, total_scores) -> [tuple[float, float]]:
        """Function which based on current game state returns the distance and angle of each unit active on the board

                Args:
                    unit_id (list(list(str))): contains the ids of each player's units (unit_id[player_idx][x])
                    unit_pos (list(list(float))): contains the position of each unit currently present on the map
                                                    (unit_pos[player_idx][x])
                    map_states (list(list(int)): contains the state of each cell, using the x, y coordinate system
                                                    (map_states[x][y])
                    current_scores (list(int)): contains the number of cells currently occupied by each player
                                                    (current_scores[player_idx])
                    total_scores (list(int)): contains the cumulative scores up until the current day
                                                    (total_scores[player_idx]

                Returns:
                    List[Tuple[float, float]]: Return a list of tuples consisting of distance and angle in radians to
                                                move each unit of the player
                """

        own_units = list(
            zip(
                unit_id[self.player_idx],
                [sympy_p_float(pos) for pos in unit_pos[self.player_idx]],
            )
        )

        enemy_units_locations = [
            (i, sympy_p_float(unit_pos[player][i]))
            for player in range(len(unit_pos))
            for i in range(len(unit_pos[player]))
            if player != self.player_idx
        ]

        BLOCK_SIZE = 4
        CLUSTER_THRESHOLD = 10
        block_count =  [[set()] * (100 // BLOCK_SIZE) for i in range(100 // BLOCK_SIZE)]
        for enemy_id, enemy_pos in enemy_units_locations:
            col, row = int(enemy_pos[0]), int(enemy_pos[1])
            block_count[row // BLOCK_SIZE][col // BLOCK_SIZE].add(enemy_id)
        
        clusters = []
        for row in range(100 // BLOCK_SIZE):
            for col in range(100 // BLOCK_SIZE):
                if len(block_count[row][col]) >= CLUSTER_THRESHOLD:
                    clusters.append((row, col, block_count[row][col]))
                
        moves = []
        if len(clusters) <= 3:
            for unit_id, unit_pos in own_units:
                moves.append(self.initial_strategy(unit_id, unit_pos, map_states, current_scores, total_scores, own_units, enemy_units_locations))
        else:
            for unit_id, unit_pos in own_units:
                closest_cluster_distance = float("inf")
                closest_cluster = None
                for (row, col, ids) in clusters:
                    cluster_center = np.array([col * BLOCK_SIZE + BLOCK_SIZE / 2, row * BLOCK_SIZE + BLOCK_SIZE / 2])
                    if np.linalg.norm(cluster_center - unit_pos) < closest_cluster_distance:
                        closest_cluster_distance = np.linalg.norm(cluster_center - unit_pos)
                        closest_cluster = (row, col, ids)
                
                if closest_cluster_distance > 20:
                    moves.append(self.initial_strategy(unit_id, unit_pos, map_states, current_scores, total_scores, 
                                                       own_units, enemy_units_locations))
                else:
                    moves.append(self.cluster_strategy(unit_id, unit_pos, map_states, current_scores, total_scores,
                                                       own_units, enemy_units_locations, closest_cluster, closest_cluster_distance))
        return moves

