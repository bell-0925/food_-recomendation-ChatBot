import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from data.repositories.base import (
    BaseRestaurantRepo, BaseWeatherRepo,
    BaseNutritionRepo, BaseTeamRepo
)

def test_base_repos_are_abstract():
    """추상 클래스는 직접 인스턴스화 불가."""
    import inspect
    assert inspect.isabstract(BaseRestaurantRepo)
    assert inspect.isabstract(BaseWeatherRepo)
    assert inspect.isabstract(BaseNutritionRepo)
    assert inspect.isabstract(BaseTeamRepo)
