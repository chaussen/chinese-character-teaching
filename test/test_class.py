from hamcrest import assert_that, equal_to
import path_configs


class TestClass:
    def __init__(self):
        path_configs.show_real_path()

    def test_one(self):
        x = "this"
        assert "h" in x

    def test_two(self):
        x = "hello"
        assert hasattr(x, "__contains__")

    def test_three(self):
        assert_that(1, equal_to(1))
