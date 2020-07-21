# -*- coding: utf-8 -*-
from astrobox.space_field import SpaceField
from devastator import DevastatorDrone
from igorDrone import IgorDrone

NUMBER_OF_DRONES = 5

if __name__ == '__main__':
    scene = SpaceField(
        field=(1500, 800),
        speed=10,
        asteroids_count=15,
        can_fight=True,
    )

    team_1 = [IgorDrone() for _ in range(NUMBER_OF_DRONES)]
    team_3 = [DevastatorDrone() for _ in range(NUMBER_OF_DRONES)]
    scene.go()
