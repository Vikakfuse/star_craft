import math
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    """Represents a 2D coordinate on the game map."""
    x: float
    y: float

def calculate_distance(p1: Point, p2: Point) -> float:
    """
    Calculates the Euclidean distance between two points.

    Args:
        p1: The first point.
        p2: The second point.

    Returns:
        The distance between the two points.
    """
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)

def is_within_radius(center: Point, target: Point, radius: float) -> bool:
    """
    Checks if a target point is within a given radius of a center point.
    This is optimized to avoid the square root calculation for performance.

    Args:
        center: The center point of the circle.
        target: The point to check.
        radius: The radius of the circle.

    Returns:
        True if the target is within the radius, False otherwise.
    """
    if radius < 0:
        return False
    # Compare squared distances to avoid costly sqrt
    distance_sq = (target.x - center.x)**2 + (target.y - center.y)**2
    return distance_sq <= radius**2
