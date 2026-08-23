from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from theatre.models import Actor, Genre, Performance, Play, TheatreHall


class Command(BaseCommand):
    help = "Create an idempotent set of demonstration theatre data."

    def handle(self, *args, **options):
        drama, _ = Genre.objects.get_or_create(name="Drama")
        tragedy, _ = Genre.objects.get_or_create(name="Tragedy")
        comedy, _ = Genre.objects.get_or_create(name="Comedy")

        actors = [
            Actor.objects.get_or_create(first_name="Mark", last_name="Rylance")[0],
            Actor.objects.get_or_create(first_name="Viola", last_name="Davis")[0],
            Actor.objects.get_or_create(first_name="Andrew", last_name="Scott")[0],
        ]

        hamlet, _ = Play.objects.get_or_create(
            title="Hamlet",
            defaults={"description": "Shakespeare's timeless tragedy of revenge."},
        )
        hamlet.genres.set((drama, tragedy))
        hamlet.actors.set(actors[1:])

        importance, _ = Play.objects.get_or_create(
            title="The Importance of Being Earnest",
            defaults={"description": "Oscar Wilde's sparkling comedy of manners."},
        )
        importance.genres.set((comedy,))
        importance.actors.set((actors[0], actors[2]))

        main_hall, _ = TheatreHall.objects.get_or_create(
            name="Main Stage",
            defaults={"rows": 12, "seats_in_row": 18},
        )
        studio, _ = TheatreHall.objects.get_or_create(
            name="Studio Theatre",
            defaults={"rows": 6, "seats_in_row": 10},
        )

        start = timezone.now().replace(minute=0, second=0, microsecond=0)
        performances = (
            (hamlet, main_hall, start + timedelta(days=1, hours=4)),
            (importance, studio, start + timedelta(days=2, hours=3)),
            (hamlet, studio, start + timedelta(days=4, hours=4)),
        )
        for play, hall, show_time in performances:
            Performance.objects.get_or_create(
                play=play,
                theatre_hall=hall,
                show_time=show_time,
            )

        self.stdout.write(self.style.SUCCESS("Demo theatre data is ready."))

