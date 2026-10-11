import re

from django.db import migrations

# Case-preserving 'income tax' -> 'salary tax' (space, hyphen or underscore).
PATTERN = re.compile(r"(?<![A-Za-z])(income)([-_\s]+)(tax)(?![A-Za-z])", re.IGNORECASE)


def _match_case(src: str, dst: str) -> str:
    if src.isupper():
        return dst.upper()
    if src[:1].isupper():
        return dst[:1].upper() + dst[1:]
    return dst


def _rename(text: str) -> str:
    def repl(m):
        return (
            _match_case(m.group(1), "salary")
            + m.group(2)
            + _match_case(m.group(3), "tax")
        )

    return PATTERN.sub(repl, text)


def update_text(apps, schema_editor):
    """
    The deductions tour is seeded once by 0044_seed_deductions_tour, so an
    already-deployed row still says 'income tax'. Rewrite any seeded tour text
    to 'salary tax' to match the terminology used everywhere else in the UI.
    """
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    for model, fields in (
        (Tour, ("title", "description")),
        (TourStep, ("title", "description")),
    ):
        for obj in model.objects.all():
            changed = False
            for field in fields:
                value = getattr(obj, field, None)
                if not isinstance(value, str) or not PATTERN.search(value):
                    continue
                setattr(obj, field, _rename(value))
                changed = True
            if changed:
                obj.save(update_fields=list(fields))


def revert_text(apps, schema_editor):
    """No-op: reversing stored tour wording is not worth the risk."""


class Migration(migrations.Migration):

    dependencies = [
        ("horilla_tour", "0087_seed_faq_view_tour"),
    ]

    operations = [
        migrations.RunPython(update_text, revert_text),
    ]
