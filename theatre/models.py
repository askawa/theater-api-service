import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def play_image_file_path(instance, filename: str) -> str:
    extension = os.path.splitext(filename)[1]
    return os.path.join("uploads", "plays", f"{uuid.uuid4()}{extension}")


class Genre(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Actor(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    class Meta:
        ordering = ("last_name", "first_name")
        constraints = [
            models.UniqueConstraint(
                fields=("first_name", "last_name"),
                name="unique_actor_full_name",
            )
        ]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return self.full_name


class Play(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    genres = models.ManyToManyField(Genre, related_name="plays")
    actors = models.ManyToManyField(Actor, related_name="plays")
    image = models.ImageField(null=True, blank=True, upload_to=play_image_file_path)

    class Meta:
        ordering = ("title",)

    def __str__(self) -> str:
        return self.title


class TheatreHall(models.Model):
    name = models.CharField(max_length=255, unique=True)
    rows = models.PositiveIntegerField()
    seats_in_row = models.PositiveIntegerField()

    class Meta:
        ordering = ("name",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rows__gt=0),
                name="theatre_hall_rows_greater_than_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(seats_in_row__gt=0),
                name="theatre_hall_seats_greater_than_zero",
            ),
        ]

    @property
    def capacity(self) -> int:
        return self.rows * self.seats_in_row

    def __str__(self) -> str:
        return self.name


class Performance(models.Model):
    play = models.ForeignKey(
        Play,
        on_delete=models.CASCADE,
        related_name="performances",
    )
    theatre_hall = models.ForeignKey(
        TheatreHall,
        on_delete=models.CASCADE,
        related_name="performances",
    )
    show_time = models.DateTimeField()

    class Meta:
        ordering = ("show_time",)
        constraints = [
            models.UniqueConstraint(
                fields=("theatre_hall", "show_time"),
                name="unique_performance_hall_show_time",
            )
        ]

    def __str__(self) -> str:
        return f"{self.play.title} at {self.show_time:%Y-%m-%d %H:%M}"


class Reservation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Reservation {self.pk} by {self.user}"


class Ticket(models.Model):
    row = models.PositiveIntegerField()
    seat = models.PositiveIntegerField()
    performance = models.ForeignKey(
        Performance,
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    class Meta:
        ordering = ("performance__show_time", "row", "seat")
        constraints = [
            models.UniqueConstraint(
                fields=("performance", "row", "seat"),
                name="unique_ticket_performance_seat",
            ),
            models.CheckConstraint(
                condition=models.Q(row__gt=0),
                name="ticket_row_greater_than_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(seat__gt=0),
                name="ticket_seat_greater_than_zero",
            ),
        ]

    @staticmethod
    def validate_ticket(row: int, seat: int, theatre_hall: TheatreHall) -> None:
        errors = {}
        if not 1 <= row <= theatre_hall.rows:
            errors["row"] = (
                f"Row must be in range [1, {theatre_hall.rows}], not {row}."
            )
        if not 1 <= seat <= theatre_hall.seats_in_row:
            errors["seat"] = (
                "Seat must be in range "
                f"[1, {theatre_hall.seats_in_row}], not {seat}."
            )
        if errors:
            raise ValidationError(errors)

    def clean(self) -> None:
        super().clean()
        if self.performance_id:
            self.validate_ticket(self.row, self.seat, self.performance.theatre_hall)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.performance} (row {self.row}, seat {self.seat})"
