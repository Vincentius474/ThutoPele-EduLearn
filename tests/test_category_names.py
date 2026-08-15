from app.main import templates


def test_category_names_include_all_icon_categories():
    category_names = templates.env.globals.get("category_names", [])

    assert category_names
    assert "Programming" in category_names
    assert "Systems" in category_names
    assert "Data Science" in category_names
    assert "Cloud Computing" in category_names
    assert "Blockchain" in category_names
    assert "General" in category_names
    assert "Other" in category_names
