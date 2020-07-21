import random
from astrobox.core import Drone
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine import scene, GameObject
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class IgorDrone(Drone):
    _map = scene.theme.FIELD_WIDTH, scene.theme.FIELD_HEIGHT
    asteroids_in_use = list()
    dead_man = None
    reserved_positions = list()
    limit_health = 0.6
    dead_drones_asteroids = set()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.position = 0
        self.distance_no_load = 0
        self.distance_partly_loaded = 0
        self.distance_fully_loaded = 0
        self.current_asteroid = None
        self.full_rounds = 0
        self.in_action = False
        self.war_is_over = False
        self.lock = False
        self.my_asteroids = list()

    def on_born(self):
        self.my_asteroids = self.asteroids
        self.build_formation()

    def check_if_anyone_to_be_short(self):
        if self.have_gun and self.dead_man and \
                self.distance_to(self.dead_man) < self.gun.shot_distance and \
                self.valide_place(self.coord) and \
                self.distance_to(self.my_mothership) > 90 and \
                self.dead_man.distance_to(self.dead_man.my_mothership) > MOTHERSHIP_HEALING_DISTANCE:
            return True

    def the_war_is_over(self):
        self.war_is_over = True
        if self.get_bases(self) and self.distance_to(self.get_bases(self).coord) > self.gun.shot_distance - 10:
            self.move_at(self.get_place_for_attack(self, self.get_bases(self)))
        elif self.get_bases(self):
            self.get_vector(self.coord, self.get_bases(self).coord)
            self.gun.shot(self.get_bases(self))

    def on_wake_up(self):
        self.find_all_elerium_left()
        self.dead_man = self.get_enemies(self)
        if self.check_if_anyone_to_be_short():
            self.get_vector(self.coord, self.dead_man.coord)
            self.gun.shot(self.dead_man)
        elif not self.dead_man or self.dead_man.distance_to(self.dead_man.my_mothership) < MOTHERSHIP_HEALING_DISTANCE:
            self.the_war_is_over()
        elif self.dead_man:
            place = self.get_place_for_attack(self, self.get_enemies(self))
            if place:
                self.move_at(place)
        self.war_or_peace()

    def war_or_peace(self):
        if not self.get_bases(self) and not self.lock:
            self.war_is_over = True
            self.lock = True
            if self.find_closest_asteroids():
                self.move_at(self.find_closest_asteroids())

    def enemy_is_near(self):
        if self.valide_place(self.coord) and not self.in_action:
            self.in_action = False
            self.stop()
            self.get_vector(self.coord, self.get_enemies(self).coord)
            self.gun.shot(self.get_enemies(self).coord)
        elif not self.valide_place(self.coord) and not self.in_action:
            self.move_at(self.get_place_for_attack(self, self.get_enemies(self)))
            self.in_action = True

    def on_hearbeat(self):
        if self.meter_2 < self.limit_health:
            self.heal()
            self.war_is_over = False
            return
        if self.get_enemies(self) and self.distance_to(self.get_enemies(self)) < self.gun.shot_distance - 20:
            self.enemy_is_near()
        if not self.get_enemies(self) and not self.get_bases(self) and not self.war_is_over:
            self.war_is_over = True
            if self.find_closest_asteroids():
                self.move_at(self.find_closest_asteroids())
        if self.turrets_left():
            return

    def turrets_left(self):
        if self.check_enemies_at_home() == len(self.get_all_enemies(self)) and \
                self.distance_to(self.my_mothership) > self._map[0] / 2 \
                and not self.war_is_over:
            self.move_at(self.my_mothership)
            self.war_is_over = True
            return True

    def on_stop_at_asteroid(self, asteroid):
        if self.war_is_over:
            if self.full_rounds > 0:
                self.load_from(asteroid)
                self.turn_to(self.mothership)
            elif self.full_rounds <= 0:
                self.load_from(asteroid)
                self.move_at(self.mothership)

    def on_load_complete(self):
        if self.payload < 95 and self.find_closest_asteroids():
            self.move_at(self.find_closest_asteroids())
        else:
            self.move_at(self.mothership)

    def on_stop_at_mothership(self, mothership):
        self.unload_to(self.my_mothership)
        if not self.war_is_over:
            self.build_formation()
        if self.war_is_over:
            self.unload_to(self.my_mothership)
            if self.find_closest_asteroids():
                self.move_at(self.find_closest_asteroids())

    def on_unload_complete(self):
        self.full_rounds -= 1
        if self.find_closest_asteroids():
            self.move_at(self.find_closest_asteroids())
        else:
            self.stop()

    def on_stop_at_target(self, target):
        try:
            if self.my_mothership.near(target):
                self.unload_to(self.my_mothership)
                self.move_at(self.find_closest_asteroids())
            for asteroid in self.my_asteroids:
                if asteroid.near(target) and asteroid.payload > 0 and self.war_is_over:
                    self.load_from(asteroid)
                    self.move_at(self.mothership)
        except:
            pass

    def get_enemies(self, soldier):
        enemies = [(drone, soldier.distance_to(drone)) for drone in soldier.scene.drones if
                   soldier.team != drone.team and drone.is_alive]
        if not enemies:
            return
        enemies.sort(key=lambda x: x[1])
        return enemies[0][0]

    def get_all_enemies(self, soldier):
        enemies = [(drone, soldier.distance_to(drone)) for drone in soldier.scene.drones if
                   soldier.team != drone.team and drone.is_alive]
        return enemies

    def check_enemies_at_home(self):
        enemies_close_to_base = 0
        enemies = self.get_all_enemies(self)
        for drone in enemies:
            if drone[0].distance_to(drone[0].my_mothership) < MOTHERSHIP_HEALING_DISTANCE:
                enemies_close_to_base += 1
        return enemies_close_to_base

    def get_bases(self, soldier):
        bases = [base for base in soldier.scene.motherships if
                 base.team != soldier.team and base.is_alive]
        if not bases:
            return
        elif len(bases) == 1:
            return bases[0]
        return bases[0]

    def go_to_random_asteroid(self):
        """ Pick a random asteroid to go to """
        return self.move_at(random.choice(self.asteroids))

    def find_closest_asteroids(self):
        """ Find the nearest asteroid """
        if self.current_asteroid in self.asteroids_in_use:
            self.asteroids_in_use.remove(self.current_asteroid)
        distance = self.sort_asteroids_distance()
        if distance:
            self.current_asteroid = distance[0][1]
            self.asteroids_in_use.append(self.current_asteroid)
            return self.current_asteroid

    def sort_asteroids_distance(self):
        distance = []
        for asteroid in self.my_asteroids:
            if asteroid.payload > 100 and asteroid not in self.asteroids_in_use and self.full_rounds:
                distance.append(((self.distance_to(asteroid)), asteroid))
            elif asteroid.payload and asteroid not in self.asteroids_in_use and self.full_rounds <= 0:
                distance.append(((self.distance_to(asteroid)), asteroid))
        distance.sort()
        return distance

    def build_formation(self):
        if self.my_mothership.coord.x < 500:
            x = self.my_mothership.coord.x + self.radius * 2.5
        elif self.my_mothership.coord.x > 500:
            x = self.my_mothership.coord.x - self.radius * 2.5
        y = 50
        for position in self.reserved_positions:
            if y in self.reserved_positions:
                y += round(int(self._map[1]) / 5)
            else:
                self.position = y
                self.reserved_positions.append(y)
                spot = Point(x, y)
                return self.move_at(spot)
        self.position = y
        self.reserved_positions.append(y)
        spot = Point(x, y)
        self.get_vector(self.coord, spot)
        return self.move_at(spot)

    def heal(self):
        self.get_vector(self.coord, self.my_mothership.coord)
        self.move_at(self.my_mothership)
        if self.position:
            self.reserved_positions.remove(self.position)
            self.position = 0

    def get_vector(self, vector_1, vector_2):
        self.vector = Vector.from_points(vector_1, vector_2)

    def get_place_near(self, point, target, angle):
        """
        Расчет места рядом с point с отклонением angle от цели target
        :param point:
        :param target:
        :param angle:
        :return: new place point
        """
        vec = Vector(point.x - target.x, point.y - target.y)
        vec.rotate(angle)
        return Point(target.x + vec.x, target.y + vec.y)

    def get_place_for_attack(self, soldier, target):
        """
        Выбор места для атаки цели, если цель не в радиусе атаки

        :param soldier: атакующий
        :param target: цель/объект атаки
        :return: Point  - место атаки или None - если не выбрано место атаки
        """
        if isinstance(target, GameObject):
            vec = Vector.from_points(target.coord, soldier.coord)
        elif isinstance(target, Point):
            vec = Vector.from_points(target, soldier.coord)
        else:
            pass
        dist = vec.module
        _koef = 1 / dist
        norm_vec = Vector(vec.x * _koef, vec.y * _koef)
        vec_gunshot = norm_vec * min(int(self.gun.shot_distance - 50), int(dist))
        purpose = Point(target.coord.x + vec_gunshot.x, target.coord.y + vec_gunshot.y)
        angles = [0, 20, -20, 40, -40]
        random.shuffle(angles)
        for ang in angles:
            place = self.get_place_near(purpose, target, ang)
            if place and soldier.valide_place(place):
                return place
        return None

    def valide_place(self, point: Point):
        """
        Подходит ли это место для атаки. Слишком рядом не должно быть партнеров и на линии огня тоже не должно быть
        партнеров.
        :param point: анализируемое место
        :return: True or False
        """

        is_valide = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT
        for partner in self.teammates:
            if not partner.is_alive or partner is self:
                continue

            is_valide = is_valide and (partner.distance_to(point) >= 50)

        return is_valide

    def get_dead_drones(self):
        dead_drone = [drone for drone in self.scene.drones if not drone.is_alive and drone.payload > 0]
        return dead_drone

    def get_enemy_load_bases(self):
        return [base for base in self.scene.motherships if
                base.team is not self.team and base.is_alive and base.payload > 0]

    def find_all_elerium_left(self):
        self.dead_drones_asteroids.update(self.get_dead_drones())
        self.dead_drones_asteroids.update(self.get_enemy_load_bases())
        self.my_asteroids.extend(self.dead_drones_asteroids)


drone_class = IgorDrone
