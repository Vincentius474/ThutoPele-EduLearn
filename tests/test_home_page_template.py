from fastapi.templating import Jinja2Templates
from pathlib import Path


def test_home_page_template_compiles():
    templates_dir = Path(__file__).resolve().parents[1] / "app" / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    template = templates.get_template("index.html")
    assert template is not None
