def test_user_background_input_defaults():
    from models import UserBackgroundInput

    bg = UserBackgroundInput()
    assert bg.occupation == ""
    assert bg.abilities == []
    assert bg.masteredKnowledge == []


def test_user_background_input_accepts_lists():
    from models import UserBackgroundInput

    bg = UserBackgroundInput(
        abilities=["JavaScript", "Python"], masteredKnowledge=["变量", "循环"]
    )
    assert len(bg.abilities) == 2
    assert "变量" in bg.masteredKnowledge


def test_generate_graph_request_with_user_background():
    from routers.ai import GenerateGraphRequest
    from models import UserBackgroundInput

    req = GenerateGraphRequest(
        input="学Python",
        interpretation="掌握Python基础",
        userBackground=UserBackgroundInput(
            abilities=["JS入门"], masteredKnowledge=["变量"]
        ),
    )
    assert req.userBackground.abilities == ["JS入门"]
    assert req.userBackground is not None


def test_generate_graph_request_without_user_background():
    from routers.ai import GenerateGraphRequest

    req = GenerateGraphRequest(input="学Python", interpretation="掌握Python基础")
    assert req.userBackground is None
