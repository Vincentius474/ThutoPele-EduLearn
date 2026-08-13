import pytest

from app.web.web import get_instructor_dashboard_data


class FakeResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count if count is not None else len(data)


class FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}
        self.select_fields = None

    def select(self, *args, **kwargs):
        self.select_fields = args
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def in_(self, key, values):
        self.filters[key] = values
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        rows = getattr(self.supabase, self.table_name)
        filtered = []
        for row in rows:
            if all(
                (row.get(key) in value if isinstance(value, list) else row.get(key) == value)
                for key, value in self.filters.items()
            ):
                filtered.append(row)

        return FakeResult(filtered, count=len(filtered))


class FakeSupabase:
    def __init__(self):
        self.courses = [
            {"id": "c1", "instructor_id": "u1", "title": "Python Basics", "is_published": True, "price": 10},
            {"id": "c2", "instructor_id": "u1", "title": "Advanced Draft", "is_published": False, "price": 20},
        ]
        self.enrollments = [
            {"id": "e1", "course_id": "c1"},
            {"id": "e2", "course_id": "c1"},
            {"id": "e3", "course_id": "c2"},
        ]
        self.reviews = [
            {"course_id": "c1", "rating": 5, "comment": "Great course!", "created_at": "2026-08-10", "users": {"full_name": "Jane Doe"}, "courses": {"title": "Python Basics"}},
            {"course_id": "c1", "rating": 3, "comment": "Helpful but short.", "created_at": "2026-08-09", "users": {"full_name": "Alex Smith"}, "courses": {"title": "Python Basics"}},
            {"course_id": "c2", "rating": 4, "comment": "Really solid.", "created_at": "2026-08-08", "users": {"full_name": "Sam Green"}, "courses": {"title": "Advanced Draft"}},
        ]

    def table(self, table_name):
        return FakeQuery(self, table_name)


@pytest.mark.asyncio
async def test_get_instructor_dashboard_data():
    supabase = FakeSupabase()

    data = await get_instructor_dashboard_data(supabase, "u1")

    assert data["total_courses"] == 2
    assert data["total_students"] == 3
    assert data["avg_rating"] == 4.0
    assert len(data["published_courses"]) == 1
    assert len(data["draft_courses"]) == 1
    assert data["published_courses"][0]["student_count"] == 2
    assert data["draft_courses"][0]["student_count"] == 1
    assert data["total_earnings"] == 40
    assert len(data["recent_reviews"]) == 3
    assert data["recent_reviews"][0]["student_name"] == "Jane Doe"
    assert data["recent_reviews"][0]["course_title"] == "Python Basics"
