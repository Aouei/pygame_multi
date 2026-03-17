import math


def check_intersection_by_radius(obj1, obj2) -> bool:
    """
    Comprueba si dos objetos intersectan basándose en sus posiciones y radios.
    Se asume que cada objeto tiene los atributos 'x', 'y' y 'radius'.
    """
    dx = obj1.x - obj2.x
    dy = obj1.y - obj2.y
    distance = math.hypot(dx, dy)
    return distance <= (obj1.radius + obj2.radius)


def check_collision_with_entities(obj, entities):
    for entity in entities:
        if check_intersection_by_radius(obj, entity):
            return entity
    return False
