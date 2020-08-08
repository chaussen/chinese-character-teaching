from hamcrest import assert_that, equal_to


class TestClass:
    def test_one(self):
        x = "this"
        assert "h" in x

    def test_two(self):
        x = "hello"
        assert hasattr(x, "check")

    def test_three(self):
        assert_that(1, equal_to(1))
